from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from apps.courses.models import CourseFile
from apps.progress.services.tracker import (
    record_playback_position,
    mark_completed,
    get_file_progress,
    reset_file_progress,
)


def update_position(request: HttpRequest, file_pk: int) -> HttpResponse:
    """
    HTMX endpoint - update playback position for a course file.
    """
    course_file = get_object_or_404(CourseFile, pk=file_pk)

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        position = float(request.POST.get("position", 0))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid position"}, status=400)

    record_playback_position(course_file, position)

    return JsonResponse({"position": position, "status": "ok"})


def mark_file_completed(request: HttpRequest, file_pk: int) -> HttpResponse:
    """Mark a course file as completed."""
    course_file = get_object_or_404(CourseFile, pk=file_pk)

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    mark_completed(course_file)

    return JsonResponse({"status": "completed"})


def file_progress(request: HttpRequest, file_pk: int) -> HttpResponse:
    """Get progress for a single file as JSON."""
    course_file = get_object_or_404(CourseFile, pk=file_pk)
    progress = get_file_progress(course_file)
    return JsonResponse(progress)


def reset_progress(request: HttpRequest, file_pk: int) -> HttpResponse:
    """Reset progress for a course file."""
    course_file = get_object_or_404(CourseFile, pk=file_pk)

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    reset_file_progress(course_file)
    return JsonResponse({"status": "reset"})
