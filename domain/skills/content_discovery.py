"""
Content Discovery Skill

Owned by: File System Agent
Purpose: Scan course root directories, build hierarchical file trees,
         and produce deterministic file indexes using relative paths only.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


HIDDEN_PREFIXES = (".", "_")
HIDDEN_NAMES = {
    "thumbs.db",
    "desktop.ini",
    ".ds_store",
    "node_modules",
    "__pycache__",
    ".git",
    ".svn",
}


@dataclass(frozen=True)
class FileInfo:
    relative_path: str
    name: str
    size: int | None
    modified_at: float | None
    is_directory: bool
    extension: str = ""


@dataclass(frozen=True)
class ChangeSet:
    added: list[FileInfo] = field(default_factory=list)
    modified: list[FileInfo] = field(default_factory=list)
    deleted: list[FileInfo] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.deleted)


@dataclass(frozen=True)
class ScanResult:
    files: list[FileInfo]
    directories: list[str]
    change_set: ChangeSet | None = None


def _is_hidden(entry: os.DirEntry) -> bool:
    """Check if a directory entry should be ignored."""
    name = entry.name.lower()
    if name.startswith(HIDDEN_PREFIXES):
        return True
    if name in HIDDEN_NAMES:
        return True
    return False


def _get_extension(entry: os.DirEntry) -> str:
    """Get the lowercase extension of a file."""
    _, ext = os.path.splitext(entry.name)
    return ext.lower()


def scan_directory(root_path: str | Path) -> ScanResult:
    """
    Perform a full scan of a course root directory.

    Returns a ScanResult containing all files and directories
    as relative paths from the root.
    """
    root = Path(root_path).resolve()

    if not root.exists():
        return ScanResult(files=[], directories=[])

    if not root.is_dir():
        return ScanResult(files=[], directories=[])

    files: list[FileInfo] = []
    directories: list[str] = []

    for entry in _walk_scandir(root):
        entry_path = Path(entry.path)
        relative = os.path.normpath(str(entry_path.relative_to(root))).replace(
            "\\", "/"
        )

        if entry.is_dir():
            directories.append(relative)
        else:
            stat = entry.stat()
            files.append(
                FileInfo(
                    relative_path=relative,
                    name=entry.name,
                    size=stat.st_size,
                    modified_at=stat.st_mtime,
                    is_directory=False,
                    extension=_get_extension(entry),
                )
            )

    files.sort(key=lambda f: f.relative_path)
    directories.sort()

    return ScanResult(files=files, directories=directories)


def _walk_scandir(root: Path) -> Iterator[os.DirEntry]:
    """
    Walk a directory tree using os.scandir, skipping hidden entries.

    Preferred over os.walk for performance with large directories.
    """
    stack = [root]

    while stack:
        current = stack.pop()

        try:
            with os.scandir(current) as it:
                entries = list(it)
        except PermissionError:
            continue
        except OSError:
            continue

        for entry in entries:
            if _is_hidden(entry):
                continue

            yield entry

            if entry.is_dir(follow_symlinks=False):
                stack.append(entry.path)


def scan_incremental(
    root_path: str | Path,
    previous_snapshot: dict[str, tuple[int | None, float | None]],
) -> ScanResult:
    """
    Perform an incremental scan, detecting changes from a previous snapshot.

    The snapshot maps relative_path -> (size, modified_at).
    Returns a ScanResult with a ChangeSet indicating what changed.
    """
    current = scan_directory(root_path)
    current_map = {
        f.relative_path: (f.size, f.modified_at) for f in current.files
    }

    added: list[FileInfo] = []
    modified: list[FileInfo] = []
    deleted: list[FileInfo] = []

    for file_info in current.files:
        rp = file_info.relative_path
        if rp not in previous_snapshot:
            added.append(file_info)
        else:
            prev_size, prev_mtime = previous_snapshot[rp]
            if file_info.size != prev_size or file_info.modified_at != prev_mtime:
                modified.append(file_info)

    for rp in previous_snapshot:
        if rp not in current_map:
            deleted.append(
                FileInfo(
                    relative_path=rp,
                    name=Path(rp).name,
                    size=None,
                    modified_at=None,
                    is_directory=False,
                    extension=Path(rp).suffix.lower(),
                )
            )

    change_set = ChangeSet(added=added, modified=modified, deleted=deleted)

    return ScanResult(
        files=current.files,
        directories=current.directories,
        change_set=change_set,
    )


def build_snapshot(files: list[FileInfo]) -> dict[str, tuple[int | None, float | None]]:
    """
    Build a snapshot dictionary from a list of FileInfo for incremental scanning.
    """
    return {f.relative_path: (f.size, f.modified_at) for f in files}
