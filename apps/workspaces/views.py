from pathlib import Path

from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.forms import ModelForm
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from apps.courses.models import Course
from apps.courses.services.scanner import scan_workspace
from apps.progress.services.tracker import get_course_progress
from apps.workspaces.models import Workspace
from apps.workspaces.services.manager import create_workspace, delete_workspace


class WorkspaceEditForm(ModelForm):
    class Meta:
        model = Workspace
        fields = ["name", "cover_image"]


PAGE_SIZE = 9


def workspace_list(request: WSGIRequest) -> HttpResponse:
    """List all workspaces."""
    workspaces = Paginator(Workspace.objects.all(), PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "workspaces/list.html", {"page_obj": workspaces})


def sort_course_list(courses, sort_by: str) -> list:
    """Build a sorted course_list with progress data."""
    course_list = [
        {"course": c, "progress": get_course_progress(c)}
        for c in courses
    ]
    if sort_by == "progress":
        course_list.sort(
            key=lambda x: (x["progress"] or {}).get("overall_percentage", 0) or 0,
            reverse=True,
        )
    else:
        course_list.sort(key=lambda x: x["course"].name.lower())
    return course_list


def workspace_detail(request: WSGIRequest, pk: int) -> HttpResponse:
    """View a workspace with its courses."""
    workspace = get_object_or_404(Workspace, pk=pk)

    sort_by = request.GET.get("sort", "progress")
    if sort_by not in ("name", "progress"):
        sort_by = "progress"

    courses = Course.objects.filter(workspace=workspace)
    course_list = Paginator(sort_course_list(courses, sort_by), PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "workspaces/detail.html",
        {"workspace": workspace, "course_list": course_list, "current_sort": sort_by},
    )


def workspace_create(request: WSGIRequest) -> HttpResponse:
    """Create a new workspace."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        course_root = request.POST.get("course_root", "").strip()

        if not name or not course_root:
            return render(
                request,
                "workspaces/create.html",
                {"error": "Name and course root are required."},
            )

        try:
            workspace = create_workspace(name, course_root)
            return redirect("workspace_detail", pk=workspace.pk)
        except ValueError as e:
            return render(
                request,
                "workspaces/create.html",
                {"error": str(e)},
            )

    return render(request, "workspaces/create.html")


def workspace_delete(request: WSGIRequest, pk: int) -> HttpResponse:
    """Delete a workspace."""
    workspace = get_object_or_404(Workspace, pk=pk)

    if request.method == "POST":
        delete_workspace(workspace)
        return redirect("workspace_list")

    return render(request, "workspaces/confirm_delete.html", {"workspace": workspace})


def workspace_scan(request: WSGIRequest, pk: int) -> HttpResponse:
    """Trigger a scan of a workspace's course root."""
    workspace = get_object_or_404(Workspace, pk=pk)
    incremental = request.POST.get("mode", "incremental") != "full"
    sort_by = request.GET.get("sort", "name")
    if sort_by not in ("name", "progress"):
        sort_by = "name"

    scan_result = scan_workspace(workspace, incremental=incremental)

    courses = Course.objects.filter(workspace=workspace)
    course_list = Paginator(sort_course_list(courses, sort_by), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "workspaces/detail.html",
        {
            "workspace": workspace,
            "course_list": course_list,
            "current_sort": sort_by,
            "scan_summary": {
                "added": len(scan_result.change_set.added) if scan_result.change_set else 0,
                "modified": len(scan_result.change_set.modified) if scan_result.change_set else 0,
                "deleted": len(scan_result.change_set.deleted) if scan_result.change_set else 0,
                "total_files": len(scan_result.files),
            },
        },
    )


def workspace_edit(request: WSGIRequest, pk: int) -> HttpResponse:
    """Edit workspace name and cover image."""
    workspace = get_object_or_404(Workspace, pk=pk)

    if request.method == "POST":
        form = WorkspaceEditForm(request.POST, request.FILES, instance=workspace)
        if form.is_valid():
            form.save()
            return redirect("workspace_detail", pk=workspace.pk)
    else:
        form = WorkspaceEditForm(instance=workspace)

    return render(request, "workspaces/edit.html", {"form": form, "workspace": workspace})


def browse_directories(request: WSGIRequest) -> HttpResponse:
    """
    HTMX partial - browse subdirectories of a given path.

    Accepts a 'path' query parameter. Returns a list of subdirectories
    as clickable items for navigation.
    """
    current_path_str = request.GET.get("path", "").strip()

    if not current_path_str:
        if Path("/").exists():
            candidates = [Path(d) for d in ("/", str(Path.home())) if Path(d).exists()]
            current_path = candidates[0] if candidates else Path.home()
        else:
            current_path = Path.home()
    else:
        current_path = Path(current_path_str).resolve()

    if not current_path.exists() or not current_path.is_dir():
        current_path = Path.home()

    parent_path = str(current_path.parent) if current_path.parent != current_path else ""

    try:
        entries = sorted(
            [e for e in current_path.iterdir() if e.is_dir() and not e.name.startswith((".", "_"))],
            key=lambda e: e.name.lower(),
        )
    except PermissionError:
        entries = []

    directories = []
    for entry in entries:
        try:
            rel_path = str(entry.resolve())
            directories.append({"name": entry.name, "path": rel_path})
        except (OSError, PermissionError):
            continue

    return render(
        request,
        "workspaces/_directory_browser.html",
        {
            "current_path": str(current_path),
            "parent_path": parent_path,
            "directories": directories,
        },
    )
