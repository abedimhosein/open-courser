"""Tests for the Integrity Management skill."""

from domain.skills.integrity_management import (
    validate_file_index,
    detect_duplicates,
    Severity,
    IssueType,
)


class TestValidateFileIndex:
    def test_no_issues_when_indexes_match(self):
        db_files = [{"relative_path": "a.mp4", "file_size": 100}]
        fs_files = [{"relative_path": "a.mp4", "size": 100}]

        report = validate_file_index(db_files, fs_files)
        assert report.total_issues == 0

    def test_detects_orphan_records(self):
        db_files = [{"relative_path": "a.mp4", "file_size": 100}]
        fs_files = []

        report = validate_file_index(db_files, fs_files)
        assert report.total_issues == 1
        assert report.issues[0].issue_type == IssueType.ORPHAN_RECORD

    def test_detects_missing_files(self):
        db_files: list = []
        fs_files = [{"relative_path": "a.mp4", "size": 100}]

        report = validate_file_index(db_files, fs_files)
        assert report.total_issues == 1
        assert report.issues[0].issue_type == IssueType.MISSING_FILE

    def test_detects_size_mismatch(self):
        db_files = [{"relative_path": "a.mp4", "file_size": 100}]
        fs_files = [{"relative_path": "a.mp4", "size": 200}]

        report = validate_file_index(db_files, fs_files)
        assert report.total_issues >= 1
        assert any(i.issue_type == IssueType.METADATA_MISMATCH for i in report.issues)


class TestDetectDuplicates:
    def test_no_duplicates(self):
        items = [
            {"relative_path": "a.mp4"},
            {"relative_path": "b.mp4"},
        ]
        report = detect_duplicates(items)
        assert report.total_issues == 0

    def test_detects_duplicates(self):
        items = [
            {"relative_path": "a.mp4"},
            {"relative_path": "a.mp4"},
        ]
        report = detect_duplicates(items)
        assert report.total_issues == 1
        assert report.issues[0].issue_type == IssueType.DUPLICATE_FILE
