"""
Media Metadata Extraction Service

Owned by: Backend Django Agent (orchestration)
Delegates to: Media Processing Agent (Media Understanding)

Purpose: Orchestrate media metadata extraction using ffprobe and
         persist results to the database.
"""

from pathlib import Path

from apps.courses.models import CourseFile
from apps.media.models import MediaMetadata
from domain.skills.media_understanding import (
    extract_metadata,
    discover_subtitles,
)
from domain.skills.storage_mapping import resolve_absolute


def extract_and_save_metadata(course_file: CourseFile) -> MediaMetadata | None:
    """
    Extract metadata for a single CourseFile and save to MediaMetadata cache.

    Returns the MediaMetadata record or None on failure.
    """
    course = course_file.course
    workspace = course.workspace

    try:
        absolute_path = resolve_absolute(workspace.course_root, course_file.relative_path)
    except Exception:
        return None

    result = extract_metadata(absolute_path)

    if result.metadata is None and not result.is_supported:
        return None

    subtitles = discover_subtitles(absolute_path, workspace.course_root)

    metadata, _ = MediaMetadata.objects.update_or_create(
        relative_path=course_file.relative_path,
        defaults={
            "duration": result.metadata.duration if result.metadata else None,
            "codec": result.metadata.codec if result.metadata else "",
            "width": result.metadata.width if result.metadata else None,
            "height": result.metadata.height if result.metadata else None,
            "bitrate": result.metadata.bitrate if result.metadata else None,
            "file_format": result.metadata.file_format if result.metadata else "",
            "subtitle_paths": [s.relative_path for s in subtitles],
        },
    )

    # Update the CourseFile duration if available
    if result.metadata and result.metadata.duration:
        CourseFile.objects.filter(pk=course_file.pk).update(
            duration=result.metadata.duration
        )

    return metadata


def batch_extract_metadata(course_files: list[CourseFile]) -> int:
    """
    Extract metadata for a list of CourseFiles.

    Returns the count of successfully extracted files.
    """
    count = 0
    for cf in course_files:
        if extract_and_save_metadata(cf) is not None:
            count += 1
    return count
