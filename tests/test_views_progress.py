"""Tests for progress views."""

import json

from django.test import TestCase, Client
from django.urls import reverse

from apps.courses.models import Course, CourseNode
from apps.media.models import MediaMetadata
from apps.progress.models import WatchHistory
from apps.workspaces.models import Workspace


class ProgressViewTestBase(TestCase):
    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/tmp/test",
        )
        self.video_node = CourseNode.objects.create(
            course=self.course,
            name="video.mp4",
            relative_path="video.mp4",
            node_type="file",
            file_type="video",
        )
        self.meta = MediaMetadata.objects.create(
            course_node=self.video_node,
            duration=300.0,
        )


class TestActivity(ProgressViewTestBase):
    def test_renders_default(self):
        response = self.client.get(reverse("activity"))
        self.assertEqual(response.status_code, 200)

    def test_renders_with_days_param(self):
        response = self.client.get(reverse("activity") + "?days=7")
        self.assertEqual(response.status_code, 200)

    def test_renders_with_long_range(self):
        response = self.client.get(reverse("activity") + "?days=365")
        self.assertEqual(response.status_code, 200)


class TestUpdatePosition(ProgressViewTestBase):
    def test_saves_position(self):
        response = self.client.post(
            reverse("update_position", args=[self.video_node.pk]),
            {"position": "100.5"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")

    def test_rejects_invalid_position(self):
        response = self.client.post(
            reverse("update_position", args=[self.video_node.pk]),
            {"position": "-5"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")


class TestMarkFileCompleted(ProgressViewTestBase):
    def test_marks_complete(self):
        response = self.client.post(
            reverse("mark_completed", args=[self.video_node.pk])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "completed")
        wh = WatchHistory.objects.get(course_node=self.video_node)
        self.assertTrue(wh.completed)


class TestFileProgress(ProgressViewTestBase):
    def test_returns_progress(self):
        response = self.client.get(
            reverse("file_progress", args=[self.video_node.pk])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("status", data)


class TestResetProgress(ProgressViewTestBase):
    def test_resets(self):
        WatchHistory.objects.create(
            course_node=self.video_node,
            completed=True,
            duration_watched=300.0,
        )
        response = self.client.post(
            reverse("reset_progress", args=[self.video_node.pk])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "reset")
        self.assertFalse(
            WatchHistory.objects.filter(course_node=self.video_node).exists()
        )
