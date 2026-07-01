from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404, redirect
from django.forms import ModelForm

from apps.courses.models import Course, CourseFile
from apps.media.services.extractor import extract_and_save_metadata
from apps.progress.models import WatchHistory
from apps.progress.services.tracker import (
    get_course_progress,
    get_file_progress,
    mark_completed,
    reset_file_progress,
)


class CourseEditForm(ModelForm):
    class Meta:
        model = Course
        fields = ["name", "cover_image"]


def course_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """View a course with its file tree and progress."""
    course = get_object_or_404(Course.objects.select_related("workspace"), pk=pk)
    files = CourseFile.objects.filter(course=course).order_by("relative_path")
    progress = get_course_progress(course)

    file_progresses = [get_file_progress(cf) for cf in files]

    return render(
        request,
        "courses/detail.html",
        {
            "course": course,
            "files": files,
            "progress": progress,
            "file_progresses": file_progresses,
        },
    )


def course_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit course name and cover image."""
    course = get_object_or_404(Course, pk=pk)

    if request.method == "POST":
        form = CourseEditForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            return redirect("course_detail", pk=course.pk)
    else:
        form = CourseEditForm(instance=course)

    return render(request, "courses/edit.html", {"form": form, "course": course})


def course_progress_partial(request: HttpRequest, pk: int) -> HttpResponse:
    """HTMX partial - returns just the course progress card."""
    course = get_object_or_404(Course, pk=pk)
    progress = get_course_progress(course)

    return render(
        request,
        "courses/_progress.html",
        {"course": course, "progress": progress},
    )


def course_files_partial(request: HttpRequest, pk: int) -> HttpResponse:
    """HTMX partial - returns just the file list for a course."""
    course = get_object_or_404(Course, pk=pk)
    files = CourseFile.objects.filter(course=course).order_by("relative_path")
    file_progresses = [get_file_progress(cf) for cf in files]

    return render(
        request,
        "courses/_file_list.html",
        {
            "course": course,
            "files": files,
            "file_progresses": file_progresses,
        },
    )


def toggle_complete(request: HttpRequest, course_pk: int, file_pk: int) -> HttpResponse:
    """Toggle completion status for a course file and return updated file list."""
    course = get_object_or_404(Course, pk=course_pk)
    course_file = get_object_or_404(CourseFile, pk=file_pk, course=course)

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    _toggle_file_completion(course_file)

    files = CourseFile.objects.filter(course=course).order_by("relative_path")
    file_progresses = [get_file_progress(cf) for cf in files]

    response = render(
        request,
        "courses/_file_list.html",
        {
            "course": course,
            "files": files,
            "file_progresses": file_progresses,
        },
    )
    response["HX-Trigger"] = "refresh-course-progress"
    return response


def toggle_file_complete(request: HttpRequest, course_pk: int, file_pk: int) -> HttpResponse:
    """Toggle completion status and return updated progress panel."""
    course = get_object_or_404(Course, pk=course_pk)
    course_file = get_object_or_404(CourseFile, pk=file_pk, course=course)

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    _toggle_file_completion(course_file)

    progress = get_file_progress(course_file)

    return render(
        request,
        "courses/_file_progress_panel.html",
        {
            "course": course,
            "file": course_file,
            "progress": progress,
        },
    )


def _toggle_file_completion(course_file: CourseFile) -> None:
    """Internal helper to toggle a file's completion status."""
    try:
        watch = WatchHistory.objects.get(course_file=course_file)
        if watch.completed:
            reset_file_progress(course_file)
        else:
            mark_completed(course_file)
    except WatchHistory.DoesNotExist:
        mark_completed(course_file)


def file_detail(request: HttpRequest, course_pk: int, file_pk: int) -> HttpResponse:
    """View a single course file."""
    course = get_object_or_404(Course, pk=course_pk)
    file = get_object_or_404(CourseFile, pk=file_pk, course=course)

    from domain.skills.storage_mapping import resolve_absolute
    from domain.skills.media_understanding import discover_subtitles

    absolute_path = resolve_absolute(course.workspace.course_root, file.relative_path)

    metadata_model = None
    subtitles = []
    if file.file_type in ("video", "audio"):
        metadata_model = extract_and_save_metadata(file)
        subtitles = discover_subtitles(absolute_path, course.workspace.course_root)

    progress = get_file_progress(file)

    return render(
        request,
        "courses/file_detail.html",
        {
            "course": course,
            "file": file,
            "file_path": str(absolute_path),
            "metadata": metadata_model,
            "subtitles": subtitles,
            "progress": progress,
        },
    )
