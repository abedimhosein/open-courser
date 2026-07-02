from django.core.handlers.wsgi import WSGIRequest
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from apps.courses.models import Course, CourseNode
from apps.courses.services.scanner import scan_course
from apps.media.services.extractor import extract_and_save_metadata
from apps.progress.models import WatchHistory
from apps.progress.services.tracker import (
    get_course_progress,
    get_file_progress,
    mark_completed,
    reset_file_progress,
)
from domain.skills.storage_mapping import resolve_absolute
from domain.skills.media_understanding import discover_subtitles


class CourseEditForm(ModelForm):
    class Meta:
        model = Course
        fields = ["title", "cover_image", "description"]


def _build_node_tree(nodes):
    """Build a nested tree from a flat list of CourseNodes."""
    node_map = {}
    roots = []
    for node in nodes:
        node.children_list = []
        node_map[node.pk] = node
    for node in nodes:
        if node.parent_id and node.parent_id in node_map:
            node_map[node.parent_id].children_list.append(node)
        else:
            roots.append(node)
    return roots


def course_detail(request: WSGIRequest, pk: int) -> HttpResponse:
    """View a course with its file tree and progress."""
    course = get_object_or_404(Course.objects.select_related("workspace"), pk=pk)
    nodes = CourseNode.objects.filter(course=course).order_by("sort_order", "name")
    tree = _build_node_tree(list(nodes))
    progress = get_course_progress(course)
    file_nodes = [n for n in nodes if n.node_type == "file"]
    file_progresses = [get_file_progress(n) for n in file_nodes]

    return render(
        request,
        "courses/detail.html",
        {
            "course": course,
            "tree": tree,
            "file_nodes": file_nodes,
            "progress": progress,
            "file_progresses": file_progresses,
        },
    )


def course_create(request: WSGIRequest, workspace_pk: int) -> HttpResponse:
    """Create a new course manually."""
    from apps.workspaces.models import Workspace
    workspace = get_object_or_404(Workspace, pk=workspace_pk)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        root_path = request.POST.get("root_path", "").strip()
        description = request.POST.get("description", "").strip()

        if not title or not root_path:
            return render(
                request,
                "courses/create.html",
                {"workspace": workspace, "error": "Title and root path are required."},
            )

        course = Course.objects.create(
            workspace=workspace,
            title=title,
            root_path=root_path,
            description=description,
            cover_image=request.FILES.get("cover_image"),
        )
        return redirect("course_detail", pk=course.pk)

    return render(request, "courses/create.html", {"workspace": workspace})


def course_edit(request: WSGIRequest, pk: int) -> HttpResponse:
    """Edit course title, description, and cover image."""
    course = get_object_or_404(Course, pk=pk)

    if request.method == "POST":
        form = CourseEditForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            if request.POST.get("remove_cover_image"):
                if course.cover_image:
                    course.cover_image.delete(save=False)
                course.cover_image = None
                course.save(update_fields=["cover_image"])
                return redirect("course_detail", pk=course.pk)
            form.save()
            return redirect("course_detail", pk=course.pk)
    else:
        form = CourseEditForm(instance=course)

    return render(request, "courses/edit.html", {"form": form, "course": course})


def course_delete(request: WSGIRequest, pk: int) -> HttpResponse:
    """Delete a course."""
    course = get_object_or_404(Course, pk=pk)
    workspace_pk = course.workspace.pk

    if request.method == "POST":
        course.delete()
        return redirect("workspace_detail", pk=workspace_pk)

    return render(request, "courses/confirm_delete.html", {"course": course})


def course_scan(request: WSGIRequest, pk: int) -> HttpResponse:
    """Scan a single course and reload the page."""
    course = get_object_or_404(Course.objects.select_related("workspace"), pk=pk)
    scan_course(course)
    response = HttpResponse()
    response["HX-Refresh"] = "true"
    return response


def course_complete_all(request: WSGIRequest, pk: int) -> HttpResponse:
    """Mark all file nodes in a course as completed."""
    course = get_object_or_404(Course, pk=pk)
    for node in CourseNode.objects.filter(course=course, node_type="file"):
        mark_completed(node)
    response = HttpResponse()
    response["HX-Redirect"] = reverse("course_detail", kwargs={"pk": course.pk})
    return response


def course_reset_all(request: WSGIRequest, pk: int) -> HttpResponse:
    """Reset progress for all file nodes in a course."""
    course = get_object_or_404(Course, pk=pk)
    WatchHistory.objects.filter(course_node__course=course, course_node__node_type="file").delete()
    response = HttpResponse()
    response["HX-Redirect"] = reverse("course_detail", kwargs={"pk": course.pk})
    return response


def course_progress_partial(request: WSGIRequest, pk: int) -> HttpResponse:
    """HTMX partial - returns just the course progress card."""
    course = get_object_or_404(Course, pk=pk)
    progress = get_course_progress(course)

    return render(
        request,
        "courses/_progress.html",
        {"course": course, "progress": progress},
    )


def course_files_partial(request: WSGIRequest, pk: int) -> HttpResponse:
    """HTMX partial - returns just the file tree for a course."""
    course = get_object_or_404(Course, pk=pk)
    nodes = CourseNode.objects.filter(course=course).order_by("sort_order", "name")
    tree = _build_node_tree(list(nodes))
    file_nodes = [n for n in nodes if n.node_type == "file"]
    file_progresses = [get_file_progress(n) for n in file_nodes]

    return render(
        request,
        "courses/_file_list.html",
        {
            "course": course,
            "tree": tree,
            "file_nodes": file_nodes,
            "file_progresses": file_progresses,
        },
    )


def toggle_complete(request: WSGIRequest, course_pk: int, node_pk: int) -> HttpResponse:
    """Toggle completion status for a course node and reload the page."""
    course = get_object_or_404(Course, pk=course_pk)
    node = get_object_or_404(CourseNode, pk=node_pk, course=course)
    _toggle_node_completion(node)
    response = HttpResponse()
    response["HX-Redirect"] = reverse("course_detail", kwargs={"pk": course.pk})
    return response


def toggle_file_complete(request: WSGIRequest, course_pk: int, node_pk: int) -> HttpResponse:
    """Toggle completion status and return updated progress panel."""
    course = get_object_or_404(Course, pk=course_pk)
    node = get_object_or_404(CourseNode, pk=node_pk, course=course)

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    _toggle_node_completion(node)

    progress = get_file_progress(node)

    return render(
        request,
        "courses/_file_progress_panel.html",
        {
            "course": course,
            "file": node,
            "progress": progress,
        },
    )


def _toggle_node_completion(node: CourseNode) -> None:
    """Internal helper to toggle a node's completion status."""
    if node.node_type != "file":
        return
    try:
        watch = WatchHistory.objects.get(course_node=node)
        if watch.completed:
            reset_file_progress(node)
        else:
            mark_completed(node)
    except WatchHistory.DoesNotExist:
        mark_completed(node)


def file_detail(request: WSGIRequest, course_pk: int, node_pk: int) -> HttpResponse:
    """View a single course file node."""
    course = get_object_or_404(Course, pk=course_pk)
    node = get_object_or_404(CourseNode, pk=node_pk, course=course)

    absolute_path = resolve_absolute(course.root_path, node.relative_path)

    metadata_model = None
    subtitles = []
    if node.file_type in ("video", "audio"):
        metadata_model = extract_and_save_metadata(node)
        subtitles = discover_subtitles(absolute_path, course.root_path)

    progress = get_file_progress(node)

    return render(
        request,
        "courses/file_detail.html",
        {
            "course": course,
            "file": node,
            "file_path": str(absolute_path),
            "metadata": metadata_model,
            "subtitles": subtitles,
            "progress": progress,
        },
    )
