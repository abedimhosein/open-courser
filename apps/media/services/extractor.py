"""
Media Metadata Extraction Service

Owned by: Backend Django Agent (orchestration)
Delegates to: Media Processing Agent (Media Understanding)

Purpose: Orchestrate media metadata extraction using ffprobe and
         persist results to the database.
"""

import mimetypes

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

    md = result.metadata
    metadata, _ = MediaMetadata.objects.update_or_create(
        relative_path=course_file.relative_path,
        defaults={
            "duration": md.duration if md else None,
            "codec": (md.codec or "") if md else "",
            "width": md.width if md else None,
            "height": md.height if md else None,
            "bitrate": md.bitrate if md else None,
            "file_format": (md.file_format or "") if md else "",
            "subtitle_paths": [s.relative_path for s in subtitles],
        },
    )

    # Update the CourseFile with extracted metadata
    if result.metadata:
        update_fields = {}

        if result.metadata.duration is not None:
            update_fields["duration"] = result.metadata.duration

        mime_type, _ = mimetypes.guess_type(str(absolute_path))
        if mime_type:
            update_fields["mime_type"] = mime_type

        meta = {
            k: v
            for k, v in {
                "codec": result.metadata.codec,
                "width": result.metadata.width,
                "height": result.metadata.height,
                "bitrate": result.metadata.bitrate,
                "file_format": result.metadata.file_format,
                "has_audio": result.metadata.has_audio,
                "has_video": result.metadata.has_video,
            }.items()
            if v is not None and v is not False
        }
        if meta:
            update_fields["metadata"] = meta

        if update_fields:
            CourseFile.objects.filter(pk=course_file.pk).update(**update_fields)

    return metadata
