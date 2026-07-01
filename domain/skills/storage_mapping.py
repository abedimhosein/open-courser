"""
Storage Mapping Skill

Owned by: Storage Mapping Agent
Purpose: Resolve relative paths, enforce course root boundaries,
         normalize paths, and prevent path traversal.

This is the foundational skill used by all domain agents that
need to access the filesystem.
"""

from dataclasses import dataclass
from pathlib import Path


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
    root = Path(course_root).resolve()

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
    result = validate_and_resolve(course_root, relative_path)

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
