from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Union


class GitError(RuntimeError):
    """Raised when Git evidence cannot be collected."""


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise GitError("Git command failed: {}".format(detail.strip())) from exc
    return result.stdout.strip()


def repository_is_git(repository: Union[str, Path]) -> bool:
    root = Path(repository).resolve()
    try:
        _git(root, "rev-parse", "--show-toplevel")
    except GitError:
        return False
    return True


def collect_git_evidence(repository: Union[str, Path]) -> dict:
    root = Path(repository).resolve()
    if not repository_is_git(root):
        return {"available": False, "commit_count": 0, "churn": 0, "hotspots": []}
    commit_count = int(_git(root, "rev-list", "--count", "HEAD") or 0)
    churn_lines = _git(root, "log", "--pretty=tformat:", "--numstat").splitlines()
    churn = 0
    for line in churn_lines:
        fields = line.split()
        if len(fields) >= 2 and fields[0].isdigit() and fields[1].isdigit():
            churn += int(fields[0]) + int(fields[1])
    names = _git(root, "log", "--pretty=tformat:", "--name-only").splitlines()
    counts = {}
    for name in names:
        if name.strip():
            counts[name] = counts.get(name, 0) + 1
    hotspots = [
        {"path": path, "commit_touch_count": count}
        for path, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {"available": True, "commit_count": commit_count, "churn": churn, "hotspots": hotspots}
