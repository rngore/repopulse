from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Union

from .git import collect_git_evidence
from .scanner.files import FileRecord, scan_repository


@dataclass(frozen=True)
class RepositoryAnalysis:
    repository: str
    files: List[FileRecord]
    total_lines: int
    todo_count: int
    fixme_count: int
    test_files: int
    source_files: int
    git: dict
    recommendations: List[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def _recommendations(records: List[FileRecord], git: dict) -> List[dict]:
    recommendations = []
    total_markers = sum(record.todo_count + record.fixme_count for record in records)
    if total_markers:
        recommendations.append(
            {"priority": "high", "area": "debt", "evidence": "{} TODO/FIXME markers".format(total_markers),
             "recommendation": "Triage markers and convert actionable items into tracked work."}
        )
    largest = max(records, key=lambda record: record.line_count, default=None)
    if largest and largest.line_count >= 500:
        recommendations.append(
            {"priority": "medium", "area": "structure", "evidence": "{} has {} lines".format(largest.path, largest.line_count),
             "recommendation": "Consider splitting the largest file into cohesive modules."}
        )
    if records and not any(record.is_test for record in records):
        recommendations.append(
            {"priority": "high", "area": "testing", "evidence": "No test-like files detected",
             "recommendation": "Add automated tests around critical behavior."}
        )
    if git.get("available") and git.get("commit_count", 0) >= 50:
        recommendations.append(
            {"priority": "medium", "area": "maintenance", "evidence": "{} commits in history".format(git["commit_count"]),
             "recommendation": "Review frequently changed areas for ownership and regression coverage."}
        )
    return recommendations


def analyze_repository(repository: Union[str, Path]) -> RepositoryAnalysis:
    root = Path(repository).resolve()
    records = scan_repository(root)
    git = collect_git_evidence(root)
    return RepositoryAnalysis(
        repository=str(root),
        files=records,
        total_lines=sum(record.line_count for record in records),
        todo_count=sum(record.todo_count for record in records),
        fixme_count=sum(record.fixme_count for record in records),
        test_files=sum(1 for record in records if record.is_test),
        source_files=sum(1 for record in records if not record.is_test),
        git=git,
        recommendations=_recommendations(records, git),
    )
