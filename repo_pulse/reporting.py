from __future__ import annotations

import json
import textwrap


def to_json(analysis: object) -> str:
    return json.dumps(analysis.to_dict(), indent=2, sort_keys=True)


def _ascii(value: object) -> str:
    return str(value).encode("ascii", "replace").decode("ascii")


def _box(title: str, body: list[str], width: int = 78) -> list[str]:
    inner_width = width - 4
    result = ["+{}+".format("-" * (width - 2)), "| {} |".format(_ascii(title).ljust(inner_width))]
    result.append("+{}+".format("-" * (width - 2)))
    for line in body or ["(none)"]:
        wrapped = textwrap.wrap(_ascii(line), width=inner_width) or [""]
        result.extend("| {} |".format(part.ljust(inner_width)) for part in wrapped)
    result.append("+{}+".format("-" * (width - 2)))
    return result


def _metric_rows(data: dict) -> list[str]:
    rows = [
        ("Files", len(data["files"])),
        ("Source files", data["source_files"]),
        ("Test-like files", data["test_files"]),
        ("Lines", data["total_lines"]),
        ("TODO markers", data["todo_count"]),
        ("FIXME markers", data["fixme_count"]),
    ]
    label_width = max(len(label) for label, _ in rows)
    return ["  {:<{}} : {}".format(label, label_width, value) for label, value in rows]


def to_terminal(analysis: object, width: int = 78) -> str:
    """Render a compact ASCII report for terminals without color or Unicode."""
    data = analysis.to_dict()
    lines = ["RepoPulse - repository maintenance report", ""]
    lines.extend(_box("Repository", [data["repository"]], width))
    lines.append("")
    lines.extend(_box("Summary", _metric_rows(data), width))
    lines.append("")

    git = data["git"]
    if git["available"]:
        git_rows = [
            "  Git repository : yes",
            "  Commits        : {}".format(git["commit_count"]),
            "  Churn          : {} lines added + deleted".format(git["churn"]),
        ]
    else:
        git_rows = [
            "  Git repository : no evidence available",
            "  Commits        : unavailable",
            "  Churn          : unavailable",
        ]
    lines.extend(_box("Git status", git_rows, width))
    lines.append("")

    recommendations = [
        "[{}] {} - {}".format(item["priority"].upper(), item["recommendation"], item["evidence"])
        for item in data["recommendations"]
    ]
    lines.extend(_box("Recommendations", recommendations or ["No evidence-based recommendations triggered."], width))
    lines.append("")

    top_files = sorted(data["files"], key=lambda item: (-item["line_count"], item["path"]))[:10]
    file_rows = [
        "  {:>7} lines  {:>8} bytes  {}".format(item["line_count"], item["size"], item["path"])
        for item in top_files
    ]
    lines.extend(_box("Top files by line count (max 10)", file_rows or ["No readable files found."], width))
    return "\n".join(lines) + "\n"


def to_markdown(analysis: object) -> str:
    data = analysis.to_dict()
    lines = [
        "# RepoPulse analysis",
        "",
        "Repository: `{}`".format(data["repository"]),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        "| Files | {} |".format(len(data["files"])),
        "| Source files | {} |".format(data["source_files"]),
        "| Test-like files | {} |".format(data["test_files"]),
        "| Lines | {} |".format(data["total_lines"]),
        "| TODO markers | {} |".format(data["todo_count"]),
        "| FIXME markers | {} |".format(data["fixme_count"]),
        "| Git commits | {} |".format(data["git"]["commit_count"] if data["git"]["available"] else "unavailable"),
        "| Git churn (added + deleted) | {} |".format(data["git"]["churn"] if data["git"]["available"] else "unavailable"),
        "",
        "## Files",
        "",
        "| Path | Lines | Bytes | TODO | FIXME |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        "| {path} | {line_count} | {size} | {todo_count} | {fixme_count} |".format(**record)
        for record in data["files"]
    )
    lines.extend(["", "## Recommendations", ""])
    if data["recommendations"]:
        lines.extend("- **{priority}** {recommendation} ({evidence})".format(**item) for item in data["recommendations"])
    else:
        lines.append("No evidence-based recommendations triggered.")
    return "\n".join(lines) + "\n"
