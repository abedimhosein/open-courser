"""
Progress Tracking Skill

Owned by: Progress Logic Agent
Purpose: Track playback state, compute watched percentage,
         determine learning status, and calculate course progress.
"""

from dataclasses import dataclass
from enum import Enum

COMPLETION_THRESHOLD = 95.0
STARTED_THRESHOLD = 5.0


class LearningStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True)
class FileProgress:
    watched_duration: float
    watched_percentage: float | None
    status: LearningStatus
    last_position: float


@dataclass(frozen=True)
class CourseProgress:
    total_duration: float
    completed_duration: float
    overall_percentage: float
    total_files: int
    completed_files: int


@dataclass(frozen=True)
class PlaybackEvent:
    position: float
    duration: float | None


def calculate_file_progress(watched_seconds: float, total_duration: float | None, last_position: float) -> FileProgress:
    """
    Calculate progress for a single media file.

    If total_duration is None or 0, percentage is None.
    """
    if not total_duration or total_duration <= 0:
        return FileProgress(
            watched_duration=watched_seconds,
            watched_percentage=None,
            status=LearningStatus.NOT_STARTED,
            last_position=last_position,
        )

    pct = min((watched_seconds / total_duration) * 100, 100.0)

    if pct >= COMPLETION_THRESHOLD:
        status = LearningStatus.COMPLETED
    elif pct >= STARTED_THRESHOLD:
        status = LearningStatus.IN_PROGRESS
    else:
        status = LearningStatus.NOT_STARTED

    return FileProgress(
        watched_duration=watched_seconds,
        watched_percentage=pct,
        status=status,
        last_position=last_position,
    )


def calculate_course_progress(file_progresses: list[FileProgress], durations: list[float | None]) -> CourseProgress:
    """
    Calculate overall progress for a course.

    Uses duration-weighted progress.
    """
    total_duration = sum(d for d in durations if d is not None and d > 0)
    completed_duration = 0.0
    total_files = len(file_progresses)
    completed_files = 0

    for fp, dur in zip(file_progresses, durations):
        effective_duration = dur if dur is not None and dur > 0 else 0
        completed_duration += effective_duration * (
            fp.watched_percentage / 100.0 if fp.watched_percentage is not None else 0.0
        )
        if fp.status == LearningStatus.COMPLETED:
            completed_files += 1

    if total_duration > 0:
        duration_pct = min((completed_duration / total_duration) * 100, 100.0)
    else:
        duration_pct = 0.0

    file_pct = (completed_files / total_files) * 100 if total_files > 0 else 0.0

    overall_pct = max(duration_pct, file_pct)

    return CourseProgress(
        total_duration=total_duration,
        completed_duration=completed_duration,
        overall_percentage=overall_pct,
        total_files=total_files,
        completed_files=completed_files,
    )


def update_watched_duration(current_watched: float, event: PlaybackEvent, previous_position: float) -> float:
    """
    Calculate incremental watched duration from a playback event.

    Only counts forward progress to avoid counting seeking backwards.
    """
    if event.position > previous_position:
        delta = event.position - previous_position
        return current_watched + delta

    return current_watched


def validate_playback_position(position: float, duration: float | None) -> bool:
    """
    Validate that a playback position is within acceptable bounds.
    """
    if position < 0:
        return False
    if duration is not None and duration > 0 and position > duration:
        return False
    return True
