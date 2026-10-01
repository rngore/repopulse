import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from repo_pulse.analyzer import analyze_repository
from repo_pulse.cli import main
from repo_pulse.reporting import to_terminal
from repo_pulse.scanner.files import scan_repository
from repo_pulse.sources import RemoteRepositoryError, analyze_source, is_https_git_url


def test_scan_excludes_generated_secrets_and_binaries(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "src" / "app.py").write_text("# TODO\nprint('x')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=secret", encoding="utf-8")
    (tmp_path / "node_modules" / "ignored.js").write_text("x", encoding="utf-8")
    (tmp_path / "image.bin").write_bytes(b"\xff\x00")

    records = scan_repository(tmp_path)
    assert [record.path for record in records] == ["src/app.py"]
    assert records[0].todo_count == 1


def test_analysis_has_git_evidence_and_recommendations(tmp_path):
    (tmp_path / "test_app.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("# FIXME\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "initial"], check=True)

    analysis = analyze_repository(tmp_path)
    assert analysis.git["available"] is True
    assert analysis.git["commit_count"] == 1
    assert analysis.test_files == 1
    assert analysis.fixme_count == 1


def test_cli_json_output(tmp_path, capsys):
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    assert main(["analyze", str(tmp_path), "--format", "json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["total_lines"] == 1


def test_cli_analyze_defaults_to_ascii_terminal_report(tmp_path, capsys):
    (tmp_path / "large.py").write_text("# TODO\n" + "print('x')\n" * 600, encoding="utf-8")
    assert main(["analyze", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "RepoPulse - repository maintenance report" in output
    assert "+----------------------------------------------------------------------------+" in output
    assert "Summary" in output
    assert "Git status" in output
    assert "Recommendations" in output
    assert "Top files by line count" in output
    assert all(ord(character) < 128 for character in output)
    assert '"total_lines"' not in output


def test_terminal_report_handles_empty_repository(tmp_path):
    report = to_terminal(analyze_repository(tmp_path))
    assert "No readable files found." in report
    assert "No evidence-based recommendations triggered." in report
    assert "Git repository : no evidence available" in report


def test_https_git_url_validation():
    assert is_https_git_url("https://github.com/example/project.git")
    assert not is_https_git_url("http://github.com/example/project.git")
    assert not is_https_git_url("example/project")
    assert not is_https_git_url("https://user:token@github.com/example/project.git")


def test_remote_analysis_clones_and_reports_source(tmp_path):
    remote_url = "https://github.com/example/project.git"
    captured = {"clone_command": None}

    def fake_run(command, **kwargs):
        captured["command"] = command
        if command[:2] == ["git", "clone"]:
            captured["clone_command"] = command
            destination = Path(command[-1])
            destination.mkdir()
            (destination / "main.py").write_text("print('remote')\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with patch("repo_pulse.sources.tempfile.TemporaryDirectory") as temporary:
        temporary.return_value.__enter__.return_value = str(tmp_path)
        temporary.return_value.__exit__.return_value = False
        with patch("repo_pulse.sources.subprocess.run", side_effect=fake_run):
            analysis = analyze_source(remote_url)

    assert analysis.repository == remote_url
    assert analysis.total_lines == 1
    assert captured["clone_command"][:5] == ["git", "clone", "--quiet", "--depth", "1"]


def test_remote_clone_failure_is_explicit():
    failure = subprocess.CalledProcessError(128, ["git", "clone"], stderr="repository not found")
    with patch("repo_pulse.sources.subprocess.run", side_effect=failure):
        try:
            analyze_source("https://github.com/example/missing.git")
        except RemoteRepositoryError as exc:
            assert "unable to clone remote repository" in str(exc)
            assert "repository not found" in str(exc)
        else:
            raise AssertionError("expected RemoteRepositoryError")
