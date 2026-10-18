# cucumber-json-aggregator

Aggregate multiple Cucumber JSON reports (Cucumber-JVM and cucumber-js) into a single report.

```
pip install cucumber-json-aggregator     # installs `cucumber-json-aggregator` and `cja`
```

## Usage

```
cja [INPUTS]... [-o OUT] [--strategy concat|merge|dedupe] [--dedupe-policy last|pass|worst]
    [--indent N | --compact] [--strict] [--quiet]
```

```bash
cja reports/ -o combined.json
cja 'reports/**/*.json' extra.json --strategy dedupe --dedupe-policy worst -o combined.json
```

**Inputs** may be files, glob patterns (expanded internally, so quote them and they work the same on
Windows) and directories (scanned recursively for `*.json`). Files are processed in argument order;
glob/directory matches are sorted. A file matched more than once is read once.

**Output** goes to stdout, or to `-o OUT`. Indentation defaults to 2; `--compact` minifies.
A summary (files, features, scenarios, passed/failed, duplicates removed) is written to stderr;
`--quiet` hides it.

### Strategies

| Strategy | Behaviour |
|---|---|
| `concat` | Concatenate the top-level arrays as-is |
| `merge` (default) | Group features by key (`uri` → `id` → `name`) and append all `elements`, keeping duplicates. Other feature fields come from the first occurrence; `tags` are unioned |
| `dedupe` | Like `merge`, but collapse duplicate scenarios (key: `id`+`line`, else `name`+`line`). A background stays attached to its scenario |

`--dedupe-policy` picks the winner among duplicates: `last` (default; later file), `pass` (a passing
copy if any, else the latest), `worst` (failed > undefined > pending > ambiguous > skipped > passed;
ties go to the later copy). A scenario's status comes from its before hooks, steps and after hooks.

Features and scenarios keep first-seen order, and all fields (hooks, embeddings, durations, unknown
keys…) are passed through verbatim.

### Bad input

Empty, whitespace-only and `[]` files are valid and contribute nothing. Invalid JSON, non-UTF-8 files,
non-array roots and array items that aren't features produce a warning and are skipped. A UTF-8 BOM
is accepted. A glob/directory that matches nothing warns. With `--strict` any warning is a failure and
nothing is written.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Error in `--strict` mode (or the output could not be written) |
| 2 | Usage error, no input files matched, or an input is also the output path |

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

The version comes from the git tag via `hatch-vcs` (`v1.2.0` → `1.2.0`); untagged checkouts report
`0.0.0`. Pushing a `v*` tag builds and publishes to PyPI through trusted publishing, which needs a
`pypi` environment configured on both PyPI and GitHub.

MIT licensed.
