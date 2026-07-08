"""Tests for media serving views."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse

from apps.courses.models import Course, CourseNode
from apps.workspaces.models import Workspace


class ServeMediaTest(TestCase):
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

    def test_404_for_nonexistent_course(self):
        response = self.client.get(
            reverse("serve_media", args=[9999, self.video_node.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_404_for_nonexistent_node(self):
        response = self.client.get(
            reverse("serve_media", args=[self.course.pk, 9999])
        )
        self.assertEqual(response.status_code, 404)


class ServeSubtitleTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/tmp/test",
        )

    def test_404_for_missing_subtitle(self):
        response = self.client.get(
            reverse("serve_subtitle", args=[self.course.pk, "nonexistent.vtt"])
        )
        self.assertEqual(response.status_code, 404)
