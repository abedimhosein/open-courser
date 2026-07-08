"""Tests for the progress tracker service."""

from django.test import TestCase

from apps.courses.models import Course, CourseNode
from apps.media.models import MediaMetadata
from apps.progress.models import WatchHistory
from apps.workspaces.models import Workspace
from apps.progress.services.tracker import (
    record_playback_position,
    mark_completed,
    get_file_progress,
    get_course_progress,
    reset_file_progress,
)


class TrackerTestBase(TestCase):
    def setUp(self):
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


class TestRecordPlaybackPosition(TrackerTestBase):
    def test_creates_watch_history(self):
        record_playback_position(self.video_node, 50.0)
        wh = WatchHistory.objects.get(course_node=self.video_node)
        assert wh.position == 50.0

    def test_updates_existing_watch(self):
        record_playback_position(self.video_node, 50.0)
        record_playback_position(self.video_node, 100.0)
        wh = WatchHistory.objects.get(course_node=self.video_node)
        assert wh.position == 100.0

    def test_rejects_invalid_position(self):
        result = record_playback_position(self.video_node, -1.0)
        assert result is None

    def test_rejects_directory_node(self):
        dir_node = CourseNode.objects.create(
            course=self.course,
            name="subdir",
            relative_path="subdir",
            node_type="directory",
        )
        result = record_playback_position(dir_node, 10.0)
        assert result is None


class TestMarkCompleted(TrackerTestBase):
    def test_sets_completed(self):
        mark_completed(self.video_node)
        wh = WatchHistory.objects.get(course_node=self.video_node)
        assert wh.completed is True
        assert wh.duration_watched == 300.0

    def test_creates_new_if_not_exists(self):
        mark_completed(self.video_node)
        assert WatchHistory.objects.filter(course_node=self.video_node).exists()


class TestGetFileProgress(TrackerTestBase):
    def test_returns_not_started(self):
        progress = get_file_progress(self.video_node)
        assert progress["status"] == "not_started"

    def test_returns_in_progress(self):
        record_playback_position(self.video_node, 50.0)
        record_playback_position(self.video_node, 100.0)
        progress = get_file_progress(self.video_node)
        assert progress["status"] == "in_progress"

    def test_returns_completed(self):
        mark_completed(self.video_node)
        progress = get_file_progress(self.video_node)
        assert progress["status"] == "completed"
        assert progress["watched_percentage"] == 100.0


class TestGetCourseProgress(TrackerTestBase):
    def test_returns_none_for_empty_course(self):
        empty_course = Course.objects.create(
            workspace=self.workspace,
            title="Empty",
            root_path="/tmp/empty",
        )
        assert get_course_progress(empty_course) is None

    def test_returns_progress_dict(self):
        progress = get_course_progress(self.course)
        assert progress is not None
        assert "total_duration" in progress
        assert "completed_duration" in progress
        assert "overall_percentage" in progress
        assert "total_files" in progress

    def test_calculates_completion(self):
        mark_completed(self.video_node)
        progress = get_course_progress(self.course)
        assert progress["completed_files"] == 1
        assert progress["total_files"] == 1
        assert progress["overall_percentage"] == 100.0


class TestResetFileProgress(TrackerTestBase):
    def test_deletes_watch_history(self):
        mark_completed(self.video_node)
        assert WatchHistory.objects.filter(course_node=self.video_node).exists()
        reset_file_progress(self.video_node)
        assert not WatchHistory.objects.filter(course_node=self.video_node).exists()

    def test_ignores_directory_node(self):
        dir_node = CourseNode.objects.create(
            course=self.course,
            name="subdir",
            relative_path="subdir",
            node_type="directory",
        )
        reset_file_progress(dir_node)  # Should not raise
