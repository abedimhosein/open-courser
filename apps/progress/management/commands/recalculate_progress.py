"""
Management command to recalculate progress for a course.

Usage:
    python manage.py recalculate_progress <course_id>
"""

from django.core.management.base import BaseCommand, CommandError

from apps.courses.models import Course
from apps.progress.services.tracker import get_course_progress


class Command(BaseCommand):
    help = "Recalculate and display progress for a course"

    def add_arguments(self, parser):
        parser.add_argument("course_id", type=int, help="Course ID")

    def handle(self, *args, **options):
        try:
            course = Course.objects.get(pk=options["course_id"])
        except Course.DoesNotExist:
            raise CommandError(f"Course with id {options['course_id']} not found")

        progress = get_course_progress(course)

        self.stdout.write(f"Progress for course: {course.name}")
        self.stdout.write(f"  Overall: {progress['overall_percentage']:.1f}%")
        self.stdout.write(f"  Files: {progress['completed_files']}/{progress['total_files']}")
        self.stdout.write(f"  Duration: {progress['completed_duration']:.0f}s / {progress['total_duration']:.0f}s")
