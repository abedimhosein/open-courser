"""
Progress Tracking Service

Owned by: Backend Django Agent (orchestration)
Delegates to: Progress Logic Agent (Progress Tracking)

Purpose: Orchestrate progress tracking operations and persist
         watch history to the database.
"""

from django.db import transaction
from django.utils import timezone

from apps.courses.models import Course, CourseFile
from apps.progress.models import WatchHistory
from domain.skills.progress_tracking import (
    FileProgress,
    LearningStatus,
    PlaybackEvent,
    calculate_file_progress,
    calculate_course_progress,
    update_watched_duration,
    validate_playback_position,
)


def record_playback_position(
    course_file: CourseFile,
    position: float,
) -> WatchHistory | None:
    """
    Record a playback position update for a course file.

    Creates or updates the WatchHistory record.
    """
    duration = course_file.duration

    if not validate_playback_position(position, duration):
        return None

    watch, created = WatchHistory.objects.get_or_create(
        course_file=course_file,
        defaults={
            "position": position,
            "duration_watched": 0.0,
            "completed": False,
        },
    )

    if not created:
        previous_position = watch.position
        event = PlaybackEvent(position=position, duration=duration)
        new_watched = update_watched_duration(
            watch.duration_watched, event, previous_position
        )

        watch.position = position
        watch.duration_watched = new_watched
        watch.last_watched_at = timezone.now()
        watch.save(update_fields=["position", "duration_watched", "last_watched_at"])

    return watch


def mark_completed(course_file: CourseFile) -> WatchHistory | None:
    """
    Mark a course file as completed (watched 100%).
    """
    last_position = course_file.duration or 0.0

    watch, created = WatchHistory.objects.get_or_create(
        course_file=course_file,
        defaults={
            "position": last_position,
            "duration_watched": course_file.duration or 0.0,
            "completed": True,
        },
    )

    if not created:
        if course_file.duration:
            last_position = course_file.duration

        watch.position = last_position
        watch.duration_watched = course_file.duration or watch.duration_watched
        watch.completed = True
        watch.last_watched_at = timezone.now()
        watch.save(
            update_fields=["position", "duration_watched", "completed", "last_watched_at"]
        )

    return watch


def get_file_progress(course_file: CourseFile) -> dict:
    """
    Get progress information for a single course file.
    """
    try:
        watch = WatchHistory.objects.get(course_file=course_file)
    except WatchHistory.DoesNotExist:
        return {
            "file_id": course_file.id,
            "name": course_file.name,
            "watched_duration": 0.0,
            "watched_percentage": None,
            "status": LearningStatus.NOT_STARTED.value,
            "last_position": 0.0,
        }

    if watch.completed:
        return {
            "file_id": course_file.id,
            "name": course_file.name,
            "watched_duration": course_file.duration or watch.duration_watched,
            "watched_percentage": 100.0 if course_file.duration else None,
            "status": LearningStatus.COMPLETED.value,
            "last_position": watch.position,
        }

    progress = calculate_file_progress(
        watched_seconds=watch.duration_watched,
        total_duration=course_file.duration,
        last_position=watch.position,
    )

    return {
        "file_id": course_file.id,
        "name": course_file.name,
        "watched_duration": progress.watched_duration,
        "watched_percentage": progress.watched_percentage,
        "status": progress.status.value,
        "last_position": progress.last_position,
    }


def get_course_progress(course: Course) -> dict:
    """
    Get overall progress for an entire course.

    Uses the database `completed` flag as the authoritative source
    for completion status, rather than recalculating from duration alone.
    """
    files = CourseFile.objects.filter(course=course)
    durations = [f.duration for f in files]
    file_ids = [f.id for f in files]

    completed_file_ids = set(
        WatchHistory.objects.filter(
            course_file_id__in=file_ids, completed=True
        ).values_list("course_file_id", flat=True)
    )

    file_progresses = []
    for cf in files:
        fp = get_file_progress(cf)

        if cf.id in completed_file_ids:
            file_progresses.append(
                FileProgress(
                    watched_duration=cf.duration or 0.0,
                    watched_percentage=100.0 if cf.duration else None,
                    status=LearningStatus.COMPLETED,
                    last_position=fp["last_position"],
                )
            )
        else:
            file_progresses.append(
                calculate_file_progress(
                    watched_seconds=fp["watched_duration"],
                    total_duration=cf.duration,
                    last_position=fp["last_position"],
                )
            )

    course_progress = calculate_course_progress(file_progresses, durations)

    return {
        "course_id": course.id,
        "course_name": course.name,
        "total_duration": course_progress.total_duration,
        "completed_duration": course_progress.completed_duration,
        "overall_percentage": course_progress.overall_percentage,
        "total_files": course_progress.total_files,
        "completed_files": course_progress.completed_files,
    }


def reset_file_progress(course_file: CourseFile) -> None:
    """Reset progress for a single file."""
    WatchHistory.objects.filter(course_file=course_file).delete()
