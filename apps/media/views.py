import mimetypes
from pathlib import Path

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404

from apps.courses.models import CourseFile
from domain.skills.storage_mapping import resolve_absolute


def serve_media(request: WSGIRequest, course_pk: int, file_pk: int) -> HttpResponse:
    """
    Serve a media file for playback.

    Uses FileResponse to stream the file efficiently without loading
    it entirely into memory.
    """
    course_file = get_object_or_404(
        CourseFile.objects.select_related("course__workspace"),
        pk=file_pk,
        course_id=course_pk,
    )

    if course_file.file_type not in ("video", "audio"):
        raise Http404("Not a playable media file")

    try:
        absolute_path = resolve_absolute(
            course_file.course.workspace.course_root,
            course_file.relative_path,
        )
    except Exception:
        raise Http404("File not found")

    path = Path(absolute_path)

    if not path.exists():
        raise Http404("File not found on disk")

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
