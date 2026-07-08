"""Tests for the Drive Discovery skill."""

from domain.skills.drive_discovery import get_available_drives


class TestGetAvailableDrives:
    def test_returns_list(self):
        result = get_available_drives()
        assert isinstance(result, list)

    def test_entries_have_required_keys(self):
        result = get_available_drives()
        for drive in result:
            assert "name" in drive
            assert "path" in drive
            assert "label" in drive

    def test_paths_are_strings(self):
        result = get_available_drives()
        for drive in result:
            assert isinstance(drive["path"], str)
            assert isinstance(drive["name"], str)
