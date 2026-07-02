from apps.courses.models import CourseNode
from apps.progress.models import WatchHistory
from domain.skills.progress_tracking import (
    LearningStatus,
    calculate_file_progress,
    calculate_course_progress,
    update_watched_duration,
    validate_playback_position,
    PlaybackEvent,
    FileProgress as DomainFileProgress,
)


def record_playback_position(node: CourseNode, position: float) -> WatchHistory | None:
    """
    Record or update a playback position for a file node.
    """
    if node.node_type != "file":
        return None

    duration = None
    if hasattr(node, "media_metadata") and node.media_metadata:
        duration = node.media_metadata.duration

    if not validate_playback_position(position, duration):
        return None

    watch, created = WatchHistory.objects.get_or_create(
        course_node=node,
        defaults={
            "position": position,
            "duration_watched": 0.0,
        },
    )

    if not created:
        event = PlaybackEvent(position=position, duration=duration)
        new_watched = update_watched_duration(
            watch.duration_watched, event, watch.position,
        )
        watch.position = position
        watch.duration_watched = new_watched
        watch.save(update_fields=["position", "duration_watched", "last_watched_at"])

    return watch


def mark_completed(node: CourseNode) -> WatchHistory | None:
    """Mark a file node as completed."""
    if node.node_type != "file":
        return None

    watch, _ = WatchHistory.objects.get_or_create(course_node=node)
    watch.completed = True
    watch.save(update_fields=["completed", "last_watched_at"])
    return watch


def get_file_progress(node: CourseNode) -> dict:
    """Get progress for a single file node as a dict."""
    duration = None
    if hasattr(node, "media_metadata") and node.media_metadata:
        duration = node.media_metadata.duration

    try:
        watch = WatchHistory.objects.get(course_node=node)
        if watch.completed:
            domain_progress = DomainFileProgress(
                watched_duration=duration or 0,
                watched_percentage=100.0,
                status=LearningStatus.COMPLETED,
                last_position=duration or 0,
            )
        else:
            domain_progress = calculate_file_progress(
                watch.duration_watched, duration, watch.position,
            )
        return {
            "file_id": node.pk,
            "name": node.name,
            "watched_duration": domain_progress.watched_duration,
            "watched_percentage": domain_progress.watched_percentage,
            "status": domain_progress.status.value,
            "last_position": domain_progress.last_position,
        }
    except WatchHistory.DoesNotExist:
        domain_progress = calculate_file_progress(0.0, duration, 0.0)
        return {
            "file_id": node.pk,
            "name": node.name,
            "watched_duration": domain_progress.watched_duration,
            "watched_percentage": domain_progress.watched_percentage,
            "status": domain_progress.status.value,
            "last_position": domain_progress.last_position,
        }


def get_course_progress(course) -> dict | None:
    """Aggregate progress across all file nodes in a course."""
    file_nodes = CourseNode.objects.filter(course=course, node_type="file").select_related(
        "media_metadata"
    )

    if not file_nodes:
        return None

    file_progresses: list[DomainFileProgress] = []
    durations: list[float | None] = []

    for node in file_nodes:
        duration = None
        if hasattr(node, "media_metadata") and node.media_metadata:
            duration = node.media_metadata.duration
        durations.append(duration)

        try:
            watch = WatchHistory.objects.get(course_node=node)
            if watch.completed:
                fp = DomainFileProgress(
                    watched_duration=duration or 0,
                    watched_percentage=100.0,
                    status=LearningStatus.COMPLETED,
                    last_position=duration or 0,
                )
            else:
                fp = calculate_file_progress(watch.duration_watched, duration, watch.position)
        except WatchHistory.DoesNotExist:
            fp = calculate_file_progress(0.0, duration, 0.0)

        file_progresses.append(fp)

    course_progress = calculate_course_progress(file_progresses, durations)

    return {
        "total_duration": course_progress.total_duration,
        "completed_duration": course_progress.completed_duration,
        "remaining_duration": course_progress.total_duration - course_progress.completed_duration,
        "overall_percentage": course_progress.overall_percentage,
        "total_files": course_progress.total_files,
        "completed_files": course_progress.completed_files,
    }


def reset_file_progress(node: CourseNode) -> None:
    """Delete watch history for a file node."""
    if node.node_type != "file":
        return
    WatchHistory.objects.filter(course_node=node).delete()
