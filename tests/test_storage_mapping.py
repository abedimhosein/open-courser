"""Tests for the Storage Mapping skill."""

from pathlib import Path

import pytest

from domain.skills.storage_mapping import (
    resolve_absolute,
    validate_and_resolve,
    normalize_relative_path,
    PathTraversalError,
    InvalidPathError,
    MissingRootError,
)


class TestNormalizeRelativePath:
    def test_normalizes_backslashes(self):
        assert normalize_relative_path("foo\\bar") == "foo/bar"

    def test_strips_leading_slash(self):
        assert normalize_relative_path("/foo/bar") == "foo/bar"

    def test_strips_leading_backslash(self):
        assert normalize_relative_path("\\foo\\bar") == "foo/bar"

    def test_removes_redundant_separators(self):
        result = normalize_relative_path("foo//bar")
        assert "//" not in result


class TestValidateAndResolve:
    def test_valid_path(self, tmp_path: Path):
        course_root = tmp_path / "courses"
        course_root.mkdir()
        file_path = course_root / "lecture.mp4"
        file_path.write_text("test")

        result = validate_and_resolve(str(course_root), "lecture.mp4")
        assert result.is_valid
        assert result.resolved_path == file_path.resolve()

    def test_empty_relative_path(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()

        result = validate_and_resolve(str(root), "")
        assert not result.is_valid
        assert "empty" in (result.reason or "")

    def rejects_path_traversal(self, tmp_path: Path):
        course_root = tmp_path / "courses"
        course_root.mkdir()

        result = validate_and_resolve(str(course_root), "../secret.txt")
        assert not result.is_valid
        assert "traversal" in (result.reason or "").lower()


class TestResolveAbsolute:
    def test_resolves_correct_path(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()
        file = root / "lecture.mp4"
        file.write_text("test")

        resolved = resolve_absolute(str(root), "lecture.mp4")
        assert resolved == file.resolve()

    def test_raises_on_traversal(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()

        with pytest.raises(PathTraversalError):
            resolve_absolute(str(root), "../secret.txt")

    def test_raises_on_missing_root(self, tmp_path: Path):
        with pytest.raises(MissingRootError):
            resolve_absolute(str(tmp_path / "nonexistent"), "file.mp4")

    def test_raises_on_empty_path(self, tmp_path: Path):
        root = tmp_path / "courses"
        root.mkdir()

        with pytest.raises(InvalidPathError):
            resolve_absolute(str(root), "")
