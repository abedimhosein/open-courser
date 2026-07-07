import logging
from django.db import transaction

from apps.courses.models import CourseNode
from apps.media.models import MediaMetadata
from domain.skills.storage_mapping import resolve_absolute
from domain.skills.media_understanding import extract_metadata, discover_subtitles

log = logging.getLogger(__name__)


@transaction.atomic
def extract_and_save_metadata(node: CourseNode) -> MediaMetadata | None:
    """
    Extract metadata for a CourseNode and persist it.
    """
    if node.file_type not in ("video", "audio"):
        return None

    absolute_path = resolve_absolute(node.course.root_path, node.relative_path)

    extraction = extract_metadata(absolute_path)

    if extraction.error:
        log.debug("Extraction error for %s: %s", node.relative_path, extraction.error)
        return None

    if not extraction.metadata:
        log.debug("No metadata returned for %s", node.relative_path)
        return None

    md = extraction.metadata

    subtitle_paths = []
    for sub in extraction.subtitles:
        subtitle_paths.append(sub.relative_path)

    media_meta, _ = MediaMetadata.objects.update_or_create(
        course_node=node,
        defaults={
            "duration": md.duration,
            "codec": md.codec or "",
            "width": md.width,
            "height": md.height,
            "bitrate": md.bitrate,
            "file_format": md.file_format or "",
            "subtitle_paths": subtitle_paths,
        },
    )

    if not subtitle_paths:
        subtitles = discover_subtitles(absolute_path, node.course.root_path)
        if subtitles:
            media_meta.subtitle_paths = [s.relative_path for s in subtitles]
            media_meta.save(update_fields=["subtitle_paths"])

    return media_meta
