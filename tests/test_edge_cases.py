from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import Cja


@pytest.mark.parametrize("name", ["empty", "whitespace", "empty_array"])
def test_empty_inputs_contribute_nothing(cja: Cja, fixtures: Path, name: str) -> None:
    result = cja.run(fixtures / f"edge/{name}.json", "--strict")
    assert result.exit_code == 0
    assert result.stderr.count("warning") == 0
    assert result.stdout.strip() == "[]"
    assert "files: 1 read, 0 skipped" in result.stderr


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("invalid", "invalid JSON"),
        ("latin1", "not valid UTF-8"),
        ("object_root", "root is dict"),
    ],
)
def test_bad_files_are_skipped_with_warning(
    cja: Cja, fixtures: Path, name: str, message: str
) -> None:
    good = fixtures / "jvm/run1.json"
    result = cja.run(fixtures / f"edge/{name}.json", good)
    assert result.exit_code == 0
    assert message in result.stderr
    assert "files: 1 read, 1 skipped" in result.stderr
    assert result.stdout.count("features/login.feature") == 1


@pytest.mark.parametrize("name", ["invalid", "latin1", "object_root", "non_features"])
def test_strict_turns_warning_into_failure(cja: Cja, fixtures: Path, name: str) -> None:
    result = cja.run(fixtures / f"edge/{name}.json", "--strict")
    assert result.exit_code == 1
    assert result.stdout == ""


def test_bom_is_handled(cja: Cja, fixtures: Path) -> None:
    result = cja.run(fixtures / "edge/bom.json", "--strict")
    assert result.exit_code == 0
    assert cja.json(fixtures / "edge/bom.json") == cja.json(fixtures / "jvm/run1.json")


def test_non_feature_items_are_skipped(cja: Cja, fixtures: Path) -> None:
    result = cja.run(fixtures / "edge/non_features.json")
    assert result.exit_code == 0
    assert result.stderr.count("is not a Cucumber feature") == 3
    assert "features: 1" in result.stderr
    assert "files: 1 read, 0 skipped" in result.stderr


def test_sparse_scenarios(cja: Cja, fixtures: Path) -> None:
    result = cja.run(fixtures / "edge/sparse_scenarios.json", "--strict")
    assert result.exit_code == 0
    # hooks-only (failed hook) -> failed; no result -> other; no duration -> passed
    assert "scenarios: 3 (passed: 1, failed: 1, other: 1)" in result.stderr


def test_non_ascii_output_is_utf8(cja: Cja, tmp_path: Path) -> None:
    src = tmp_path / "in.json"
    src.write_text('[{"keyword":"Feature","name":"Café ☕","elements":[]}]', encoding="utf-8")
    result = cja.run(src, "--quiet")
    assert "Café ☕" in result.stdout_bytes.decode("utf-8")


def test_large_embedding(cja: Cja, tmp_path: Path) -> None:
    blob = "A" * (5 * 1024 * 1024)
    src = tmp_path / "big.json"
    src.write_text(
        '[{"uri":"u","keyword":"Feature","elements":[{"id":"s","line":1,"type":"scenario",'
        f'"steps":[{{"embeddings":[{{"mime_type":"image/png","data":"{blob}"}}],'
        '"result":{"status":"passed"}}]}]}]',
        encoding="utf-8",
    )
    data = cja.json(src, "--compact", "--quiet")
    assert data[0]["elements"][0]["steps"][0]["embeddings"][0]["data"] == blob
