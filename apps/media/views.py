import mimetypes
from pathlib import Path

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404

from apps.courses.models import Course, CourseNode
from domain.skills.storage_mapping import resolve_absolute


def serve_subtitle(request: WSGIRequest, course_pk: int, sub_path: str) -> HttpResponse:
    """Serve a subtitle file for a course, converting SRT to VTT if needed."""
    import re
    course = get_object_or_404(Course, pk=course_pk)

    try:
        absolute_path = resolve_absolute(course.root_path, sub_path)
    except Exception:
        raise Http404("File not found")

    path = Path(absolute_path)

    if not path.exists():
        raise Http404("File not found on disk")

    content_type, _ = mimetypes.guess_type(str(path))
    if content_type is None:
        content_type = "text/plain"

    # Convert SRT to VTT on the fly for browser playback
    if path.suffix.lower() == ".srt":
        content = path.read_text(encoding="utf-8", errors="replace")
        # Add VTT header and convert timestamps
        vtt_content = "WEBVTT\n\n"
        # Replace comma with dot in timestamps: 00:00:01,000 -> 00:00:01.000
        vtt_content += re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", content)
        response = HttpResponse(vtt_content, content_type="text/vtt")
        response["Content-Disposition"] = f'inline; filename="{path.stem}.vtt"'
        return response

    response = FileResponse(open(path, "rb"), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{path.name}"'
    return response


def serve_media(request: WSGIRequest, course_pk: int, node_pk: int) -> HttpResponse:
    """
    Serve a media file for playback.
    """
    node = get_object_or_404(
        CourseNode.objects.select_related("course__workspace"),
        pk=node_pk,
        course_id=course_pk,
    )

    if node.file_type not in ("video", "audio"):
        raise Http404("Not a playable media file")

    try:
        absolute_path = resolve_absolute(node.course.root_path, node.relative_path)
    except Exception:
        raise Http404("File not found - course root may need re-scanning")

    path = Path(absolute_path)

    if not path.exists():
        # Try to find the file by name in the root directory as a fallback
        root_path = Path(node.course.root_path).resolve()
        if root_path.exists():
            for file_path in root_path.rglob(node.name):
                if file_path.is_file():
                    path = file_path
                    break

    if not path.exists():
        raise Http404("File not found on disk - course may need re-scanning")

    content_type, _ = mimetypes.guess_type(str(path))
    if content_type is None:
        content_type = "application/octet-stream"

    response = FileResponse(
        open(path, "rb"),
        content_type=content_type,
    )

    response["Content-Disposition"] = f'inline; filename="{path.name}"'
    response["Accept-Ranges"] = "bytes"

    return response
