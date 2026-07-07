"""Utility functions for listing available drives and mount points."""
import platform
import os
from pathlib import Path


def get_available_drives() -> list[dict]:
    """
    Get list of available drives/mount points.
    
    Returns a list of dicts with 'name', 'path', and 'label' keys.
    """
    system = platform.system()
    drives = []
    
    if system == "Windows":
        # Windows: Check drives A: through Z:
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = Path(f"{letter}:\\")
            if drive_path.exists():
                label = _get_windows_drive_label(letter)
                drives.append({
                    "name": f"{letter}:",
                    "path": str(drive_path),
                    "label": label or f"Drive {letter}:",
                })
    else:
        # Linux/macOS: Check common mount points
        mount_bases = ["/mnt", "/media", "/Volumes"]
        
        for base in mount_bases:
            base_path = Path(base)
            if base_path.exists():
                try:
                    for entry in base_path.iterdir():
                        if entry.is_dir():
                            drives.append({
                                "name": entry.name,
                                "path": str(entry),
                                "label": f"{entry.name} ({base})",
                            })
                except PermissionError:
                    continue
        
        # Also include root if it exists
        if Path("/").exists() and not any(d["path"] == "/" for d in drives):
            drives.append({
                "name": "/",
                "path": "/",
                "label": "Root",
            })
        
        # Include home directory
        home = Path.home()
        if home.exists() and not any(d["path"] == str(home) for d in drives):
            drives.append({
                "name": home.name,
                "path": str(home),
                "label": f"Home ({home})",
            })
    
    return drives


def _get_windows_drive_label(letter: str) -> str:
    """Try to get the volume label for a Windows drive."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_unicode_buffer(256)
        kernel32.GetVolumeInformationW(
            f"{letter}:\\",
            buffer,
            256,
            None,
            None,
            None,
            None,
            0,
        )
        return buffer.value if buffer.value else ""
    except Exception:
        return ""
