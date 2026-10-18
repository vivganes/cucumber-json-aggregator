# cucumber-json-aggregator — Specification

Aggregate multiple Cucumber JSON reports into a single report.

## Package

- **PyPI name / CLI:** `cucumber-json-aggregator` (alias `cja`)
- **Interface:** CLI only
- **Python:** 3.10+
- **Build/tooling:** uv
- **Runtime deps:** Typer
- **Versioning:** from git tag via `hatch-vcs` (tag `v1.2.0` → version `1.2.0`)
- **License:** MIT
- **Supported flavors:** Cucumber-JVM (Java), cucumber-js

## CLI

```
cja [INPUTS]... [-o OUT] [--strategy concat|merge|dedupe] [--dedupe-policy last|pass|worst]
    [--indent N | --compact] [--strict] [--quiet]
```

### Inputs

- Accepts any mix of:
  - explicit file paths
  - glob patterns (e.g. `'reports/**/*.json'`), expanded internally so behavior is the same across platforms including Windows
  - directories, scanned recursively for `*.json`
- Files are processed in argument order. Matches from a glob or directory are sorted for determinism.
- A file matched more than once (e.g. by a glob and an explicit path) is read only once.

### Output

- `-o OUT` writes to a file; without it, output goes to stdout.
- `--indent N` sets indentation (default `2`); `--compact` writes minified JSON.
- A summary is written to stderr: files read/skipped, features, scenarios, passed/failed, duplicates removed. `--quiet` suppresses it.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Error in `--strict` mode |
| 2 | Usage error / no input files matched |

### Bad input handling

- Default: warn on stderr and skip the bad file.
- `--strict`: any warning becomes a failure (exit 1).

## Merge strategies

| Strategy | Behavior |
|---|---|
| `concat` | Concatenate the top-level arrays as-is |
| **`merge`** (default) | Group features by key and append all `elements`, keeping duplicates |
| `dedupe` | Like `merge`, but collapse duplicate scenarios according to `--dedupe-policy` |

### Feature key

`uri` → fallback `id` → fallback `name`.

When features merge, feature-level `description` and other fields come from the first occurrence, and `tags` are unioned.

### Scenario key

`id` + `line` → fallback `name` + `line`.

Background elements (`type: "background"`) stay attached to the scenario that follows them, so they are deduped as a pair.

### Dedupe policy (`--dedupe-policy`)

| Policy | Winner |
|---|---|
| `last` (default) | The copy from the later file |
| `pass` | A passing copy, if one exists |
| `worst` | The most severe status: failed > undefined > pending > ambiguous > skipped > passed |

A scenario's status is derived from its before hooks, steps, and after hooks.

### Ordering

Features and scenarios appear in output in the order they were first seen.

### Data preservation

All fields are kept verbatim, including unknown or extra ones: `before`/`after` hooks, `embeddings`, `output`, `doc_string`, `rows`, `match`, etc.

## Edge cases (must be handled and tested)

- A 0-byte file, a whitespace-only file, or `[]` is valid and contributes nothing
- Invalid JSON → warn and skip
- A UTF-8 BOM is handled transparently
- Non-UTF-8 encoding → warn and skip
- A root that is an object instead of an array → warn and skip
- Array items that are not features (missing `elements`/`keyword`) → warn and skip
- A feature with no `elements` or with `elements: null`
- A missing `uri`/`id` → fallback key is used
- Scenario Outlines: each example row has a unique `id`/`line`
- Scenarios that have only hooks, a missing `result`, or a missing `duration`
- Durations (nanoseconds in both JVM and JS) are passed through untouched
- Large files with base64 embeddings are handled without streaming (fine below about 1 GB)
- An input path that equals the output path → refuse
- A file matched by both a glob and an explicit path → read once
- A glob that matches nothing → warn (error under `--strict`)

## Project layout

```
src/cucumber_json_aggregator/
    __init__.py
    cli.py
    loader.py
    merge.py
    models.py
    summary.py
tests/
    fixtures/{jvm,js,edge}/*.json
    test_*.py
.github/workflows/
    ci.yml
    publish.yml
pyproject.toml
README.md
LICENSE
.gitignore
```

## Quality & CI

- **Tests:** pytest with JVM, JS, and edge-case fixtures
- **Lint/format:** ruff
- **Types:** mypy (strict)
- **CI (`ci.yml`):** ruff, mypy, and pytest on Python 3.10 (the minimum supported version) on Linux
- **Publish (`publish.yml`):** manually triggered (`workflow_dispatch`) with a `version` input from `main`: runs the checks, creates tag `v<version>`, `uv build`, then PyPI trusted publishing (OIDC) using a `pypi` environment that must be configured on both PyPI and GitHub; the tag is pushed only after publishing succeeds

## Open points (current defaults)

1. Unwrap `{"features": [...]}` object roots? — **No**, warn and skip.
2. When features merge, take tags from the first occurrence or union them? — **Union**.
3. Add a `--fail-on-failed` CI-gate flag? — **Not for now**.
