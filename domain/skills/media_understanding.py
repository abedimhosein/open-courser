"""
Media Understanding Skill

Owned by: Media Processing Agent
Purpose: Extract media metadata using ffprobe, discover associated
         subtitle files, and provide standardized metadata for playback.
"""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


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
            timeout=30,
        )
    except FileNotFoundError:
        return MediaExtractionResult(
            metadata=None,
            error="ffprobe not found. Install ffmpeg.",
            is_supported=False,
        )
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


def discover_subtitles(
    media_path: str | Path,
    course_root: str | Path,
) -> list[SubtitleInfo]:
    """
    Discover subtitle files associated with a media file.

    Uses base filename matching within the same directory.
    """
    media = Path(media_path)
    root = Path(course_root).resolve()

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
                relative = str(entry.relative_to(root))
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
