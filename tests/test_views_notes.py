"""Tests for note views: from subtitle, list partial."""

from pathlib import Path

from django.test import TestCase, Client
from django.urls import reverse

from apps.courses.models import Course, CourseNode
from apps.notes.models import Note
from apps.workspaces.models import Workspace


class NoteFromSubtitleTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/tmp/test",
        )
        self.node = CourseNode.objects.create(
            course=self.course,
            name="video.mp4",
            relative_path="video.mp4",
            node_type="file",
            file_type="video",
        )

    def test_post_creates_note_from_vtt(self, tmp_path=Path("/tmp/test")):
        vtt = tmp_path / "video.vtt"
        vtt.parent.mkdir(parents=True, exist_ok=True)
        vtt.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world\n\n00:00:06.000 --> 00:00:10.000\nGoodbye")

        response = self.client.post(
            reverse("note_from_subtitle", args=[self.course.pk, self.node.pk]),
            {"sub_path": "video.vtt"},
        )
        self.assertEqual(response.status_code, 200)
        note = Note.objects.get(course_node=self.node)
        self.assertIn("Hello world", note.content)
        self.assertIn("Goodbye", note.content)

    def test_post_with_missing_file_returns_204(self):
        response = self.client.post(
            reverse("note_from_subtitle", args=[self.course.pk, self.node.pk]),
            {"sub_path": "nonexistent.vtt"},
        )
        self.assertEqual(response.status_code, 204)

    def test_post_with_empty_path_returns_204(self):
        response = self.client.post(
            reverse("note_from_subtitle", args=[self.course.pk, self.node.pk]),
            {"sub_path": ""},
        )
        self.assertEqual(response.status_code, 204)


class NoteListPartialTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/tmp/test",
        )
        self.node = CourseNode.objects.create(
            course=self.course,
            name="video.mp4",
            relative_path="video.mp4",
            node_type="file",
            file_type="video",
        )

    def test_returns_note_list(self):
        Note.objects.create(course_node=self.node, content="Test note")
        response = self.client.get(
            reverse("note_list_partial", args=[self.course.pk, self.node.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test note")

    def test_empty_state(self):
        response = self.client.get(
            reverse("note_list_partial", args=[self.course.pk, self.node.pk])
        )
        self.assertEqual(response.status_code, 200)
