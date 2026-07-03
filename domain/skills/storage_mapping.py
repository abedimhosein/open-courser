"""
Storage Mapping Skill

Owned by: Storage Mapping Agent
Purpose: Resolve relative paths, enforce course root boundaries,
         normalize paths, and prevent path traversal.

This is the foundational skill used by all domain agents that
need to access the filesystem.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path


# Mapping of Windows base paths to Docker mount points
# Populated from COURSE_ROOT_0, COURSE_ROOT_1 environment variables
_DOCKER_MOUNT_MAP: dict[str, str] | None = None


def _build_docker_mount_map() -> dict[str, str]:
    """Build mapping from Windows paths to Docker mount points."""
    global _DOCKER_MOUNT_MAP
    if _DOCKER_MOUNT_MAP is not None:
        return _DOCKER_MOUNT_MAP

    _DOCKER_MOUNT_MAP = {}
    for i in range(2):
        env_key = f"COURSE_ROOT_{i}"
        docker_path = f"/courses/{i}"
        win_path = os.environ.get(env_key, "")
        if win_path:
            # Normalize Windows path for comparison
            normalized = win_path.replace("\\", "/").rstrip("/").lower()
            _DOCKER_MOUNT_MAP[normalized] = docker_path
    return _DOCKER_MOUNT_MAP


def translate_to_docker_path(path: str) -> str:
    """
    Translate a Windows path to its Docker equivalent if running in container.

    Handles paths like:
    - C:\\Users\\Amir\\Downloads\\courses\\... -> /courses/0/courses/...
    - C:\\Users\\Amir\\Videos\\4K Video Downloader+\\... -> /courses/1/...
    """
    # Only translate if we're inside Docker (check for /app directory)
    if not os.path.exists("/app"):
        return path

    # Check if path looks like a Windows path
    if not re.match(r'^[A-Za-z]:\\', path) and not re.match(r'^[A-Za-z]:/', path):
        return path

    mount_map = _build_docker_mount_map()
    normalized_path = path.replace("\\", "/").rstrip("/")

    # Try to find a matching mount point
    for win_base, docker_base in sorted(mount_map.items(), key=lambda x: -len(x[0])):
        if normalized_path.lower().startswith(win_base):
            # Extract the relative part after the Windows base
            relative_part = normalized_path[len(win_base):]
            # Strip leading slash to avoid double slashes
            relative_part = relative_part.lstrip("/")
            return f"{docker_base}/{relative_part}" if relative_part else docker_base

    return path


@dataclass(frozen=True)
class PathValidationResult:
    is_valid: bool
    resolved_path: Path | None
    reason: str | None


class PathTraversalError(Exception):
    """Raised when a path attempts to escape the course root."""


class InvalidPathError(Exception):
    """Raised when a path is malformed or empty."""


class MissingRootError(Exception):
    """Raised when the course root does not exist."""


def validate_and_resolve(course_root: str | Path, relative_path: str) -> PathValidationResult:
    """
    Resolve a relative path against a course root with security validation.

    Returns a validation result. Does not raise exceptions for recoverable
    validation failures.
    """
    # Translate Windows paths to Docker paths if needed
    translated_root = translate_to_docker_path(str(course_root))
    root = Path(translated_root).resolve()

    if not root.exists():
        return PathValidationResult(
            is_valid=False,
            resolved_path=None,
            reason=f"Course root does not exist: {root}",
        )

    if not relative_path or not relative_path.strip():
        return PathValidationResult(
            is_valid=False,
            resolved_path=None,
            reason="Relative path must not be empty",
        )

    normalized_relative = normalize_relative_path(relative_path)

    candidate = (root / normalized_relative).resolve()

    if not _is_within_root(candidate, root):
        return PathValidationResult(
            is_valid=False,
            resolved_path=None,
            reason="Path traversal detected: resolved path is outside course root",
        )

    return PathValidationResult(
        is_valid=True,
        resolved_path=candidate,
        reason=None,
    )


def resolve_absolute(course_root: str | Path, relative_path: str) -> Path:
    """
    Resolve a relative path to an absolute path with full validation.

    Raises PathTraversalError, InvalidPathError, or MissingRootError
    on validation failure.
    """
    # Translate Windows paths to Docker paths if needed
    translated_root = translate_to_docker_path(str(course_root))
    result = validate_and_resolve(translated_root, relative_path)

    if not result.is_valid:
        reason = result.reason or "Unknown validation error"

        if "does not exist" in reason:
            raise MissingRootError(reason)

        if "traversal" in reason:
            raise PathTraversalError(reason)

        raise InvalidPathError(reason)

    return result.resolved_path


def normalize_relative_path(relative_path: str) -> str:
    """
    Normalize a relative path for consistent storage and comparison.

    - Converts backslashes to forward slashes
    - Strips leading slashes
    - Removes redundant separators
    """
    normalized = relative_path.replace("\\", "/")
    normalized = normalized.strip("/")
    parts = [p for p in normalized.split("/") if p]
    return "/".join(parts)


def is_within_root(path: Path, root: Path) -> bool:
    """Check whether a resolved path is within the course root boundary."""
    return _is_within_root(path.resolve(), root.resolve())


def _is_within_root(resolved: Path, root: Path) -> bool:
    """Internal check - assumes both paths are already resolved."""
    try:
        resolved.relative_to(root)
        return True
    except ValueError:
        return False
