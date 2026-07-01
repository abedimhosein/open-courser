"""Tests for the Progress Tracking skill."""

from domain.skills.progress_tracking import (
    calculate_file_progress,
    calculate_course_progress,
    LearningStatus,
    PlaybackEvent,
    update_watched_duration,
    validate_playback_position,
)


class TestCalculateFileProgress:
    def test_returns_not_started_when_below_threshold(self):
        result = calculate_file_progress(watched_seconds=10, total_duration=1000, last_position=10)
        assert result.status == LearningStatus.NOT_STARTED
        assert result.watched_percentage == 1.0

    def test_returns_in_progress_when_above_started_threshold(self):
        result = calculate_file_progress(watched_seconds=100, total_duration=1000, last_position=100)
        assert result.status == LearningStatus.IN_PROGRESS
        assert result.watched_percentage == 10.0

    def test_returns_completed_when_above_completion_threshold(self):
        result = calculate_file_progress(watched_seconds=960, total_duration=1000, last_position=960)
        assert result.status == LearningStatus.COMPLETED
        assert result.watched_percentage == 96.0

    def test_caps_percentage_at_100(self):
        result = calculate_file_progress(watched_seconds=2000, total_duration=1000, last_position=1000)
        assert result.status == LearningStatus.COMPLETED
        assert result.watched_percentage == 100.0

    def test_returns_none_percentage_without_duration(self):
        result = calculate_file_progress(watched_seconds=100, total_duration=None, last_position=100)
        assert result.watched_percentage is None
        assert result.status == LearningStatus.NOT_STARTED


class TestCalculateCourseProgress:
    def test_returns_zero_for_no_files(self):
        result = calculate_course_progress([], [])
        assert result.total_duration == 0
        assert result.overall_percentage == 0.0
        assert result.total_files == 0

    def test_calculates_weighted_average(self):
        fp1 = calculate_file_progress(100, 100, 100)  # completed
        fp2 = calculate_file_progress(0, 100, 0)       # not started

        result = calculate_course_progress([fp1, fp2], [100, 100])
        assert result.total_duration == 200
        assert result.completed_files == 1
        assert result.total_files == 2
        assert result.overall_percentage == 50.0


class TestUpdateWatchedDuration:
    def test_adds_forward_progress(self):
        result = update_watched_duration(
            current_watched=50.0,
            event=PlaybackEvent(position=100.0, duration=200.0),
            previous_position=50.0,
        )
        assert result == 100.0

    def test_ignores_backward_seek(self):
        result = update_watched_duration(
            current_watched=100.0,
            event=PlaybackEvent(position=30.0, duration=200.0),
            previous_position=100.0,
        )
        assert result == 100.0


class TestValidatePlaybackPosition:
    def test_accepts_valid_position(self):
        assert validate_playback_position(50.0, 100.0) is True

    def test_rejects_negative_position(self):
        assert validate_playback_position(-1.0, 100.0) is False

    def test_rejects_position_exceeding_duration(self):
        assert validate_playback_position(101.0, 100.0) is False

    def test_accepts_position_without_duration(self):
        assert validate_playback_position(50.0, None) is True
