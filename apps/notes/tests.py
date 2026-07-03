import markdown
from django.test import TestCase, Client
from django.urls import reverse

from apps.notes.models import Note
from apps.courses.models import Course, CourseNode
from apps.workspaces.models import Workspace


class NoteModelTest(TestCase):
    """Tests for the Note model."""

    def setUp(self):
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/courses/test",
        )
        self.node = CourseNode.objects.create(
            course=self.course,
            name="lecture.mp4",
            relative_path="lecture.mp4",
            node_type="file",
            file_type="video",
        )

    def test_create_note(self):
        """Test creating a note."""
        note = Note.objects.create(
            course_node=self.node,
            content="This is a test note",
        )
        self.assertEqual(note.content, "This is a test note")
        self.assertEqual(note.course_node, self.node)

    def test_note_str(self):
        """Test note string representation."""
        note = Note.objects.create(
            course_node=self.node,
            content="Short note",
        )
        self.assertIn("Short note", str(note))

    def test_note_ordering(self):
        """Test notes are ordered by most recent first."""
        from django.utils import timezone
        import datetime

        note1 = Note.objects.create(
            course_node=self.node,
            content="First note",
        )
        # Update timestamp to ensure ordering
        note1.created_at = timezone.now() - datetime.timedelta(hours=1)
        note1.save(update_fields=["created_at"])

        note2 = Note.objects.create(
            course_node=self.node,
            content="Second note",
        )
        notes = list(self.node.notes.all())
        self.assertEqual(notes[0], note2)
        self.assertEqual(notes[1], note1)


class NoteCreateViewTest(TestCase):
    """Tests for creating notes."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/courses/test",
        )
        self.node = CourseNode.objects.create(
            course=self.course,
            name="lecture.mp4",
            relative_path="lecture.mp4",
            node_type="file",
            file_type="video",
        )

    def test_create_note_success(self):
        """Test creating a note via POST."""
        response = self.client.post(
            reverse("note_create", kwargs={"course_pk": self.course.pk, "node_pk": self.node.pk}),
            {"content": "Test note content"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Note.objects.filter(course_node=self.node, content="Test note content").exists())

    def test_create_note_empty_content(self):
        """Test creating a note with empty content shows error."""
        response = self.client.post(
            reverse("note_create", kwargs={"course_pk": self.course.pk, "node_pk": self.node.pk}),
            {"content": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Note.objects.count(), 0)

    def test_create_note_get_not_allowed(self):
        """Test GET request is not allowed on create."""
        response = self.client.get(
            reverse("note_create", kwargs={"course_pk": self.course.pk, "node_pk": self.node.pk}),
        )
        self.assertEqual(response.status_code, 405)


class NoteEditViewTest(TestCase):
    """Tests for editing notes."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/courses/test",
        )
        self.node = CourseNode.objects.create(
            course=self.course,
            name="lecture.mp4",
            relative_path="lecture.mp4",
            node_type="file",
            file_type="video",
        )
        self.note = Note.objects.create(
            course_node=self.node,
            content="Original content",
        )

    def test_edit_note_get(self):
        """Test GET request returns edit form."""
        response = self.client.get(
            reverse("note_edit", kwargs={"pk": self.note.pk}),
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_note_post(self):
        """Test POST request updates the note."""
        response = self.client.post(
            reverse("note_edit", kwargs={"pk": self.note.pk}),
            {"content": "Updated content"},
        )
        self.assertEqual(response.status_code, 200)
        self.note.refresh_from_db()
        self.assertEqual(self.note.content, "Updated content")


class NoteDeleteViewTest(TestCase):
    """Tests for deleting notes."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/courses/test",
        )
        self.node = CourseNode.objects.create(
            course=self.course,
            name="lecture.mp4",
            relative_path="lecture.mp4",
            node_type="file",
            file_type="video",
        )
        self.note = Note.objects.create(
            course_node=self.node,
            content="Note to delete",
        )

    def test_delete_note(self):
        """Test deleting a note."""
        response = self.client.post(
            reverse("note_delete", kwargs={"pk": self.note.pk}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Note.objects.filter(pk=self.note.pk).exists())


class NotesSearchViewTest(TestCase):
    """Tests for notes search."""

    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/courses/test",
        )
        self.node = CourseNode.objects.create(
            course=self.course,
            name="lecture.mp4",
            relative_path="lecture.mp4",
            node_type="file",
            file_type="video",
        )
        self.note = Note.objects.create(
            course_node=self.node,
            content="Important Python concept",
        )

    def test_search_page_loads(self):
        """Test search page loads."""
        response = self.client.get(reverse("notes_search"))
        self.assertEqual(response.status_code, 200)

    def test_search_by_content(self):
        """Test search finds notes by content."""
        response = self.client.get(reverse("notes_search") + "?q=Python")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["notes"]), 1)

    def test_search_by_workspace(self):
        """Test filtering by workspace."""
        response = self.client.get(reverse("notes_search") + f"?workspace={self.workspace.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["notes"]), 1)

    def test_search_by_course(self):
        """Test filtering by course."""
        response = self.client.get(reverse("notes_search") + f"?course={self.course.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["notes"]), 1)

    def test_search_no_results(self):
        """Test search with no matching results."""
        response = self.client.get(reverse("notes_search") + "?q=nonexistent")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["notes"]), 0)
