"""
Course Scanner Service

Owned by: Backend Django Agent (orchestration)
Delegates to: File System Agent (Content Discovery)

Purpose: Orchestrate filesystem scanning and persist results
as Course and CourseFile records.
"""
from __future__ import annotations

import mimetypes

from django.db import transaction

from apps.courses.models import Course, CourseFile
from apps.workspaces.models import Workspace
from domain.skills.content_discovery import (
    FileInfo,
    ScanResult,
    scan_directory,
    scan_incremental,
)


@transaction.atomic
def scan_workspace(workspace: Workspace, incremental: bool = True) -> ScanResult:
    """
    Scan a workspace's course root and sync database records.

    Returns the ScanResult with change information.
    """
    if incremental:
        previous_files = CourseFile.objects.filter(course__workspace=workspace)
        snapshot: dict[str, tuple[int | None, float | None]] = {}
        for cf in previous_files.select_related("course"):
            snapshot[cf.relative_path] = (cf.file_size, None)

        scan_result = scan_incremental(workspace.course_root, snapshot)
    else:
        scan_result = scan_directory(workspace.course_root)

    # Determine courses from the top-level directories
    top_level_dirs = _get_top_level_directories(scan_result)

    # Sync courses
    existing_courses = {
        c.relative_path: c for c in Course.objects.filter(workspace=workspace)
    }

    for dir_rel_path in top_level_dirs:
        dir_name = dir_rel_path.rstrip("/").split("/")[-1] or dir_rel_path
        if dir_rel_path in existing_courses:
            course = existing_courses[dir_rel_path]
        else:
            course = Course.objects.create(
                workspace=workspace,
                name=dir_name,
                relative_path=dir_rel_path,
            )

    # Remove courses that no longer exist on filesystem
    current_dir_set = set(top_level_dirs)
    for rel_path, course in existing_courses.items():
        if rel_path not in current_dir_set:
            course.delete()

    # Sync files
    _sync_course_files(workspace, scan_result)

    return scan_result


def _get_top_level_directories(scan_result: ScanResult) -> list[str]:
    """
    Extract top-level directories from scan result.

    A top-level directory is one directly under the root (no '/' in relative path).
    """
    top_level = set()
    for d in scan_result.directories:
        parts = d.split("/")
        if len(parts) == 1:
            top_level.add(d)

    for f in scan_result.files:
        parts = f.relative_path.split("/")
        if len(parts) > 1:
            top_level.add(parts[0])

    return sorted(top_level)


def _sync_course_files(workspace: Workspace, scan_result: ScanResult) -> None:
    """
    Synchronize CourseFile records with the scan result.
    """
    courses_by_path = {
        c.relative_path: c
        for c in Course.objects.filter(workspace=workspace).select_related("workspace")
    }

    existing_files: dict[tuple[int, str], CourseFile] = {}
    for cf in CourseFile.objects.filter(course__workspace=workspace).select_related("course"):
        existing_files[(cf.course_id, cf.relative_path)] = cf

    seen_keys: set[tuple[int, str]] = set()

    for file_info in scan_result.files:
        course_path = file_info.relative_path.split("/")[0]
        course = courses_by_path.get(course_path)
        if course is None:
            continue

        file_type = _classify_file_type(file_info)
        key = (course.id, file_info.relative_path)
        seen_keys.add(key)

        if key in existing_files:
            cf = existing_files[key]
            changed = False
            if cf.file_size != file_info.size:
                cf.file_size = file_info.size
                changed = True
            if cf.file_type != file_type:
                cf.file_type = file_type
                changed = True
            if changed:
                cf.save(update_fields=["file_size", "file_type", "updated_at"])
        else:
            mime_type, _ = mimetypes.guess_type(file_info.name)
            CourseFile.objects.create(
                course=course,
                name=file_info.name,
                relative_path=file_info.relative_path,
                file_type=file_type,
                file_size=file_info.size,
                mime_type=mime_type or "",
            )

    for key, cf in existing_files.items():
        if key not in seen_keys:
            cf.delete()


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass"}
DOCUMENT_EXTENSIONS = {".pdf", ".epub", ".doc", ".docx", ".txt", ".md"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"}
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".html", ".css", ".scss", ".java",
    ".cpp", ".c", ".h", ".rs", ".go", ".rb", ".php",
}


def _classify_file_type(file_info: FileInfo) -> str:
    """Classify a file into a type category based on extension."""
    ext = file_info.extension
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
