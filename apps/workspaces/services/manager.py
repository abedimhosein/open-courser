"""
Workspace Management Service

Owned by: Backend Django Agent (orchestration)
Purpose: Create, update, and manage workspaces.
"""

from pathlib import Path

from apps.workspaces.models import Workspace


def create_workspace(name: str, course_root: str) -> Workspace:
    """
    Create a new workspace with a validated course root path.
    """
    root = Path(course_root).resolve()

    if not root.exists():
        raise ValueError(f"Course root does not exist: {course_root}")

    if not root.is_dir():
        raise ValueError(f"Course root is not a directory: {course_root}")

    return Workspace.objects.create(
        name=name,
        course_root=str(root),
    )


def delete_workspace(workspace: Workspace) -> None:
    """
    Delete a workspace and all associated data.
    """
    workspace.delete()


def get_all_workspaces():
    """Get all workspaces ordered by name."""
    return Workspace.objects.all()


def get_workspace_by_id(workspace_id: int) -> Workspace | None:
    """Get a workspace by ID."""
    try:
        return Workspace.objects.get(pk=workspace_id)
    except Workspace.DoesNotExist:
        return None
