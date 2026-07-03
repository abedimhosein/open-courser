from django.test import TestCase, Client
from django.urls import reverse

from apps.courses.models import Course, CourseNode
from apps.workspaces.models import Workspace


class CourseSearchViewTest(TestCase):
    """Tests for the course search view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course1 = Course.objects.create(
            workspace=self.workspace,
            title="Docker Fundamentals",
            root_path="/courses/docker",
        )
        self.course2 = Course.objects.create(
            workspace=self.workspace,
            title="Python Advanced",
            root_path="/courses/python",
        )
        self.course3 = Course.objects.create(
            workspace=self.workspace,
            title="Docker Swarm",
            root_path="/courses/docker-swarm",
        )

    def test_search_page_loads(self):
        """Test that search page loads successfully."""
        response = self.client.get(reverse("course_search"))
        self.assertEqual(response.status_code, 200)

    def test_search_with_empty_query(self):
        """Test search with empty query returns no results."""
        response = self.client.get(reverse("course_search"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["results"]), 0)

    def test_search_finds_matching_courses(self):
        """Test search finds courses matching the query."""
        response = self.client.get(reverse("course_search") + "?q=docker")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["results"]), 2)

    def test_search_is_case_insensitive(self):
        """Test search is case insensitive."""
        response = self.client.get(reverse("course_search") + "?q=DOCKER")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["results"]), 2)

    def test_search_with_no_matches(self):
        """Test search with query matching no courses."""
        response = self.client.get(reverse("course_search") + "?q=nonexistent")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["results"]), 0)

    def test_search_query_is_preserved(self):
        """Test that the search query is preserved in context."""
        response = self.client.get(reverse("course_search") + "?q=docker")
        self.assertEqual(response.context["query"], "docker")

    def test_search_strips_whitespace(self):
        """Test that whitespace is stripped from query."""
        response = self.client.get(reverse("course_search") + "?q=  docker  ")
        self.assertEqual(response.context["query"], "docker")
        self.assertEqual(len(response.context["results"]), 2)

    def test_search_results_contain_progress(self):
        """Test that search results contain progress data."""
        response = self.client.get(reverse("course_search") + "?q=docker")
        for result in response.context["results"]:
            self.assertIn("course", result)
            self.assertIn("progress", result)


class CourseCreateViewTest(TestCase):
    """Tests for the course create view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")

    def test_create_page_loads(self):
        """Test that create page loads successfully."""
        response = self.client.get(
            reverse("course_create", kwargs={"workspace_pk": self.workspace.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_create_course_with_valid_data(self):
        """Test creating a course with valid data."""
        response = self.client.post(
            reverse("course_create", kwargs={"workspace_pk": self.workspace.pk}),
            {
                "title": "New Course",
                "root_path": "/courses/new",
                "description": "A test course",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(title="New Course").exists())

    def test_create_course_without_title(self):
        """Test creating a course without title shows error."""
        response = self.client.post(
            reverse("course_create", kwargs={"workspace_pk": self.workspace.pk}),
            {
                "title": "",
                "root_path": "/courses/new",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Title and root path are required")

    def test_create_course_without_root_path(self):
        """Test creating a course without root_path shows error."""
        response = self.client.post(
            reverse("course_create", kwargs={"workspace_pk": self.workspace.pk}),
            {
                "title": "New Course",
                "root_path": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Title and root path are required")

    def test_create_course_redirects_to_detail(self):
        """Test that successful creation redirects to course detail."""
        response = self.client.post(
            reverse("course_create", kwargs={"workspace_pk": self.workspace.pk}),
            {
                "title": "New Course",
                "root_path": "/courses/new",
            },
        )
        course = Course.objects.get(title="New Course")
        self.assertRedirects(response, reverse("course_detail", kwargs={"pk": course.pk}))


class CourseEditViewTest(TestCase):
    """Tests for the course edit view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Original Title",
            root_path="/courses/test",
        )

    def test_edit_page_loads(self):
        """Test that edit page loads successfully."""
        response = self.client.get(
            reverse("course_edit", kwargs={"pk": self.course.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_course_updates_title(self):
        """Test editing course updates the title."""
        response = self.client.post(
            reverse("course_edit", kwargs={"pk": self.course.pk}),
            {
                "workspace": self.workspace.pk,
                "title": "Updated Title",
                "description": "Updated description",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Updated Title")

    def test_edit_course_redirects_to_detail(self):
        """Test that successful edit redirects to course detail."""
        response = self.client.post(
            reverse("course_edit", kwargs={"pk": self.course.pk}),
            {
                "workspace": self.workspace.pk,
                "title": "Updated Title",
            },
        )
        self.assertRedirects(response, reverse("course_detail", kwargs={"pk": self.course.pk}))


class CourseDeleteViewTest(TestCase):
    """Tests for the course delete view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Course to Delete",
            root_path="/courses/test",
        )

    def test_delete_page_loads(self):
        """Test that delete confirmation page loads."""
        response = self.client.get(
            reverse("course_delete", kwargs={"pk": self.course.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_course(self):
        """Test deleting a course."""
        response = self.client.post(
            reverse("course_delete", kwargs={"pk": self.course.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())

    def test_delete_redirects_to_workspace(self):
        """Test that deletion redirects to workspace detail."""
        response = self.client.post(
            reverse("course_delete", kwargs={"pk": self.course.pk})
        )
        self.assertRedirects(
            response,
            reverse("workspace_detail", kwargs={"pk": self.workspace.pk}),
        )


class CourseDetailViewTest(TestCase):
    """Tests for the course detail view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/courses/test",
        )

    def test_detail_page_loads(self):
        """Test that detail page loads successfully."""
        response = self.client.get(
            reverse("course_detail", kwargs={"pk": self.course.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_returns_404_for_nonexistent(self):
        """Test that detail returns 404 for nonexistent course."""
        response = self.client.get(
            reverse("course_detail", kwargs={"pk": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_includes_course_data(self):
        """Test that detail page includes course data."""
        response = self.client.get(
            reverse("course_detail", kwargs={"pk": self.course.pk})
        )
        self.assertEqual(response.context["course"], self.course)


class CourseScanViewTest(TestCase):
    """Tests for the course scan view."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/nonexistent/path",
        )

    def test_scan_returns_hx_refresh(self):
        """Test that scan returns HX-Refresh header."""
        response = self.client.get(
            reverse("course_scan", kwargs={"pk": self.course.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Refresh"], "true")
