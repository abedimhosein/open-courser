"""
Media Understanding Skill

Owned by: Media Processing Agent
Purpose: Extract media metadata using ffprobe, discover associated
         subtitle files, and provide standardized metadata for playback.
"""

import json
import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from domain.skills.storage_mapping import translate_to_docker_path

SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass"}


@dataclass(frozen=True)
class MediaMetadata:
    duration: float | None = None
    codec: str | None = None
    width: int | None = None
    height: int | None = None
    bitrate: int | None = None
    file_format: str | None = None
    has_audio: bool = False
    has_video: bool = False


@dataclass(frozen=True)
class SubtitleInfo:
    relative_path: str
    language: str | None = None
    format: str = ""


@dataclass(frozen=True)
class MediaExtractionResult:
    metadata: MediaMetadata | None = None
    subtitles: list[SubtitleInfo] = field(default_factory=list)
    error: str | None = None
    is_supported: bool = True


def extract_metadata(file_path: str | Path) -> MediaExtractionResult:
    """
    Extract metadata from a media file using ffprobe.

    Returns a MediaExtractionResult with metadata or error information.
    """
    path = Path(file_path)

    if not path.exists():
        return MediaExtractionResult(
            metadata=None,
            error=f"File not found: {path}",
            is_supported=False,
        )

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except FileNotFoundError:
        return _extract_metadata_fallback(path)
    except subprocess.TimeoutExpired:
        return MediaExtractionResult(
            metadata=None,
            error="ffprobe timed out",
            is_supported=False,
        )

    if result.returncode != 0:
        return MediaExtractionResult(
            metadata=None,
            error=result.stderr.strip() or "Unknown ffprobe error",
            is_supported=False,
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return MediaExtractionResult(
            metadata=None,
            error="Failed to parse ffprobe output",
            is_supported=False,
        )

    return _parse_ffprobe_output(data)


def _parse_ffprobe_output(data: dict) -> MediaExtractionResult:
    """Parse ffprobe JSON output into MediaMetadata."""
    format_info = data.get("format", {})
    streams = data.get("streams", [])

    duration = _safe_float(format_info.get("duration"))
    bitrate = _safe_int(format_info.get("bit_rate"))
    file_format = format_info.get("format_name")

    video_stream = None
    audio_stream = None

    for stream in streams:
        codec_type = stream.get("codec_type")
        if codec_type == "video" and video_stream is None:
            video_stream = stream
        elif codec_type == "audio" and audio_stream is None:
            audio_stream = stream

    codec = None
    width = None
    height = None

    if video_stream:
        codec = video_stream.get("codec_name")
        width = _safe_int(video_stream.get("width"))
        height = _safe_int(video_stream.get("height"))

    metadata = MediaMetadata(
        duration=duration,
        codec=codec,
        width=width,
        height=height,
        bitrate=bitrate,
        file_format=file_format,
        has_audio=audio_stream is not None,
        has_video=video_stream is not None,
    )

    return MediaExtractionResult(metadata=metadata, is_supported=True)


def discover_subtitles(media_path: str | Path, course_root: str | Path) -> list[SubtitleInfo]:
    """
    Discover subtitle files associated with a media file.

    Uses base filename matching within the same directory.
    """
    media = Path(media_path)
    root = Path(translate_to_docker_path(str(course_root))).resolve()

    media_stem = media.stem
    media_dir = media.parent

    subtitles: list[SubtitleInfo] = []

    if not media_dir.exists():
        return subtitles

    for entry in media_dir.iterdir():
        if entry.suffix.lower() not in SUBTITLE_EXTENSIONS:
            continue

        entry_stem = entry.stem

        # Remove language suffix like .en, .fr from subtitle filename
        base_stem = entry_stem
        lang = None
        if "." in entry_stem:
            parts = entry_stem.rsplit(".", 1)
            if len(parts[1]) in (2, 3) and parts[1].isalpha():
                base_stem = parts[0]
                lang = parts[1]

        if base_stem == media_stem:
            try:
                relative = entry.relative_to(root).as_posix()
            except ValueError:
                relative = entry.name

            subtitles.append(
                SubtitleInfo(
                    relative_path=relative,
                    language=lang,
                    format=entry.suffix.lstrip("."),
                )
            )

    return subtitles


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


MEDIA_EXTENSIONS = {
    ".mp4", ".m4v", ".m4a", ".mov", ".mkv",
    ".webm", ".avi", ".mp3", ".wav", ".flac", ".aac", ".ogg",
}


def _extract_metadata_fallback(path: Path) -> MediaExtractionResult:
    """Extract basic metadata without ffprobe by parsing file headers."""
    ext = path.suffix.lower()
    file_format = ext.lstrip(".")

    if ext not in MEDIA_EXTENSIONS:
        return MediaExtractionResult(
            metadata=None,
            error=f"No metadata extractor for {ext} files",
            is_supported=False,
        )

    if ext in (".mp4", ".m4v", ".m4a", ".mov"):
        return _parse_mp4_header(path, file_format)

    if ext == ".mkv":
        return _parse_mkv_header(path, file_format)

    return MediaExtractionResult(
        metadata=MediaMetadata(file_format=file_format or None),
        is_supported=True,
    )


def _find_mdat_end(data: bytes, file_size: int) -> int | None:
    """Find the end of the mdat atom to locate where moov should follow."""
    i = 0
    while i < len(data) - 8:
        atom_size = struct.unpack_from(">I", data, i)[0]
        atom_type = data[i + 4: i + 8]
        if atom_type == b"mdat":
            if atom_size == 1 and i + 16 <= len(data):
                # 64-bit size
                extended_size = struct.unpack_from(">Q", data, i + 8)[0]
                return i + extended_size
            return i + atom_size
        if atom_size == 0:
            break
        i += atom_size
    return None


def _parse_mp4_header(path: Path, file_format: str) -> MediaExtractionResult:
    """Extract duration from MP4/M4V/MOV file by parsing the mvhd atom."""
    try:
        file_size = path.stat().st_size
        read_size = min(file_size, 4 * 1024 * 1024)  # up to 4MB for moov
        with open(path, "rb") as f:
            head = f.read(min(file_size, 65536))
            tail = b""
            # Search head for moov (fast-start MP4s put moov first)
            data = head
            moov_start = _find_mp4_atom(data, b"moov")
            if moov_start is None and file_size > 65536:
                # Not in head — read tail of file (moov is typically at end)
                tail_size = min(file_size, read_size)
                f.seek(file_size - tail_size)
                tail = f.read(tail_size)
                data = tail
            elif moov_start is None:
                data = head
    except OSError:
        return MediaExtractionResult(
            metadata=None,
            error=f"Cannot read file: {path}",
            is_supported=False,
        )

    moov_start = _find_mp4_atom(data, b"moov")
    if moov_start is None:
        return MediaExtractionResult(
            metadata=MediaMetadata(file_format=file_format),
            is_supported=True,
        )

    # Read up to 8KB from moov atom to find mvhd
    moov_data = data[moov_start + 8:]
    mvhd_start = _find_mp4_atom(moov_data, b"mvhd")
    if mvhd_start is None:
        return MediaExtractionResult(
            metadata=MediaMetadata(file_format=file_format),
            is_supported=True,
        )

    mvhd = moov_data[mvhd_start + 8:]
    if len(mvhd) < 20:
        return MediaExtractionResult(
            metadata=MediaMetadata(file_format=file_format),
            is_supported=True,
        )

    version = mvhd[0]

    if version == 0:
        if len(mvhd) < 20:
            return MediaExtractionResult(
                metadata=MediaMetadata(file_format=file_format),
                is_supported=True,
            )
        timescale = struct.unpack_from(">I", mvhd, 12)[0]
        duration = struct.unpack_from(">I", mvhd, 16)[0]
    else:
        if len(mvhd) < 28:
            return MediaExtractionResult(
                metadata=MediaMetadata(file_format=file_format),
                is_supported=True,
            )
        timescale = struct.unpack_from(">I", mvhd, 20)[0]
        duration = struct.unpack_from(">Q", mvhd, 24)[0]

    duration_sec = duration / timescale if timescale > 0 else None

    return MediaExtractionResult(
        metadata=MediaMetadata(
            duration=duration_sec,
            file_format=file_format,
            has_video=file_format in ("mp4", "m4v", "mov"),
            has_audio=True,
        ),
        is_supported=True,
    )


def _find_mp4_atom(data: bytes, target: bytes) -> int | None:
    """Find the position of an MP4 atom in binary data."""
    i = 0
    while i < len(data) - 8:
        atom_size = struct.unpack_from(">I", data, i)[0]
        atom_type = data[i + 4: i + 8]
        if atom_type == target:
            return i
        if atom_size == 0:
            break
        i += atom_size
    return None


def _parse_mkv_header(path: Path, file_format: str) -> MediaExtractionResult:
    """Extract duration from MKV file by parsing EBML header."""
    try:
        with open(path, "rb") as f:
            data = f.read(8192)
    except OSError:
        return MediaExtractionResult(
            metadata=None,
            error=f"Cannot read file: {path}",
            is_supported=False,
        )

    duration = _find_mkv_duration(data)

    return MediaExtractionResult(
        metadata=MediaMetadata(
            duration=duration,
            file_format=file_format,
            has_video=True,
            has_audio=True,
        ),
        is_supported=True,
    )


def _find_mkv_duration(data: bytes) -> float | None:
    """Search for Duration element in MKV Segment Info."""
    # EBML element IDs
    SEGMENT_ID = 0x18538067
    SEEKHEAD_ID = 0x114D9B74
    INFO_ID = 0x1549A966
    DURATION_ID = 0x4489
    # Segment Info starts after Segment element
    # SeekHead comes before Info, skip it
    i = 0
    while i < len(data) - 4:
        # Look for Segment element
        if i + 4 <= len(data):
            possible_id = struct.unpack(">I", data[i: i + 4])[0]
            if possible_id == SEGMENT_ID:
                seg_size, size_len = _read_ebml_size(data, i + 4)
                if seg_size is None:
                    return None
                seg_end = i + 4 + size_len + seg_size
                i += 4 + size_len
                # Search inside Segment for Info
                return _find_mkv_info_duration(data[i:seg_end])
        i += 1
    return None


def _read_ebml_size(data: bytes, offset: int) -> tuple[int | None, int]:
    """Read an EBML variable-length integer, return (value, bytes_consumed)."""
    if offset >= len(data):
        return None, 0
    first = data[offset]
    # Find the position of the first 1 bit (the marker)
    mask = 0x80
    for i in range(8):
        if first & mask:
            size = first & (mask - 1)
            for j in range(1, i + 1):
                if offset + j >= len(data):
                    return None, 0
                size = (size << 8) | data[offset + j]
            return size, i + 1
        mask >>= 1
    return None, 0


def _find_mkv_info_duration(data: bytes) -> float | None:
    """Find Duration element within MKV Segment Info."""
    INFO_ID = 0x1549A966
    DURATION_ID = 0x4489

    i = 0
    while i < len(data) - 4:
        # Look for Info element
        if i + 4 <= len(data):
            possible_id = struct.unpack(">I", data[i: i + 4])[0]
            if possible_id == INFO_ID:
                info_size, size_len = _read_ebml_size(data, i + 4)
                if info_size is None:
                    return None
                i += 4 + size_len
                info_end = i + info_size
                # Search inside Info for Duration
                while i < info_end - 2:
                    if i + 2 <= len(data):
                        dur_id = struct.unpack(">H", data[i: i + 2])[0]
                        if dur_id == DURATION_ID:
                            dur_size, size_len = _read_ebml_size(data, i + 2)
                            if dur_size is None:
                                return None
                            if dur_size <= 8:
                                val_data = data[i + 2 + size_len: i + 2 + size_len + dur_size]
                                if len(val_data) >= 8:
                                    raw = struct.unpack(">d", val_data[:8])[0]
                                    # MKV Duration is in milliseconds, convert to seconds
                                    return raw / 1000.0
                            return None
                    i += 1
                return None
        i += 1
    return None
