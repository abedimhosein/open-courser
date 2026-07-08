"""Tests for the scanner service."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.courses.models import Course, CourseNode
from apps.workspaces.models import Workspace
from apps.courses.services.scanner import (
    _classify_file_type,
    _update_course_durations,
    scan_course,
)


class TestClassifyFileType(TestCase):
    def test_classifies_video(self):
        assert _classify_file_type(".mp4") == "video"
        assert _classify_file_type(".mkv") == "video"

    def test_classifies_audio(self):
        assert _classify_file_type(".mp3") == "audio"
        assert _classify_file_type(".wav") == "audio"

    def test_classifies_subtitle(self):
        assert _classify_file_type(".srt") == "subtitle"
        assert _classify_file_type(".vtt") == "subtitle"

    def test_classifies_document(self):
        assert _classify_file_type(".pdf") == "document"
        assert _classify_file_type(".docx") == "document"

    def test_classifies_image(self):
        assert _classify_file_type(".jpg") == "image"
        assert _classify_file_type(".png") == "image"

    def test_classifies_source_code(self):
        assert _classify_file_type(".py") == "source_code"
        assert _classify_file_type(".js") == "source_code"

    def test_classifies_unknown_as_other(self):
        assert _classify_file_type(".xyz") == "other"


class TestUpdateCourseDurations(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(name="Test")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/tmp/test",
        )

    def test_sets_zero_when_no_metadata(self):
        _update_course_durations(self.course)
        self.course.refresh_from_db()
        assert self.course.total_duration == 0
        assert self.course.watched_duration == 0

    def test_sums_total_from_metadata(self):
        from apps.courses.models import CourseNode
        from apps.media.models import MediaMetadata

        node = CourseNode.objects.create(
            course=self.course,
            name="video.mp4",
            relative_path="video.mp4",
            node_type="file",
            file_type="video",
        )
        MediaMetadata.objects.create(course_node=node, duration=120.0)

        node2 = CourseNode.objects.create(
            course=self.course,
            name="audio.mp3",
            relative_path="audio.mp3",
            node_type="file",
            file_type="audio",
        )
        MediaMetadata.objects.create(course_node=node2, duration=60.0)

        _update_course_durations(self.course)
        self.course.refresh_from_db()
        assert self.course.total_duration == 180.0


class TestScanCourse(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(name="Test")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/tmp/nonexistent",
        )

    def test_returns_empty_for_missing_root(self):
        result = scan_course(self.course)
        assert result.total_nodes == 0
        assert result.added == 0
