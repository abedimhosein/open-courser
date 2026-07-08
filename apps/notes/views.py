import re
import markdown
from pathlib import Path
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404

from apps.notes.models import Note
from apps.courses.models import CourseNode, Course
from apps.workspaces.models import Workspace
from domain.skills.storage_mapping import resolve_absolute


def _render_markdown(content: str) -> str:
    """Render Markdown content to HTML."""
    return markdown.markdown(
        content,
        extensions=["fenced_code", "tables", "nl2br"],
    )


def note_list_partial(request: WSGIRequest, course_pk: int, node_pk: int) -> HttpResponse:
    """HTMX partial - returns notes list for a course node."""
    node = get_object_or_404(CourseNode, pk=node_pk, course_id=course_pk)
    notes = node.notes.all()

    return render(
        request,
        "notes/_note_list.html",
        {
            "node": node,
            "notes": notes,
        },
    )


def note_create(request: WSGIRequest, course_pk: int, node_pk: int) -> HttpResponse:
    """Create a new note for a course node."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    node = get_object_or_404(CourseNode, pk=node_pk, course_id=course_pk)
    content = request.POST.get("content", "").strip()

    if not content:
        notes = node.notes.all()
        return render(
            request,
            "notes/_note_list.html",
            {
                "node": node,
                "notes": notes,
                "error": "Note content is required.",
            },
        )

    note = Note.objects.create(course_node=node, content=content)

    return render(
        request,
        "notes/_note_item.html",
        {
            "node": node,
            "note": note,
        },
    )


def note_from_subtitle(request: WSGIRequest, course_pk: int, node_pk: int) -> HttpResponse:
    """Create a note from a subtitle file's content."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    course = get_object_or_404(Course, pk=course_pk)
    node = get_object_or_404(CourseNode, pk=node_pk, course_id=course_pk)
    sub_path = request.POST.get("sub_path", "").strip()

    if not sub_path:
        return HttpResponse(status=204)

    try:
        absolute_path = resolve_absolute(course.root_path, sub_path)
    except Exception:
        return HttpResponse(status=204)

    path = Path(absolute_path)
    if not path.exists():
        return HttpResponse(status=204)

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return HttpResponse(status=204)

    # Clean subtitle content into readable text
    content = _clean_subtitle(raw, path.suffix.lower())

    if not content.strip():
        return HttpResponse(status=204)

    note = Note.objects.create(course_node=node, content=content)

    notes = node.notes.all()
    return render(
        request,
        "notes/_note_list.html",
        {
            "node": node,
            "notes": notes,
        },
    )


def _clean_subtitle(raw: str, ext: str) -> str:
    """Convert SRT/VTT content to clean readable text."""
    # Remove VTT header
    if raw.startswith("WEBVTT"):
        raw = raw[6:]
    # Remove blank lines and metadata
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip sequence numbers (SRT)
        if re.match(r"^\d+$", line):
            continue
        # Skip timestamps
        if re.match(r"[\d:,.]+ --> [\d:,.]+", line):
            continue
        # Skip VTT metadata
        if line.startswith("NOTE") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        lines.append(line)
    # Deduplicate consecutive identical lines
    deduped = []
    for line in lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)
    return "\n".join(deduped)


def note_edit(request: WSGIRequest, pk: int) -> HttpResponse:
    """Inline edit a note (HTMX swap)."""
    note = get_object_or_404(Note, pk=pk)

    if request.method == "GET":
        return render(
            request,
            "notes/_note_form.html",
            {
                "node": note.course_node,
                "note": note,
            },
        )

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST", "GET"])

    content = request.POST.get("content", "").strip()
    if not content:
        return render(
            request,
            "notes/_note_form.html",
            {
                "node": note.course_node,
                "note": note,
                "error": "Note content is required.",
            },
        )

    note.content = content
    note.save()

    return render(
        request,
        "notes/_note_item.html",
        {
            "node": note.course_node,
            "note": note,
        },
    )


def note_delete(request: WSGIRequest, pk: int) -> HttpResponse:
    """Delete a note."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    note = get_object_or_404(Note, pk=pk)
    node = note.course_node
    note.delete()

    notes = node.notes.all()
    return render(
        request,
        "notes/_note_list.html",
        {
            "node": node,
            "notes": notes,
        },
    )


def notes_search(request: WSGIRequest) -> HttpResponse:
    """Search all notes with workspace and course filters."""
    query = request.GET.get("q", "").strip()
    workspace_id = request.GET.get("workspace", "")
    course_id = request.GET.get("course", "")

    notes = Note.objects.select_related(
        "course_node", "course_node__course", "course_node__course__workspace"
    )

    if query:
        notes = notes.filter(content__icontains=query)
    if workspace_id:
        notes = notes.filter(course_node__course__workspace_id=workspace_id)
    if course_id:
        notes = notes.filter(course_node__course_id=course_id)

    notes = notes[:100]

    workspaces = Workspace.objects.all()
    courses = Course.objects.all()
    if workspace_id:
        courses = courses.filter(workspace_id=workspace_id)

    # Render Markdown for each note
    notes_with_html = []
    for note in notes:
        notes_with_html.append({
            "note": note,
            "content_html": _render_markdown(note.content),
        })

    return render(
        request,
        "notes/search.html",
        {
            "query": query,
            "notes": notes_with_html,
            "workspaces": workspaces,
            "courses": courses,
            "selected_workspace": workspace_id,
            "selected_course": course_id,
        },
    )
