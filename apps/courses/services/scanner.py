from dataclasses import dataclass
from pathlib import Path

from django.db import transaction

from apps.courses.models import Course, CourseNode
from apps.media.services.extractor import extract_and_save_metadata
from domain.skills.content_discovery import scan_directory
from domain.skills.storage_mapping import normalize_relative_path, translate_to_docker_path

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass"}
DOCUMENT_EXTENSIONS = {".pdf", ".epub", ".doc", ".docx", ".txt", ".md"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"}
SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".html", ".css", ".scss", ".java", ".cpp", ".c", ".h", ".rs", ".go", ".rb", ".php"}

CONTENT_EXTENSIONS = VIDEO_EXTENSIONS | {".pdf", ".docx", ".html"}

MIME_TYPE_MAP = {
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
}


@dataclass
class ScanResult:
    total_nodes: int = 0
    added: int = 0
    deleted: int = 0


def _classify_file_type(ext: str) -> str:
    ext = ext.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in SUBTITLE_EXTENSIONS:
        return "subtitle"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in ARCHIVE_EXTENSIONS:
        return "archive"
    if ext in SOURCE_EXTENSIONS:
        return "source_code"
    return "other"


def _get_natural_sort_key(name: str):
    """Split name into (text, number) parts for natural sorting."""
    import re
    parts = re.split(r'(\d+)', name)
    result = []
    for part in parts:
        if part.isdigit():
            result.append((0, int(part)))
        else:
            result.append((1, part.lower()))
    return result


@transaction.atomic
def scan_course(course: Course) -> ScanResult:
    """
    Recursively scan a course's root_path and build a CourseNode tree
    preserving the filesystem hierarchy.
    """
    root_path = Path(translate_to_docker_path(course.root_path))
    if not root_path.exists():
        return ScanResult()

    domain_result = scan_directory(str(root_path))

    existing_nodes = {
        n.relative_path: n
        for n in CourseNode.objects.filter(course=course).select_related("media_metadata")
    }
    seen_paths: set[str] = set()
    result = ScanResult()
    media_nodes: list[CourseNode] = []

    for file_info in domain_result.files:
        rel_path = normalize_relative_path(file_info.relative_path)
        ext = Path(file_info.name).suffix
        if ext.lower() not in CONTENT_EXTENSIONS:
            continue

        seen_paths.add(rel_path)

        parts = Path(rel_path).parts
        parent_rel = ""
        sort_order = 0

        for i, part in enumerate(parts[:-1]):
            dir_rel = str(Path(*parts[:i + 1]).as_posix()) if i >= 0 else part
            seen_paths.add(dir_rel)
            if dir_rel not in existing_nodes or existing_nodes[dir_rel].node_type != "directory":
                dir_node, created = CourseNode.objects.update_or_create(
                    course=course,
                    relative_path=dir_rel,
                    defaults={
                        "parent": _find_parent_node(course, dir_rel),
                        "name": part,
                        "node_type": "directory",
                        "sort_order": _natural_sort_value(part),
                    },
                )
                existing_nodes[dir_rel] = dir_node
                if created:
                    result.added += 1
            parent_rel = dir_rel

        file_type = _classify_file_type(ext)
        defaults = {
            "parent": _find_parent_node(course, rel_path),
            "name": file_info.name,
            "node_type": "file",
            "file_type": file_type,
            "file_size": file_info.size,
            "mime_type": MIME_TYPE_MAP.get(ext.lower(), ""),
            "sort_order": _natural_sort_value(file_info.name),
        }

        if rel_path in existing_nodes:
            node = existing_nodes[rel_path]
            changed = (
                node.file_type != file_type
                or (file_info.size is not None and node.file_size != file_info.size)
            )
            if changed:
                for key, val in defaults.items():
                    setattr(node, key, val)
                node.save()
            if file_type in ("video", "audio") and node.media_metadata is None:
                media_nodes.append(node)
        else:
            node = CourseNode.objects.create(course=course, relative_path=rel_path, **defaults)
            existing_nodes[rel_path] = node
            result.added += 1
            if file_type in ("video", "audio"):
                media_nodes.append(node)

        result.total_nodes += 1

    deleted = []
    for rel_path, node in existing_nodes.items():
        if rel_path not in seen_paths:
            deleted.append(node.pk)
            result.deleted += 1
    CourseNode.objects.filter(pk__in=deleted).delete()

    for node in media_nodes:
        try:
            extract_and_save_metadata(node)
        except Exception:
            pass

    return result


def _find_parent_node(course: Course, rel_path: str) -> CourseNode | None:
    """Find the parent directory node for a given relative path."""
    path = Path(rel_path)
    parent_path = path.parent.as_posix()
    if parent_path == ".":
        return None
    try:
        return CourseNode.objects.get(course=course, relative_path=parent_path)
    except CourseNode.DoesNotExist:
        return None


def _natural_sort_value(name: str) -> int:
    """Extract a leading number from a filename for sort_order precedence."""
    import re
    match = re.match(r'(\d+)', name)
    if match:
        return int(match.group(1))
    return 0
