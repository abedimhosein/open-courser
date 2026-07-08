"""Tests for the Media Understanding skill."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from domain.skills.media_understanding import (
    extract_metadata,
    discover_subtitles,
    _parse_ffprobe_output,
    _parse_mp4_header,
    _parse_mkv_header,
    _safe_float,
    _safe_int,
)


class TestSafeFloat:
    def test_converts_valid_string(self):
        assert _safe_float("3.14") == 3.14

    def test_returns_none_for_none(self):
        assert _safe_float(None) is None

    def test_returns_none_for_invalid(self):
        assert _safe_float("abc") is None

    def test_converts_int(self):
        assert _safe_float(42) == 42.0


class TestSafeInt:
    def test_converts_valid_string(self):
        assert _safe_int("42") == 42

    def test_returns_none_for_none(self):
        assert _safe_int(None) is None

    def test_returns_none_for_invalid(self):
        assert _safe_int("abc") is None


class TestParseFfprobeOutput:
    def test_parses_video_metadata(self):
        data = {
            "format": {"duration": "120.5", "bit_rate": "1000000", "format_name": "mp4"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }
        result = _parse_ffprobe_output(data)
        assert result.metadata.duration == 120.5
        assert result.metadata.codec == "h264"
        assert result.metadata.width == 1920
        assert result.metadata.height == 1080
        assert result.metadata.has_video is True
        assert result.metadata.has_audio is True

    def test_parses_audio_only(self):
        data = {
            "format": {"duration": "60.0", "format_name": "mp3"},
            "streams": [{"codec_type": "audio", "codec_name": "mp3"}],
        }
        result = _parse_ffprobe_output(data)
        assert result.metadata.has_video is False
        assert result.metadata.has_audio is True
        assert result.metadata.codec is None

    def test_handles_empty_format(self):
        data = {"format": {}, "streams": []}
        result = _parse_ffprobe_output(data)
        assert result.metadata.duration is None


class TestExtractMetadata:
    def test_returns_error_for_missing_file(self, tmp_path: Path):
        result = extract_metadata(str(tmp_path / "nonexistent.mp4"))
        assert result.error is not None
        assert result.is_supported is False

    @patch("domain.skills.media_understanding.subprocess.run")
    def test_calls_ffprobe(self, mock_run, tmp_path: Path):
        fake_file = tmp_path / "test.mp4"
        fake_file.write_bytes(b"\x00" * 100)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "10.0"}, "streams": []}',
            stderr="",
        )
        result = extract_metadata(str(fake_file))
        assert result.metadata.duration == 10.0
        mock_run.assert_called_once()

    @patch("domain.skills.media_understanding.subprocess.run", side_effect=FileNotFoundError)
    def test_falls_back_when_ffprobe_missing(self, mock_run, tmp_path: Path):
        fake_file = tmp_path / "test.mp4"
        fake_file.write_bytes(b"\x00" * 100)
        result = extract_metadata(str(fake_file))
        assert result.is_supported is True


class TestDiscoverSubtitles:
    def test_finds_matching_vtt(self, tmp_path: Path):
        media = tmp_path / "video.mp4"
        media.write_bytes(b"\x00")
        sub = tmp_path / "video.vtt"
        sub.write_text("WEBVTT\n\nHello")
        result = discover_subtitles(str(media), str(tmp_path))
        assert len(result) == 1
        assert result[0].format == "vtt"

    def test_finds_srt_with_language(self, tmp_path: Path):
        media = tmp_path / "video.mp4"
        media.write_bytes(b"\x00")
        sub = tmp_path / "video.en.srt"
        sub.write_text("1\n00:00:01 --> 00:00:02\nHello")
        result = discover_subtitles(str(media), str(tmp_path))
        assert len(result) == 1
        assert result[0].language == "en"
        assert result[0].format == "srt"

    def test_ignores_non_matching_files(self, tmp_path: Path):
        media = tmp_path / "video.mp4"
        media.write_bytes(b"\x00")
        other = tmp_path / "other.vtt"
        other.write_text("WEBVTT\n\nHello")
        result = discover_subtitles(str(media), str(tmp_path))
        assert len(result) == 0

    def test_ignores_non_subtitle_extensions(self, tmp_path: Path):
        media = tmp_path / "video.mp4"
        media.write_bytes(b"\x00")
        txt = tmp_path / "video.txt"
        txt.write_text("not a subtitle")
        result = discover_subtitles(str(media), str(tmp_path))
        assert len(result) == 0


class TestParseMp4Header:
    def test_returns_format_for_unsupported(self, tmp_path: Path):
        f = tmp_path / "test.xyz"
        f.write_bytes(b"\x00" * 100)
        result = _parse_mp4_header(f, "xyz")
        assert result.metadata.file_format == "xyz"
