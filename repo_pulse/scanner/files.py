from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Set, Union


DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "dist",
        "build",
        "site-packages",
        "coverage",
        ".idea",
        ".vscode",
    }
)
SECRET_FILE_NAMES = frozenset(
    {".env", ".env.local", ".env.production", "id_rsa", "id_dsa", "credentials"}
)
GENERATED_NAME_PARTS = ("-lock.", ".min.", ".map")


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    line_count: int
    extension: str
    is_test: bool
    todo_count: int
    fixme_count: int


def _is_excluded(path: Path, root: Path, excluded: Set[str]) -> bool:
    relative = path.relative_to(root)
    if any(part in excluded for part in relative.parts[:-1]):
        return True
    name = path.name.lower()
    return name in SECRET_FILE_NAMES or any(part in name for part in GENERATED_NAME_PARTS)


def _is_test_path(path: Path) -> bool:
    lowered = path.as_posix().lower()
    return (
        "test" in path.parts
        or "spec" in path.parts
        or path.name.lower().startswith(("test_", "test-"))
        or ".test." in lowered
        or ".spec." in lowered
    )


def iter_repository_files(
    repository: Union[str, Path], excluded_directories: Optional[Set[str]] = None
) -> Iterator[Path]:
    root = Path(repository).resolve()
    if not root.is_dir():
        raise FileNotFoundError("Repository directory does not exist: {}".format(root))
    excluded = set(DEFAULT_EXCLUDED_DIRECTORIES)
    if excluded_directories:
        excluded.update(excluded_directories)
    for path in sorted(root.rglob("*")):
        if path.is_file() and not _is_excluded(path, root, excluded):
            yield path


def scan_repository(repository: Union[str, Path]) -> list[FileRecord]:
    root = Path(repository).resolve()
    records = []
    for path in iter_repository_files(root):
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        records.append(
            FileRecord(
                path=path.relative_to(root).as_posix(),
                size=len(data),
                line_count=len(text.splitlines()),
                extension=path.suffix.lower(),
                is_test=_is_test_path(path.relative_to(root)),
                todo_count=sum(1 for line in text.splitlines() if "TODO" in line.upper()),
                fixme_count=sum(1 for line in text.splitlines() if "FIXME" in line.upper()),
            )
        )
    return records
