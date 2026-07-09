from django.core.handlers.wsgi import WSGIRequest
from django import forms
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseNotAllowed
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from apps.courses.models import Course, CourseNode, Tag
from apps.courses.services.scanner import scan_course
from apps.media.services.extractor import extract_and_save_metadata
from apps.progress.models import WatchHistory
from apps.progress.services.tracker import (
    get_course_progress,
    get_file_progress,
    mark_completed,
    reset_file_progress,
)
from apps.workspaces.views import sort_course_list, PAGE_SIZE
from domain.skills.storage_mapping import resolve_absolute, MissingRootError
from domain.skills.media_understanding import discover_subtitles, SubtitleInfo


class CourseEditForm(ModelForm):
    class Meta:
        model = Course
        fields = ["workspace", "title", "cover_image", "description", "locked", "tags"]
        widgets = {
            "tags": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
        }


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


def course_search(request: WSGIRequest) -> HttpResponse:
    """Search courses by title across all workspaces."""
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        courses = Course.objects.filter(title__icontains=query).select_related("workspace")
        results = [
            {"course": c, "progress": get_course_progress(c)}
            for c in courses
        ]
    return render(request, "courses/search.html", {"query": query, "results": results})


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
    if course.locked:
        response = HttpResponse()
        response["HX-Refresh"] = "true"
        return response
    scan_course(course)
    response = HttpResponse()
    response["HX-Refresh"] = "true"
    return response


def course_toggle_lock(request: WSGIRequest, pk: int) -> HttpResponse:
    """Toggle the lock state of a course."""
    course = get_object_or_404(Course, pk=pk)
    course.locked = not course.locked
    course.save(update_fields=["locked"])
    response = HttpResponse()
    response["HX-Refresh"] = "true"
    return response


def course_complete_all(request: WSGIRequest, pk: int) -> HttpResponse:
    """Mark all file nodes in a course as completed."""
    from apps.courses.services.scanner import _update_course_durations
    course = get_object_or_404(Course, pk=pk)
    for node in CourseNode.objects.filter(course=course, node_type="file"):
        mark_completed(node)
    _update_course_durations(course)

    nodes = CourseNode.objects.filter(course=course).order_by("sort_order", "name")
    tree = _build_node_tree(list(nodes))
    file_nodes = [n for n in nodes if n.node_type == "file"]
    file_progresses = [get_file_progress(n) for n in file_nodes]
    progress = get_course_progress(course)

    return render(
        request,
        "courses/_course_content.html",
        {
            "course": course,
            "tree": tree,
            "file_nodes": file_nodes,
            "file_progresses": file_progresses,
            "progress": progress,
        },
    )


def course_reset_all(request: WSGIRequest, pk: int) -> HttpResponse:
    """Reset progress for all file nodes in a course."""
    from apps.courses.services.scanner import _update_course_durations
    course = get_object_or_404(Course, pk=pk)
    WatchHistory.objects.filter(course_node__course=course, course_node__node_type="file").delete()
    _update_course_durations(course)

    nodes = CourseNode.objects.filter(course=course).order_by("sort_order", "name")
    tree = _build_node_tree(list(nodes))
    file_nodes = [n for n in nodes if n.node_type == "file"]
    file_progresses = [get_file_progress(n) for n in file_nodes]
    progress = get_course_progress(course)

    return render(
        request,
        "courses/_course_content.html",
        {
            "course": course,
            "tree": tree,
            "file_nodes": file_nodes,
            "file_progresses": file_progresses,
            "progress": progress,
        },
    )


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
    """Toggle completion status for a course node and update the file list."""
    course = get_object_or_404(Course, pk=course_pk)
    node = get_object_or_404(CourseNode, pk=node_pk, course=course)
    _toggle_node_completion(node)

    nodes = CourseNode.objects.filter(course=course).order_by("sort_order", "name")
    tree = _build_node_tree(list(nodes))
    file_nodes = [n for n in nodes if n.node_type == "file"]
    file_progresses = [get_file_progress(n) for n in file_nodes]

    progress = get_course_progress(course)

    response = render(
        request,
        "courses/_course_content.html",
        {
            "course": course,
            "tree": tree,
            "file_nodes": file_nodes,
            "file_progresses": file_progresses,
            "progress": progress,
        },
    )
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

    from django.utils import timezone
    from apps.courses.services.scanner import _update_course_durations
    Course.objects.filter(pk=node.course_id).update(updated_at=timezone.now())
    _update_course_durations(node.course)


def file_detail(request: WSGIRequest, course_pk: int, node_pk: int) -> HttpResponse:
    """View a single course file node."""
    from pathlib import Path as FilePath

    course = get_object_or_404(Course, pk=course_pk)
    node = get_object_or_404(CourseNode, pk=node_pk, course=course)

    # Prev / next navigation (file nodes only, ordered)
    file_nodes = list(
        CourseNode.objects.filter(course=course, node_type="file")
        .order_by("sort_order", "name")
        .values_list("pk", flat=True)
    )
    current_idx = file_nodes.index(node_pk) if node_pk in file_nodes else -1
    prev_node = None
    next_node = None
    if current_idx > 0:
        prev_node = file_nodes[current_idx - 1]
    if current_idx < len(file_nodes) - 1:
        next_node = file_nodes[current_idx + 1]

    error = None
    absolute_path = None

    try:
        absolute_path = resolve_absolute(course.root_path, node.relative_path)
        if not FilePath(absolute_path).exists():
            # Fallback: search for file by name in root directory
            root_path = FilePath(course.root_path).resolve()
            if root_path.exists():
                for file_path in root_path.rglob(node.name):
                    if file_path.is_file():
                        absolute_path = file_path
                        break
            if not FilePath(absolute_path).exists():
                error = "File not found on disk. The course may need to be re-scanned."
    except MissingRootError:
        error = "Course root directory not found. The course may need to be re-scanned."

    metadata_model = None
    subtitles = []
    if absolute_path and FilePath(absolute_path).exists() and node.file_type in ("video", "audio"):
        metadata_model = extract_and_save_metadata(node)
        subtitles = discover_subtitles(absolute_path, course.root_path)

        # Fallback: use stored subtitle paths if runtime discovery found nothing
        if not subtitles and metadata_model and metadata_model.subtitle_paths:
            for sub_rel in metadata_model.subtitle_paths:
                sub_file = FilePath(course.root_path) / sub_rel
                if sub_file.exists():
                    fmt = sub_file.suffix.lstrip(".")
                    subtitles.append(SubtitleInfo(
                        relative_path=sub_rel,
                        language=None,
                        format=fmt,
                    ))

    progress = get_file_progress(node)

    return render(
        request,
        "courses/file_detail.html",
        {
            "course": course,
            "file": node,
            "file_path": str(absolute_path) if absolute_path and FilePath(absolute_path).exists() else None,
            "metadata": metadata_model,
            "subtitles": subtitles,
            "progress": progress,
            "error": error,
            "prev_node": prev_node,
            "next_node": next_node,
        },
    )


def tag_list(request: WSGIRequest) -> HttpResponse:
    """List all tags with course counts."""
    from django.db.models import Count
    tags = Tag.objects.annotate(course_count=Count("courses")).order_by("name")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        color = request.POST.get("color", "#6c757d").strip()
        if name:
            Tag.objects.get_or_create(
                name__iexact=name,
                defaults={"name": name, "slug": name.lower().replace(" ", "-"), "color": color},
            )
        return redirect("tag_list")

    return render(request, "courses/tag_list.html", {"tags": tags})


def tag_edit(request: WSGIRequest, pk: int) -> HttpResponse:
    """Edit a tag's name and color."""
    tag = get_object_or_404(Tag, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        color = request.POST.get("color", "#6c757d").strip()
        if name:
            tag.name = name
            tag.slug = name.lower().replace(" ", "-")
            tag.color = color
            tag.save()
        return redirect("tag_list")

    return render(request, "courses/tag_edit.html", {"tag": tag})


def tag_delete(request: WSGIRequest, pk: int) -> HttpResponse:
    """Delete a tag."""
    tag = get_object_or_404(Tag, pk=pk)
    if request.method == "POST":
        tag.delete()
        return redirect("tag_list")
    return render(request, "courses/tag_confirm_delete.html", {"tag": tag})


def tag_courses(request: WSGIRequest, pk: int) -> HttpResponse:
    """List all courses with a specific tag."""
    tag = get_object_or_404(Tag, pk=pk)
    sort_by = request.GET.get("sort", "name")
    if sort_by not in ("name", "progress", "duration"):
        sort_by = "name"
    courses = Course.objects.filter(tags=tag)
    course_list = Paginator(sort_course_list(courses, sort_by), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "courses/tag_courses.html",
        {
            "tag": tag,
            "course_list": course_list,
            "current_sort": sort_by,
        },
    )
