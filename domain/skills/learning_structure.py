"""
Learning Structure Skill

Owned by: Learning Structure Agent
Purpose: Transform discovered course content into a navigable,
         UI-ready tree structure with stable identifiers and
         lazy-loading support.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class TreeNode:
    id: str
    name: str
    node_type: str  # "course", "folder", "file"
    relative_path: str
    has_children: bool = False
    children: Optional[list["TreeNode"]] = None
    file_type: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class NavigationTree:
    nodes: list[TreeNode]
    total_nodes: int = 0


def build_navigation_tree(
    files: list[dict],
    course_relative_path: str,
    course_name: str,
) -> NavigationTree:
    """
    Build a navigation tree from a list of file dictionaries.

    Each file dict should have:
        relative_path: str
        name: str
        file_type: str (optional)
    """
    tree: dict[str, dict] = {}
    all_nodes: list[TreeNode] = []

    for file_info in files:
        rp = file_info["relative_path"]
        parts = rp.split("/")
        current = tree

        for i, part in enumerate(parts):
            if part not in current:
                current[part] = {}
            current = current[part]

    def _build_subtree(
        subtree: dict,
        parent_path: str,
        level: int,
    ) -> list[TreeNode]:
        nodes: list[TreeNode] = []
        entries = sorted(subtree.items())

        for name, children in entries:
            node_path = f"{parent_path}/{name}" if parent_path else name
            is_leaf = len(children) == 0
            node_id = _generate_node_id(node_path, course_relative_path)

            if is_leaf:
                matching_files = [
                    f for f in files if f["relative_path"] == node_path
                ]
                file_type = matching_files[0].get("file_type") if matching_files else None

                nodes.append(
                    TreeNode(
                        id=node_id,
                        name=name,
                        node_type="file",
                        relative_path=node_path,
                        has_children=False,
                        file_type=file_type,
                    )
                )
            else:
                child_nodes = _build_subtree(children, node_path, level + 1)
                nodes.append(
                    TreeNode(
                        id=node_id,
                        name=name,
                        node_type="folder",
                        relative_path=node_path,
                        has_children=True,
                        children=child_nodes,
                    )
                )

        return nodes

    children = _build_subtree(tree, "", 0)

    root_node = TreeNode(
        id=_generate_node_id(course_relative_path, course_relative_path),
        name=course_name,
        node_type="course",
        relative_path=course_relative_path,
        has_children=True,
        children=children,
    )

    def _count_nodes(node: TreeNode) -> int:
        count = 1
        if node.children:
            for child in node.children:
                count += _count_nodes(child)
        return count

    return NavigationTree(
        nodes=[root_node],
        total_nodes=_count_nodes(root_node),
    )


def build_subtree(
    files: list[dict],
    parent_path: str,
    course_relative_path: str,
) -> list[TreeNode]:
    """
    Build only a subtree for lazy loading.

    Returns only the direct children of parent_path.
    """
    children: dict[str, list[dict]] = {}

    for file_info in files:
        rp = file_info["relative_path"]
        if not rp.startswith(parent_path):
            continue

        remaining = rp[len(parent_path):].strip("/")
        if not remaining:
            continue

        child_name = remaining.split("/")[0]

        if child_name not in children:
            children[child_name] = []
        children[child_name].append(file_info)

    result: list[TreeNode] = []

    for name, matching_files in sorted(children.items()):
        child_path = f"{parent_path}/{name}" if parent_path else name
        node_id = _generate_node_id(child_path, course_relative_path)

        is_leaf = all(
            f["relative_path"] == child_path for f in matching_files
        )

        if is_leaf or len(matching_files) == 1:
            file_type = matching_files[0].get("file_type") if matching_files else None
            result.append(
                TreeNode(
                    id=node_id,
                    name=name,
                    node_type="file",
                    relative_path=child_path,
                    has_children=False,
                    file_type=file_type,
                )
            )
        else:
            result.append(
                TreeNode(
                    id=node_id,
                    name=name,
                    node_type="folder",
                    relative_path=child_path,
                    has_children=True,
                )
            )

    return result


def _generate_node_id(relative_path: str, course_path: str) -> str:
    """Generate a stable, deterministic node identifier."""
    clean_path = relative_path.replace("\\", "/").strip("/")
    clean_course = course_path.replace("\\", "/").strip("/")
    return f"{clean_course}:{clean_path}" if clean_path else clean_course
