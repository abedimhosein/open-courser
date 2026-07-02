from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from apps.courses.models import CourseNode
from apps.progress.services.tracker import (
    record_playback_position,
    mark_completed,
    get_file_progress,
    reset_file_progress,
)


def update_position(request: WSGIRequest, node_pk: int) -> HttpResponse:
    """
    HTMX endpoint - update playback position for a course node.
    """
    node = get_object_or_404(CourseNode, pk=node_pk)

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        position = float(request.POST.get("position", 0))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid position"}, status=400)

    record_playback_position(node, position)

    return JsonResponse({"position": position, "status": "ok"})


def mark_file_completed(request: WSGIRequest, node_pk: int) -> HttpResponse:
    """Mark a course node as completed."""
    node = get_object_or_404(CourseNode, pk=node_pk)

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    mark_completed(node)

    return JsonResponse({"status": "completed"})


def file_progress(request: WSGIRequest, node_pk: int) -> HttpResponse:
    """Get progress for a single file node as JSON."""
    node = get_object_or_404(CourseNode, pk=node_pk)
    progress = get_file_progress(node)
    return JsonResponse(progress)


def reset_progress(request: WSGIRequest, node_pk: int) -> HttpResponse:
    """Reset progress for a course node."""
    node = get_object_or_404(CourseNode, pk=node_pk)

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    reset_file_progress(node)
    return JsonResponse({"status": "reset"})
