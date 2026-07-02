"""
Management command to scan all courses in a workspace.

Usage:
    python manage.py scan_workspace <workspace_id>
"""

from django.core.management.base import BaseCommand, CommandError

from apps.courses.models import Course
from apps.courses.services.scanner import scan_course
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = "Scan all courses in a workspace"

    def add_arguments(self, parser):
        parser.add_argument("workspace_id", type=int, help="Workspace ID to scan")

    def handle(self, *args, **options):
        try:
            workspace = Workspace.objects.get(pk=options["workspace_id"])
        except Workspace.DoesNotExist:
            raise CommandError(f"Workspace with id {options['workspace_id']} not found")

        courses = Course.objects.filter(workspace=workspace)
        total_added = 0
        total_deleted = 0

        self.stdout.write(f"Scanning workspace: {workspace.name} ({courses.count()} courses)")

        for course in courses:
            self.stdout.write(f"  Scanning course: {course.title}")
            result = scan_course(course)
            total_added += result.added
            total_deleted += result.deleted
            self.stdout.write(f"    Nodes: {result.total_nodes}, Added: {result.added}, Deleted: {result.deleted}")

        self.stdout.write(self.style.SUCCESS(f"Scan complete: {total_added} added, {total_deleted} deleted"))
