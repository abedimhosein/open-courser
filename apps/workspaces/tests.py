from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse

from apps.workspaces.models import Workspace
from apps.courses.models import Course


class WorkspaceListViewTest(TestCase):
    """Tests for the workspace list view."""

    def setUp(self):
        self.client = Client()

    def test_list_page_loads(self):
        """Test that list page loads successfully."""
        response = self.client.get(reverse("workspace_list"))
        self.assertEqual(response.status_code, 200)

    def test_list_shows_workspaces(self):
        """Test that list shows workspaces."""
        Workspace.objects.create(name="Workspace 1")
        Workspace.objects.create(name="Workspace 2")
        response = self.client.get(reverse("workspace_list"))
        self.assertEqual(len(response.context["page_obj"]), 2)

    def test_list_empty_when_no_workspaces(self):
        """Test that list is empty when no workspaces exist."""
        response = self.client.get(reverse("workspace_list"))
        self.assertEqual(len(response.context["page_obj"]), 0)


class WorkspaceDetailViewTest(TestCase):
    """Tests for the workspace detail view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(
            name="Test Workspace",
            description="A test workspace",
        )

    def test_detail_page_loads(self):
        """Test that detail page loads successfully."""
        response = self.client.get(
            reverse("workspace_detail", kwargs={"pk": self.workspace.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_returns_404_for_nonexistent(self):
        """Test that detail returns 404 for nonexistent workspace."""
        response = self.client.get(
            reverse("workspace_detail", kwargs={"pk": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_shows_courses(self):
        """Test that detail page shows courses."""
        Course.objects.create(
            workspace=self.workspace,
            title="Course 1",
            root_path="/courses/1",
        )
        Course.objects.create(
            workspace=self.workspace,
            title="Course 2",
            root_path="/courses/2",
        )
        response = self.client.get(
            reverse("workspace_detail", kwargs={"pk": self.workspace.pk})
        )
        self.assertEqual(len(response.context["course_list"]), 2)

    def test_detail_sort_by_name(self):
        """Test that detail can sort courses by name."""
        Course.objects.create(
            workspace=self.workspace,
            title="Z Course",
            root_path="/courses/z",
        )
        Course.objects.create(
            workspace=self.workspace,
            title="A Course",
            root_path="/courses/a",
        )
        response = self.client.get(
            reverse("workspace_detail", kwargs={"pk": self.workspace.pk})
            + "?sort=name"
        )
        self.assertEqual(response.context["current_sort"], "name")
        titles = [item["course"].title for item in response.context["course_list"]]
        self.assertEqual(titles, ["A Course", "Z Course"])

    def test_detail_sort_by_progress(self):
        """Test that detail can sort courses by progress."""
        response = self.client.get(
            reverse("workspace_detail", kwargs={"pk": self.workspace.pk})
            + "?sort=progress"
        )
        self.assertEqual(response.context["current_sort"], "progress")

    def test_detail_invalid_sort_defaults_to_progress(self):
        """Test that invalid sort parameter defaults to progress."""
        response = self.client.get(
            reverse("workspace_detail", kwargs={"pk": self.workspace.pk})
            + "?sort=invalid"
        )
        self.assertEqual(response.context["current_sort"], "progress")


class WorkspaceCreateViewTest(TestCase):
    """Tests for the workspace create view."""

    def setUp(self):
        self.client = Client()

    def test_create_page_loads(self):
        """Test that create page loads successfully."""
        response = self.client.get(reverse("workspace_create"))
        self.assertEqual(response.status_code, 200)

    def test_create_workspace_with_valid_data(self):
        """Test creating a workspace with valid data."""
        response = self.client.post(
            reverse("workspace_create"),
            {
                "name": "New Workspace",
                "description": "A new workspace",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Workspace.objects.filter(name="New Workspace").exists())

    def test_create_workspace_without_name(self):
        """Test creating a workspace without name shows error."""
        response = self.client.post(
            reverse("workspace_create"),
            {
                "name": "",
                "description": "Some description",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workspace name is required")

    def test_create_workspace_redirects_to_detail(self):
        """Test that successful creation redirects to workspace detail."""
        response = self.client.post(
            reverse("workspace_create"),
            {"name": "New Workspace"},
        )
        workspace = Workspace.objects.get(name="New Workspace")
        self.assertRedirects(
            response,
            reverse("workspace_detail", kwargs={"pk": workspace.pk}),
        )


class WorkspaceEditViewTest(TestCase):
    """Tests for the workspace edit view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(
            name="Original Name",
            description="Original description",
        )

    def test_edit_page_loads(self):
        """Test that edit page loads successfully."""
        response = self.client.get(
            reverse("workspace_edit", kwargs={"pk": self.workspace.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_updates_workspace(self):
        """Test editing workspace updates the data."""
        response = self.client.post(
            reverse("workspace_edit", kwargs={"pk": self.workspace.pk}),
            {
                "name": "Updated Name",
                "description": "Updated description",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.name, "Updated Name")

    def test_edit_redirects_to_detail(self):
        """Test that successful edit redirects to workspace detail."""
        response = self.client.post(
            reverse("workspace_edit", kwargs={"pk": self.workspace.pk}),
            {"name": "Updated Name"},
        )
        self.assertRedirects(
            response,
            reverse("workspace_detail", kwargs={"pk": self.workspace.pk}),
        )


class WorkspaceDeleteViewTest(TestCase):
    """Tests for the workspace delete view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Workspace to Delete")

    def test_delete_page_loads(self):
        """Test that delete confirmation page loads."""
        response = self.client.get(
            reverse("workspace_delete", kwargs={"pk": self.workspace.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_workspace(self):
        """Test deleting a workspace."""
        response = self.client.post(
            reverse("workspace_delete", kwargs={"pk": self.workspace.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Workspace.objects.filter(pk=self.workspace.pk).exists())

    def test_delete_redirects_to_list(self):
        """Test that deletion redirects to workspace list."""
        response = self.client.post(
            reverse("workspace_delete", kwargs={"pk": self.workspace.pk})
        )
        self.assertRedirects(response, reverse("workspace_list"))


class WorkspaceImportCoursesTest(TestCase):
    """Tests for the workspace course import functionality."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Import Workspace")

    def test_import_creates_courses_from_subdirectories(self):
        """Test that import creates courses from subdirectories."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "courses"
            root.mkdir()
            (root / "Course 1").mkdir()
            (root / "Course 2").mkdir()
            (root / ".hidden").mkdir()
            (root / "_backup").mkdir()

            response = self.client.post(
                reverse("workspace_create"),
                {
                    "name": "Import Workspace 2",
                    "auto_import": "1",
                    "root_path": str(root),
                },
            )
            self.assertEqual(response.status_code, 302)
            # Should create courses for Course 1 and Course 2 only
            self.assertEqual(
                Course.objects.filter(workspace__name="Import Workspace 2").count(),
                2,
            )

    def test_import_skips_hidden_directories(self):
        """Test that import skips hidden directories (starting with . or _)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "courses"
            root.mkdir()
            (root / ".hidden").mkdir()
            (root / "_backup").mkdir()
            (root / "Visible").mkdir()

            response = self.client.post(
                reverse("workspace_create"),
                {
                    "name": "Import Workspace 3",
                    "auto_import": "1",
                    "root_path": str(root),
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                Course.objects.filter(workspace__name="Import Workspace 3").count(),
                1,
            )

    def test_import_requires_root_path_when_enabled(self):
        """Test that import requires root path when auto_import is enabled."""
        response = self.client.post(
            reverse("workspace_create"),
            {
                "name": "Import Workspace 4",
                "auto_import": "1",
                "root_path": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Root directory is required")

    def test_import_skips_when_auto_import_disabled(self):
        """Test that import is skipped when auto_import is disabled."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "courses"
            root.mkdir()
            (root / "Course 1").mkdir()

            response = self.client.post(
                reverse("workspace_create"),
                {
                    "name": "No Import Workspace",
                    "root_path": str(root),
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                Course.objects.filter(workspace__name="No Import Workspace").count(),
                0,
            )


class BrowseDirectoriesViewTest(TestCase):
    """Tests for the directory browser view."""

    def setUp(self):
        self.client = Client()

    def test_browse_loads_with_configured_roots(self):
        """Test that browse loads with configured course roots."""
        with patch(
            "apps.workspaces.views.settings"
        ) as mock_settings:
            mock_settings.COURSE_ROOTS = [
                {
                    "host_path": "C:/Users/Amir/Downloads",
                    "container_path": "/courses/0",
                },
            ]
            response = self.client.get(reverse("browse_directories"))
            self.assertEqual(response.status_code, 200)

    def test_browse_filters_directories(self):
        """Test that browse filters directories by query."""
        with patch(
            "apps.workspaces.views.settings"
        ) as mock_settings:
            mock_settings.COURSE_ROOTS = [
                {
                    "host_path": "C:/Users/Amir/Downloads",
                    "container_path": "/courses/0",
                },
                {
                    "host_path": "C:/Users/Amir/Videos",
                    "container_path": "/courses/1",
                },
            ]
            response = self.client.get(
                reverse("browse_directories") + "?q=downloads"
            )
            self.assertEqual(response.status_code, 200)

    def test_browse_with_specific_path(self):
        """Test browse with a specific path parameter."""
        response = self.client.get(
            reverse("browse_directories") + "?path=/tmp"
        )
        self.assertEqual(response.status_code, 200)

    def test_browse_handles_nonexistent_path(self):
        """Test browse handles nonexistent path gracefully."""
        response = self.client.get(
            reverse("browse_directories") + "?path=/nonexistent/path"
        )
        self.assertEqual(response.status_code, 200)


class WorkspaceScanAllViewTest(TestCase):
    """Tests for the workspace scan all view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Scan Workspace")

    def test_scan_all_returns_200(self):
        """Test that scan all returns 200."""
        response = self.client.get(
            reverse("workspace_scan", kwargs={"pk": self.workspace.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_scan_all_includes_scan_summary(self):
        """Test that scan all includes scan summary in response."""
        Course.objects.create(
            workspace=self.workspace,
            title="Course 1",
            root_path="/nonexistent/path",
        )
        response = self.client.get(
            reverse("workspace_scan", kwargs={"pk": self.workspace.pk})
        )
        self.assertIn("scan_summary", response.context)
