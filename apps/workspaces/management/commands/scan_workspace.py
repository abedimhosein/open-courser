"""
Management command to scan a workspace's course root.

Usage:
    python manage.py scan_workspace <workspace_id>
    python manage.py scan_workspace <workspace_id> --full
"""

from django.core.management.base import BaseCommand, CommandError

from apps.courses.services.scanner import scan_workspace
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = "Scan a workspace's course root for files"

    def add_arguments(self, parser):
        parser.add_argument("workspace_id", type=int, help="Workspace ID to scan")
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full scan instead of incremental",
        )

    def handle(self, *args, **options):
        try:
            workspace = Workspace.objects.get(pk=options["workspace_id"])
        except Workspace.DoesNotExist:
            raise CommandError(f"Workspace with id {options['workspace_id']} not found")

        self.stdout.write(f"Scanning workspace: {workspace.name}")
        self.stdout.write(f"Course root: {workspace.course_root}")

        result = scan_workspace(workspace, incremental=not options["full"])

        self.stdout.write(self.style.SUCCESS(f"Scan complete:"))
        self.stdout.write(f"  Files found: {len(result.files)}")
        self.stdout.write(f"  Directories: {len(result.directories)}")

        if result.change_set:
            self.stdout.write(f"  Added: {len(result.change_set.added)}")
            self.stdout.write(f"  Modified: {len(result.change_set.modified)}")
            self.stdout.write(f"  Deleted: {len(result.change_set.deleted)}")
