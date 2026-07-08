from django.db import migrations


def populate_durations(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    MediaMetadata = apps.get_model("media", "MediaMetadata")
    WatchHistory = apps.get_model("progress", "WatchHistory")

    for course in Course.objects.all():
        # Total duration from media metadata
        total = MediaMetadata.objects.filter(
            course_node__course=course,
            course_node__node_type="file",
            duration__isnull=False,
        ).values_list("duration", flat=True)
        course.total_duration = sum(total)

        # Watched duration from watch history
        watched = 0.0
        for wh in WatchHistory.objects.filter(
            course_node__course=course,
            course_node__node_type="file",
        ).select_related("course_node__media_metadata"):
            node = wh.course_node
            dur = None
            if node.media_metadata:
                dur = node.media_metadata.duration
            if wh.completed and dur:
                watched += dur
            elif wh.duration_watched:
                watched += wh.duration_watched

        course.watched_duration = watched
        course.remaining_duration = max(course.total_duration - watched, 0)
        course.save(update_fields=["total_duration", "watched_duration", "remaining_duration"])


def reverse_populate_durations(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Course.objects.all().update(total_duration=0, watched_duration=0, remaining_duration=0)


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0005_course_remaining_duration_course_total_duration_and_more"),
        ("media", "0001_initial"),
        ("progress", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(populate_durations, reverse_populate_durations),
    ]
