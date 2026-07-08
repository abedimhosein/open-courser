from pathlib import Path

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.core.paginator import Paginator
from django.forms import ModelForm

from apps.courses.services.scanner import scan_course
from apps.courses.models import Course
from apps.progress.services.tracker import get_course_progress, get_workspace_progress
from apps.workspaces.models import Workspace
from apps.workspaces.services.manager import create_workspace, delete_workspace
from domain.skills.drive_discovery import get_available_drives

PAGE_SIZE = 15


class WorkspaceEditForm(ModelForm):
    class Meta:
        model = Workspace
        fields = ["name", "description", "cover_image"]


def workspace_list(request: HttpRequest) -> HttpResponse:
    """List all workspaces."""
    from django.db.models import Count, Sum, Q, Subquery, OuterRef, IntegerField
    from apps.courses.models import Course

    sort_by = request.GET.get("sort", "name")
    if sort_by not in ("name", "courses", "duration"):
        sort_by = "name"

    # Subquery for course count to avoid cross-join multiplication
    course_count_subq = Course.objects.filter(
        workspace=OuterRef("pk")
    ).order_by().values("workspace").annotate(
        c=Count("id")
    ).values("c")

    workspaces = Workspace.objects.annotate(
        course_count=Subquery(course_count_subq, output_field=IntegerField()),
        total_dur=Sum("courses__total_duration"),
    )

    if sort_by == "duration":
        workspaces = workspaces.order_by("-total_dur")
    elif sort_by == "courses":
        workspaces = workspaces.order_by("-course_count")
    else:
        workspaces = workspaces.order_by("name")

    workspaces = Paginator(workspaces, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "workspaces/list.html", {"page_obj": workspaces, "current_sort": sort_by})


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
    elif sort_by == "duration":
        course_list.sort(
            key=lambda x: x["course"].total_duration,
            reverse=True,
        )
    else:
        course_list.sort(key=lambda x: x["course"].title.lower())
    return course_list


def workspace_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """View a workspace with its courses."""
    workspace = get_object_or_404(Workspace, pk=pk)
    sort_by = request.GET.get("sort", "progress")
    if sort_by not in ("name", "progress", "duration"):
        sort_by = "progress"
    courses = Course.objects.filter(workspace=workspace)
    course_list = Paginator(sort_course_list(courses, sort_by), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    workspace_progress = get_workspace_progress(workspace)
    return render(
        request,
        "workspaces/detail.html",
        {
            "workspace": workspace,
            "course_list": course_list,
            "current_sort": sort_by,
            "workspace_progress": workspace_progress,
        },
    )


def workspace_create(request: HttpRequest) -> HttpResponse:
    """Create a new workspace."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        root_path = request.POST.get("root_path", "").strip()
        auto_import = request.POST.get("auto_import") == "1"

        if not name:
            return render(
                request,
                "workspaces/create.html",
                {"error": "Workspace name is required."},
            )

        if auto_import and not root_path:
            return render(
                request,
                "workspaces/create.html",
                {"error": "Root directory is required when auto-import is enabled."},
            )

        try:
            workspace = create_workspace(name, description)
        except ValueError as e:
            return render(
                request,
                "workspaces/create.html",
                {"error": str(e)},
            )

        if auto_import and root_path:
            _import_courses_from_root(workspace, root_path)

        return redirect("workspace_detail", pk=workspace.pk)

    return render(request, "workspaces/create.html")


def _import_courses_from_root(workspace: Workspace, root_path: str) -> None:
    """Scan root_path and create a course for each immediate subdirectory."""
    root = Path(root_path)
    if not root.exists() or not root.is_dir():
        return

    for entry in sorted(root.iterdir(), key=lambda e: e.name.lower()):
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue

        course = Course.objects.create(
            workspace=workspace,
            title=entry.name,
            root_path=str(entry.resolve()),
        )
        try:
            scan_course(course)
        except Exception:
            pass


def workspace_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete a workspace."""
    workspace = get_object_or_404(Workspace, pk=pk)

    if request.method == "POST":
        delete_workspace(workspace)
        return redirect("workspace_list")

    return render(request, "workspaces/confirm_delete.html", {"workspace": workspace})


def workspace_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit workspace name, description, and cover image."""
    workspace = get_object_or_404(Workspace, pk=pk)

    if request.method == "POST":
        form = WorkspaceEditForm(request.POST, request.FILES, instance=workspace)
        if form.is_valid():
            if request.POST.get("remove_cover_image"):
                if workspace.cover_image:
                    workspace.cover_image.delete(save=False)
                workspace.cover_image = None
                workspace.save(update_fields=["cover_image"])
                return redirect("workspace_detail", pk=workspace.pk)
            form.save()
            return redirect("workspace_detail", pk=workspace.pk)
    else:
        form = WorkspaceEditForm(instance=workspace)

    return render(request, "workspaces/edit.html", {"form": form, "workspace": workspace})


def workspace_scan_all(request: HttpRequest, pk: int) -> HttpResponse:
    """Scan all courses in a workspace."""
    workspace = get_object_or_404(Workspace, pk=pk)
    courses = Course.objects.filter(workspace=workspace)
    total_files = 0
    for course in courses:
        result = scan_course(course)
        total_files += result.total_nodes

    sort_by = request.GET.get("sort", "progress")
    if sort_by not in ("name", "progress", "duration"):
        sort_by = "progress"
    course_list = Paginator(sort_course_list(courses, sort_by), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    workspace_progress = get_workspace_progress(workspace)
    return render(
        request,
        "workspaces/detail.html",
        {
            "workspace": workspace,
            "course_list": course_list,
            "current_sort": sort_by,
            "workspace_progress": workspace_progress,
            "scan_summary": {
                "total_files": total_files,
            },
        },
    )


def browse_directories(request: HttpRequest) -> HttpResponse:
    """
    HTMX partial - browse subdirectories of a given path.
    Used for the course root directory picker.
    """
    current_path_str = request.GET.get("path", "").strip()
    filter_query = request.GET.get("q", "").strip().lower()
    drives = get_available_drives()

    if not current_path_str:
        configured = getattr(settings, "COURSE_ROOTS", [])
        if configured:
            directories = []
            for root in configured:
                container_path = root["container_path"]
                host_name = Path(root["host_path"]).name or root["host_path"]
                directories.append({"name": host_name, "path": container_path})
            if filter_query:
                directories = [d for d in directories if filter_query in d["name"].lower()]
            return render(
                request,
                "workspaces/_directory_browser.html",
                {
                    "current_path": "Course Roots",
                    "parent_path": "",
                    "directories": directories,
                    "filter_query": filter_query,
                    "drives": drives,
                },
            )
        # Show drives by default when no path is given
        return render(
            request,
            "workspaces/_directory_browser.html",
            {
                "current_path": "",
                "parent_path": "",
                "directories": [],
                "filter_query": filter_query,
                "drives": drives,
                "show_drives_only": True,
            },
        )

    current_path = Path(current_path_str).resolve()

    if not current_path.exists() or not current_path.is_dir():
        current_path = Path.home()

    # Always set parent_path for navigation (empty string = show drives list)
    parent_path = ""
    if current_path.parent != current_path:
        parent_path = str(current_path.parent)

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

    if filter_query:
        directories = [d for d in directories if filter_query in d["name"].lower()]

    # Determine current drive letter for highlighting
    current_drive = ""
    if current_path.drive:
        current_drive = f"{current_path.drive}\\"

    return render(
        request,
        "workspaces/_directory_browser.html",
        {
            "current_path": str(current_path),
            "parent_path": parent_path,
            "directories": directories,
            "filter_query": filter_query,
            "drives": drives,
            "current_drive": current_drive,
        },
    )
