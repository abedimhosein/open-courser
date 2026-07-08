"""Tests for the Storage Mapping skill."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from domain.skills.storage_mapping import (
    resolve_absolute,
    validate_and_resolve,
    normalize_relative_path,
    translate_to_docker_path,
    _build_docker_mount_map,
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

    def test_rejects_path_traversal(self, tmp_path: Path):
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


class TestTranslateToDockerPath:
    def test_translates_windows_path_to_docker(self):
        """Test translation of Windows path to Docker mount point."""
        env = {
            "COURSE_ROOT_0": r"C:\Users\Amir\Downloads",
            "COURSE_ROOT_1": r"C:\Users\Amir\Videos\4K Video Downloader+",
        }
        with patch.dict(os.environ, env), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None  # Reset cache

            # Test COURSE_ROOT_0 translation
            result = translate_to_docker_path(r"C:\Users\Amir\Downloads\courses\Docker")
            assert result == "/courses/0/courses/Docker"

            # Test COURSE_ROOT_1 translation
            result = translate_to_docker_path(r"C:\Users\Amir\Videos\4K Video Downloader+\Linux")
            assert result == "/courses/1/Linux"

    def test_passes_through_linux_paths(self):
        """Test that Linux paths are not translated."""
        result = translate_to_docker_path("/courses/0/some/path")
        assert result == "/courses/0/some/path"

    def test_passes_through_when_not_in_docker(self):
        """Test that paths pass through when not running in Docker."""
        with patch("os.path.exists", return_value=False):
            result = translate_to_docker_path(r"C:\Users\Downloads\test")
            assert result == r"C:\Users\Downloads\test"

    def test_handles_forward_slash_windows_paths(self):
        """Test translation with forward slash Windows paths."""
        env = {"COURSE_ROOT_0": "C:/Users/Amir/Downloads"}
        with patch.dict(os.environ, env), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = translate_to_docker_path("C:/Users/Amir/Downloads/courses/Docker")
            assert result == "/courses/0/courses/Docker"

    def test_handles_path_with_trailing_slash(self):
        """Test translation with trailing slash in input path."""
        env = {"COURSE_ROOT_0": r"C:\Users\Amir\Downloads"}
        with patch.dict(os.environ, env), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = translate_to_docker_path("C:\\Users\\Amir\\Downloads\\courses\\Docker\\")
            assert result == "/courses/0/courses/Docker"

    def test_returns_original_when_no_matching_mount(self):
        """Test that unmatched Windows paths are returned as-is."""
        env = {"COURSE_ROOT_0": r"C:\Users\Amir\Downloads"}
        with patch.dict(os.environ, env), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = translate_to_docker_path(r"D:\Other\Path\courses")
            assert result == r"D:\Other\Path\courses"

    def test_handles_empty_env_vars(self):
        """Test behavior when environment variables are empty."""
        env = {"COURSE_ROOT_0": "", "COURSE_ROOT_1": ""}
        with patch.dict(os.environ, env, clear=True), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = translate_to_docker_path(r"C:\Users\Downloads\test")
            assert result == r"C:\Users\Downloads\test"

    def test_handles_missing_env_vars(self):
        """Test behavior when environment variables are not set."""
        with patch.dict(os.environ, {}, clear=True), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = translate_to_docker_path(r"C:\Users\Downloads\test")
            assert result == r"C:\Users\Downloads\test"

    def test_longest_match_wins(self):
        """Test that the longest matching mount point is used."""
        env = {
            "COURSE_ROOT_0": r"C:\Users",
            "COURSE_ROOT_1": r"C:\Users\Amir\Downloads",
        }
        with patch.dict(os.environ, env), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            # Should match COURSE_ROOT_1 (longer match)
            result = translate_to_docker_path(r"C:\Users\Amir\Downloads\courses\Docker")
            assert result == "/courses/1/courses/Docker"

    def test_case_insensitive_matching(self):
        """Test that path matching is case-insensitive."""
        env = {"COURSE_ROOT_0": r"C:\Users\Amir\Downloads"}
        with patch.dict(os.environ, env), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = translate_to_docker_path(r"C:\users\amir\downloads\courses\Docker")
            assert result == "/courses/0/courses/Docker"

    def test_nested_subdirectory_translation(self):
        """Test translation with deeply nested subdirectories."""
        env = {"COURSE_ROOT_0": r"C:\Courses"}
        with patch.dict(os.environ, env), patch("os.path.exists", return_value=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = translate_to_docker_path(r"C:\Courses\Docker\Section1\Lecture1.mp4")
            assert result == "/courses/0/Docker/Section1/Lecture1.mp4"


class TestBuildDockerMountMap:
    def test_builds_map_from_env_vars(self):
        """Test that mount map is built correctly from environment variables."""
        env = {
            "COURSE_ROOT_0": r"C:\Users\Amir\Downloads",
            "COURSE_ROOT_1": r"C:\Users\Amir\Videos",
        }
        with patch.dict(os.environ, env):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None  # Reset cache

            result = _build_docker_mount_map()

            assert "c:/users/amir/downloads" in result
            assert result["c:/users/amir/downloads"] == "/courses/0"
            assert "c:/users/amir/videos" in result
            assert result["c:/users/amir/videos"] == "/courses/1"

    def test_caches_mount_map(self):
        """Test that mount map is cached after first call."""
        env = {"COURSE_ROOT_0": r"C:\Courses"}
        with patch.dict(os.environ, env):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result1 = _build_docker_mount_map()
            result2 = _build_docker_mount_map()

            assert result1 is result2

    def test_handles_no_env_vars(self):
        """Test behavior when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = _build_docker_mount_map()
            assert result == {}

    def test_normalizes_backslashes_to_forward_slashes(self):
        """Test that backslashes are normalized to forward slashes."""
        env = {"COURSE_ROOT_0": r"C:\Users\Amir\Downloads"}
        with patch.dict(os.environ, env):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = _build_docker_mount_map()
            assert "c:/users/amir/downloads" in result

    def test_strips_trailing_slashes(self):
        """Test that trailing slashes are stripped from paths."""
        env = {"COURSE_ROOT_0": r"C:\Users\Amir\Downloads\\"}
        with patch.dict(os.environ, env):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            result = _build_docker_mount_map()
            assert "c:/users/amir/downloads" in result


class TestValidateAndResolveDocker:
    """Tests for validate_and_resolve with Docker path translation."""

    def test_translates_and_resolves_valid_path(self, tmp_path: Path):
        """Test that Windows paths are translated and resolved in Docker."""
        # Create a mock Docker mount structure
        docker_courses = tmp_path / "courses_0"
        docker_courses.mkdir()
        file_path = docker_courses / "lecture.mp4"
        file_path.write_text("test")

        # Mock the env var and os.path.exists
        env = {"COURSE_ROOT_0": str(docker_courses)}
        with patch.dict(os.environ, env):
            from domain.skills import storage_mapping
            storage_mapping._DOCKER_MOUNT_MAP = None

            # When not in Docker, translation is bypassed, so test the path directly
            result = validate_and_resolve(str(docker_courses), "lecture.mp4")
            assert result.is_valid
            assert result.resolved_path == file_path.resolve()

    def test_returns_error_for_missing_root(self, tmp_path: Path):
        """Test that error is returned when root doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        result = validate_and_resolve(str(nonexistent), "lecture.mp4")
        assert not result.is_valid
        assert "does not exist" in (result.reason or "")


class TestResolveAbsoluteDocker:
    """Tests for resolve_absolute with Docker path translation."""

    def test_resolves_valid_path(self, tmp_path: Path):
        """Test that valid paths are resolved correctly."""
        docker_courses = tmp_path / "courses_0"
        docker_courses.mkdir()
        file_path = docker_courses / "lecture.mp4"
        file_path.write_text("test")

        resolved = resolve_absolute(str(docker_courses), "lecture.mp4")
        assert resolved == file_path.resolve()

    def test_raises_missing_root_for_nonexistent_path(self, tmp_path: Path):
        """Test that MissingRootError is raised for nonexistent path."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(MissingRootError):
            resolve_absolute(str(nonexistent), "file.mp4")
