from apps.workspaces.models import Workspace


def create_workspace(name: str, description: str = "") -> Workspace:
    """
    Create a new workspace.
    Workspace is a logical category, not a filesystem concept.
    """
    return Workspace.objects.create(
        name=name,
        description=description,
    )


def delete_workspace(workspace: Workspace) -> None:
    """
    Delete a workspace and all associated data.
    """
    workspace.delete()
