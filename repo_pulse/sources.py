from __future__ import annotations

import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from .analyzer import RepositoryAnalysis, analyze_repository


class RemoteRepositoryError(RuntimeError):
    """Raised when a remote repository cannot be cloned safely."""


def is_https_git_url(source: str) -> bool:
    parsed = urlparse(source)
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
    )


@contextmanager
def clone_remote_repository(source: str) -> Iterator[Path]:
    if not is_https_git_url(source):
        raise RemoteRepositoryError(
            "remote repositories must use an HTTPS Git URL without credentials or query parameters"
        )
    with tempfile.TemporaryDirectory(prefix="repo-pulse-") as temporary_directory:
        destination = Path(temporary_directory) / "repository"
        try:
            subprocess.run(
                ["git", "clone", "--quiet", "--depth", "1", source, str(destination)],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RemoteRepositoryError("Git is required to clone remote repositories") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or "").strip()
            message = "unable to clone remote repository {}".format(source)
            if detail:
                message += ": {}".format(detail)
            raise RemoteRepositoryError(message) from exc
        yield destination


def analyze_source(source: str) -> RepositoryAnalysis:
    """Analyze a local path or an HTTPS Git URL, cleaning remote checkouts up."""
    if is_https_git_url(source):
        with clone_remote_repository(source) as repository:
            analysis = analyze_repository(repository)
        return RepositoryAnalysis(
            repository=source,
            files=analysis.files,
            total_lines=analysis.total_lines,
            todo_count=analysis.todo_count,
            fixme_count=analysis.fixme_count,
            test_files=analysis.test_files,
            source_files=analysis.source_files,
            git=analysis.git,
            recommendations=analysis.recommendations,
        )
    return analyze_repository(source)
