"""
Management command to extract media metadata for all files in a course.

Usage:
    python manage.py extract_metadata <course_id>
"""

from django.core.management.base import BaseCommand, CommandError

from apps.courses.models import Course, CourseFile
from apps.media.services.extractor import extract_and_save_metadata


class Command(BaseCommand):
    help = "Extract media metadata for all files in a course"

    def add_arguments(self, parser):
        parser.add_argument("course_id", type=int, help="Course ID to process")

    def handle(self, *args, **options):
        try:
            course = Course.objects.get(pk=options["course_id"])
        except Course.DoesNotExist:
            raise CommandError(f"Course with id {options['course_id']} not found")

        files = CourseFile.objects.filter(course=course)
        total = files.count()
        success = 0

        self.stdout.write(f"Extracting metadata for course: {course.name} ({total} files)")

        for cf in files:
            if extract_and_save_metadata(cf):
                success += 1

        self.stdout.write(self.style.SUCCESS(f"Extraction complete: {success}/{total} succeeded"))
