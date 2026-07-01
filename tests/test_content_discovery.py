"""Tests for the Content Discovery skill."""

from pathlib import Path

from domain.skills.content_discovery import scan_directory, scan_incremental, build_snapshot


class TestScanDirectory:
    def test_returns_empty_for_nonexistent_path(self):
        result = scan_directory("/nonexistent/path")
        assert result.files == []
        assert result.directories == []

    def test_scans_files_recursively(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()
        (root / "lecture1.mp4").write_text("test")
        (root / "lecture2.mp4").write_text("test")
        (root / "subfolder").mkdir()
        (root / "subfolder" / "notes.pdf").write_text("test")

        result = scan_directory(str(root))
        assert len(result.files) == 3
        assert len(result.directories) == 1

    def test_ignores_hidden_files(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()
        (root / "lecture.mp4").write_text("test")
        (root / ".hidden.mp4").write_text("secret")
        (root / "_backup.mp4").write_text("backup")

        result = scan_directory(str(root))
        assert len(result.files) == 1


class TestScanIncremental:
    def test_detects_added_files(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()
        (root / "existing.mp4").write_text("test")

        snapshot: dict = {}
        result = scan_incremental(str(root), snapshot)

        assert result.change_set is not None
        assert len(result.change_set.added) == 1

    def test_no_changes_with_identical_snapshot(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()
        path = root / "file.mp4"
        path.write_text("test")

        current = scan_directory(str(root))
        snapshot = build_snapshot(current.files)

        result = scan_incremental(str(root), snapshot)
        assert result.change_set is not None
        assert not result.change_set.has_changes


class TestBuildSnapshot:
    def test_builds_path_to_size_mtime_map(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()
        f = root / "file.mp4"
        f.write_text("test")

        result = scan_directory(str(root))
        snapshot = build_snapshot(result.files)

        assert "file.mp4" in snapshot
        size, mtime = snapshot["file.mp4"]
        assert size == 4  # "test" = 4 bytes
        assert mtime is not None
