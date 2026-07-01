"""
Integrity Management Skill

Owned by: Integrity Agent
Purpose: Detect inconsistencies between filesystem state, indexed data,
         media metadata, and user progress records.
"""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueType(Enum):
    ORPHAN_RECORD = "orphan_record"
    MISSING_FILE = "missing_file"
    DUPLICATE_FILE = "duplicate_file"
    METADATA_MISMATCH = "metadata_mismatch"
    INVALID_PROGRESS = "invalid_progress"
    INVALID_PATH = "invalid_path"
    CORRUPTED_REFERENCE = "corrupted_reference"


@dataclass(frozen=True)
class IntegrityIssue:
    issue_type: IssueType
    severity: Severity
    message: str
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class IntegrityReport:
    issues: list[IntegrityIssue] = field(default_factory=list)
    total_checked: int = 0
    total_issues: int = 0

    @property
    def has_critical(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)


def validate_file_index(
    db_files: list[dict],
    filesystem_files: list[dict],
) -> IntegrityReport:
    """
    Compare database file records with actual filesystem content.

    db_files: list of dicts with keys: relative_path, file_size
    filesystem_files: list of dicts with keys: relative_path, size
    """
    issues: list[IntegrityIssue] = []
    db_map = {f["relative_path"]: f for f in db_files}
    fs_map = {f["relative_path"]: f for f in filesystem_files}

    db_paths = set(db_map.keys())
    fs_paths = set(fs_map.keys())

    for rp in db_paths - fs_paths:
        issues.append(
            IntegrityIssue(
                issue_type=IssueType.ORPHAN_RECORD,
                severity=Severity.WARNING,
                message=f"Database record exists but file is missing: {rp}",
                details={"relative_path": rp},
            )
        )

    for rp in fs_paths - db_paths:
        issues.append(
            IntegrityIssue(
                issue_type=IssueType.MISSING_FILE,
                severity=Severity.INFO,
                message=f"File exists on disk but not in database: {rp}",
                details={"relative_path": rp},
            )
        )

    for rp in db_paths & fs_paths:
        db_file = db_map[rp]
        fs_file = fs_map[rp]
        if db_file.get("file_size") is not None and fs_file.get("size") is not None:
            if db_file["file_size"] != fs_file["size"]:
                issues.append(
                    IntegrityIssue(
                        issue_type=IssueType.METADATA_MISMATCH,
                        severity=Severity.WARNING,
                        message=f"File size mismatch for: {rp}",
                        details={
                            "relative_path": rp,
                            "db_size": db_file["file_size"],
                            "fs_size": fs_file["size"],
                        },
                    )
                )

    return IntegrityReport(
        issues=issues,
        total_checked=len(db_paths | fs_paths),
        total_issues=len(issues),
    )


def detect_duplicates(
    items: list[dict],
    key_field: str = "relative_path",
) -> IntegrityReport:
    """
    Detect duplicate entries in a list of items.
    """
    issues: list[IntegrityIssue] = []
    seen: dict[str, list[int]] = {}

    for i, item in enumerate(items):
        key = item.get(key_field, "")
        if key in seen:
            seen[key].append(i)
        else:
            seen[key] = [i]

    for key, indices in seen.items():
        if len(indices) > 1:
            issues.append(
                IntegrityIssue(
                    issue_type=IssueType.DUPLICATE_FILE,
                    severity=Severity.ERROR,
                    message=f"Duplicate {key_field}: {key} (found {len(indices)} times)",
                    details={
                        key_field: key,
                        "occurrences": len(indices),
                        "indices": indices,
                    },
                )
            )

    return IntegrityReport(
        issues=issues,
        total_checked=len(items),
        total_issues=len(issues),
    )
