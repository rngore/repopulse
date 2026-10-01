# RepoPulse

RepoPulse is a local, evidence-first repository maintenance CLI. It scans a
repository without changing it and turns observable source-tree and Git
history facts into a compact maintenance report.

The core analyzer is deterministic and built with Python's standard library.
It does not require LM Studio, a language model, network access for local
analysis,
or any claim that the software was trained locally or by AI. Optional AI
assistance could be added around the reports later, but it is not part of the
core product.

## Features

- File inventory, byte counts, and line counts
- TODO and FIXME marker counts
- Test-file heuristics and a simple test-coverage signal
- Git commit counts, added-plus-deleted churn, and frequently touched files
- Evidence-based, prioritized maintenance recommendations
- Readable ASCII terminal output, stable JSON, and Markdown reports
- Local repository paths and public HTTPS Git URLs, including GitHub URLs
- Explicit errors for missing paths, unavailable Git, invalid remote inputs,
  and clone/network failures
- Exclusion of Git metadata, dependency/build/cache directories, common secret
  filenames, generated-looking files, binary files, and invalid UTF-8 files

## Requirements

- Python 3.9 or newer
- Git on `PATH` when analyzing a Git repository or an HTTPS Git URL
- Network access only when cloning a remote repository

## Installation

For a checkout or editable development install:

```console
python -m pip install -e .
```

To install the test extra as well:

```console
python -m pip install -e ".[test]"
```

You can also run directly from a checkout with
`python -m repo_pulse.cli ...`.

## Usage

### Analyze a local repository

The default is a human-readable ASCII report:

```console
repo-pulse analyze /path/to/repository
```

The report contains repository identity, summary metrics, Git status,
recommendations, and the largest readable files.

### Analyze a public HTTPS Git URL

Remote sources are cloned shallowly into a temporary directory, analyzed, and
cleaned up:

```console
repo-pulse analyze https://github.com/OWNER/REPOSITORY.git
```

Only HTTPS URLs without embedded credentials, query strings, or fragments are
accepted. GitHub `OWNER/REPOSITORY` shorthand is intentionally not accepted;
use the complete HTTPS URL so RepoPulse never guesses whether a string should
trigger a network request. The remote repository is never pushed to or
otherwise modified.

### Choose an output format

JSON is intended for scripts and integrations:

```console
repo-pulse analyze /path/to/repository --format json
repo-pulse analyze https://github.com/OWNER/REPOSITORY.git \
  --format json --output report.json
```

Markdown is suitable for issue descriptions and saved documents:

```console
repo-pulse analyze /path/to/repository --format markdown --output report.md
```

`--format json` and `--format markdown` preserve the structured and document
report formats; omitting `--format` selects the ASCII terminal report.

### Scan files only

`scan` is local-only and emits the file inventory without Git history:

```console
repo-pulse scan /path/to/repository --format json --output files.json
repo-pulse scan /path/to/repository --format markdown
```

### Check prerequisites

`doctor` checks a local target directory and reports whether it is a Git
repository:

```console
repo-pulse doctor /path/to/repository
```

## Read-only and privacy behavior

RepoPulse reads files and invokes read-only Git commands such as `git log` and
`git rev-list`. It does not edit, stage, commit, push, or delete anything in a
local target. For an HTTPS source, Git writes only to an automatically managed
temporary clone; that directory is removed when analysis finishes, including
after clone or analysis errors.

No credentials are accepted in remote URLs. Reports contain paths and measured
repository metadata, so review output before sharing it. Repository contents
are not sent to a model or third-party service by RepoPulse.

## Limitations

- Git history is reported as unavailable when the local target is not a Git
  repository.
- Remote analysis requires the `git` executable and network access; private
  repositories and authentication flows are not supported.
- Test detection is a filename/path heuristic, not a test runner or coverage
  measurement. RepoPulse does not execute the repository's code or tests.
- Binary and invalid UTF-8 files are skipped. Common generated, dependency,
  cache, and secret paths are excluded conservatively.
- GitHub shorthand such as `OWNER/REPOSITORY` is not supported.

## Architecture

The implementation is intentionally small and layered:

- `repo_pulse/sources.py` validates sources, owns temporary remote clones, and
  delegates to the analyzer.
- `repo_pulse/scanner/files.py` performs the read-only file inventory and
  marker/test heuristics.
- `repo_pulse/git.py` collects Git evidence through fixed subprocess argument
  lists.
- `repo_pulse/analyzer.py` combines evidence and creates recommendations.
- `repo_pulse/reporting.py` renders terminal, JSON, and Markdown output.
- `repo_pulse/cli.py` provides the `analyze`, `scan`, and `doctor` commands.

## Development and testing

```console
python -m pip install -e ".[test]"
pytest
python -m compileall -q repo_pulse tests
```

Tests mock remote clone boundaries and use temporary repositories for local Git
behavior. No remote repository is required for the test suite.

## License

RepoPulse is released under the MIT License. See [LICENSE](LICENSE).
