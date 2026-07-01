"""Tests for the Learning Structure skill."""

from domain.skills.learning_structure import build_navigation_tree, build_subtree


class TestBuildNavigationTree:
    def test_builds_tree_from_file_list(self):
        files = [
            {"relative_path": "course/lecture1.mp4", "name": "lecture1.mp4", "file_type": "video"},
            {"relative_path": "course/lecture2.mp4", "name": "lecture2.mp4", "file_type": "video"},
            {"relative_path": "course/notes/reading.pdf", "name": "reading.pdf", "file_type": "document"},
        ]

        tree = build_navigation_tree(files, "course", "Test Course")
        # root course -> course folder -> 2 files + notes folder -> reading.pdf
        assert tree.total_nodes == 6

        root = tree.nodes[0]
        assert root.node_type == "course"
        assert root.name == "Test Course"
        assert root.has_children
        assert root.children is not None


class TestBuildSubtree:
    def test_returns_direct_children(self):
        files = [
            {"relative_path": "course/lecture1.mp4", "name": "lecture1.mp4", "file_type": "video"},
            {"relative_path": "course/notes/reading.pdf", "name": "reading.pdf", "file_type": "document"},
        ]

        nodes = build_subtree(files, "course", "course")
        assert len(nodes) == 2  # 1 file + 1 folder
