from __future__ import annotations

import json
from pathlib import Path

from .conftest import Cja


def test_basic_summary_on_stderr(cja: Cja, fixtures: Path) -> None:
    result = cja.run(fixtures / "jvm/run1.json", fixtures / "jvm/run2.json", "--strategy", "dedupe")
    assert result.exit_code == 0
    assert "files: 2 read, 0 skipped" in result.stderr
    assert "features: 2" in result.stderr
    assert "scenarios: 4 (passed: 3, failed: 0, other: 1)" in result.stderr
    assert "duplicates removed: 2" in result.stderr


def test_quiet_suppresses_summary(cja: Cja, fixtures: Path) -> None:
    result = cja.run(fixtures / "jvm/run1.json", "--quiet")
    assert result.exit_code == 0
    assert result.stderr == ""


def test_output_file(cja: Cja, fixtures: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    result = cja.run(fixtures / "jvm/run1.json", "-o", out, "--quiet")
    assert result.exit_code == 0
    assert result.stdout == ""
    assert json.loads(out.read_text(encoding="utf-8"))[0]["uri"] == "features/login.feature"


def test_indent_and_compact(cja: Cja, fixtures: Path) -> None:
    path = fixtures / "edge/outline.json"
    default = cja.run(path, "--quiet").stdout
    assert default.startswith('[\n  {\n    "uri"')
    assert cja.run(path, "--quiet", "--indent", "4").stdout.startswith('[\n    {\n        "uri"')
    compact = cja.run(path, "--quiet", "--compact").stdout
    assert "\n" not in compact.strip() and ", " not in compact
    assert cja.run(path, "--indent", "2", "--compact").exit_code == 2


def test_no_inputs_is_usage_error(cja: Cja) -> None:
    assert cja.run().exit_code == 2


def test_nothing_matched_exits_2(cja: Cja, tmp_path: Path) -> None:
    result = cja.run(tmp_path / "*.json")
    assert result.exit_code == 2
    assert "no input files matched" in result.stderr


def test_directory_is_scanned_recursively_and_sorted(cja: Cja, fixtures: Path) -> None:
    data = cja.json(fixtures / "jvm", "--strategy", "concat")
    assert [f["description"] for f in data] == ["run1", "run2", "cart"]


def test_glob_is_expanded_internally(cja: Cja, fixtures: Path) -> None:
    pattern = str(fixtures / "**" / "run*.json")
    data = cja.json(pattern, "--strategy", "concat")
    assert len(data) == 5  # jvm: 1 + 2, js: 1 + 1


def test_file_matched_twice_is_read_once(cja: Cja, fixtures: Path) -> None:
    run1 = fixtures / "jvm/run1.json"
    result = cja.run(
        run1, str(fixtures / "jvm" / "run1.*"), fixtures / "jvm", "--strategy", "dedupe"
    )
    assert result.exit_code == 0
    assert "files: 2 read" in result.stderr
    assert "duplicates removed: 2" in result.stderr  # only run1<->run2, not run1<->run1


def test_input_equal_to_output_is_refused(cja: Cja, tmp_path: Path, fixtures: Path) -> None:
    out = tmp_path / "out.json"
    out.write_text("[]")
    result = cja.run(out, "-o", out)
    assert result.exit_code == 2
    assert out.read_text() == "[]"
    # also when matched via a glob
    assert cja.run(tmp_path / "*.json", "-o", out).exit_code == 2


def test_unmatched_glob_warns_and_strict_fails(cja: Cja, fixtures: Path, tmp_path: Path) -> None:
    result = cja.run(fixtures / "jvm/run1.json", tmp_path / "nope-*.json", "--quiet")
    assert result.exit_code == 0
    assert "matched no files" in result.stderr
    strict = cja.run(fixtures / "jvm/run1.json", tmp_path / "nope-*.json", "--strict")
    assert strict.exit_code == 1
    assert strict.stdout == ""


def test_missing_file_warns(cja: Cja, fixtures: Path, tmp_path: Path) -> None:
    result = cja.run(fixtures / "jvm/run1.json", tmp_path / "missing.json")
    assert result.exit_code == 0
    assert "does not exist" in result.stderr


def test_version(cja: Cja) -> None:
    assert cja.run("--version").exit_code == 0
