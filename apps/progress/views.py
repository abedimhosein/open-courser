from datetime import timedelta

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.courses.models import CourseNode
from apps.progress.models import WatchHistory
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


def activity(request: WSGIRequest) -> HttpResponse:
    """Show daily watch activity chart."""
    days = int(request.GET.get("days", 30))
    now = timezone.now()
    start = now - timedelta(days=days)

    watch_qs = (
        WatchHistory.objects.filter(last_watched_at__gte=start)
        .select_related("course_node__media_metadata")
    )

    daily = {}
    for watch in watch_qs:
        day_str = str(watch.last_watched_at.date())
        hours = watch.duration_watched
        if hours == 0 and watch.completed:
            meta = getattr(watch.course_node, "media_metadata", None)
            if meta and meta.duration:
                hours = meta.duration
        daily[day_str] = daily.get(day_str, 0) + hours

    if days <= 30:
        labels = []
        values = []
        for i in range(days):
            day = (now - timedelta(days=days - 1 - i)).date()
            labels.append(day.strftime("%b %d"))
            values.append(round(daily.get(day.isoformat(), 0) / 3600, 2))
        chart_type = "bar"
    else:
        start_date = (now - timedelta(days=days)).date()
        end_date = now.date()
        current = start_date
        labels = []
        values = []
        while current <= end_date:
            week_end = min(current + timedelta(days=6), end_date)
            week_hours = 0.0
            d = current
            while d <= week_end:
                week_hours += daily.get(d.isoformat(), 0) / 3600
                d += timedelta(days=1)
            labels.append(current.strftime("%b %d"))
            values.append(round(week_hours, 2))
            current += timedelta(days=7)
        chart_type = "line"

    total_hours = round(sum(values), 1)
    active_days = sum(1 for v in values if v > 0)

    return render(
        request,
        "progress/activity.html",
        {
            "labels": labels,
            "values": values,
            "days": days,
            "total_hours": total_hours,
            "active_days": active_days,
            "chart_type": chart_type,
        },
    )
