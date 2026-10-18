from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cucumber_json_aggregator.merge import aggregate
from cucumber_json_aggregator.models import DedupePolicy, Strategy

from .conftest import Cja


def scenarios(features: list[dict[str, Any]], uri: str) -> dict[str, dict[str, Any]]:
    feature = next(f for f in features if f["uri"] == uri)
    return {e["id"]: e for e in feature["elements"] if e["type"] == "scenario"}


def test_concat_keeps_features_as_is(cja: Cja, fixtures: Path) -> None:
    data = cja.json(fixtures / "jvm/run1.json", fixtures / "jvm/run2.json", "--strategy", "concat")
    assert [f["uri"] for f in data] == [
        "features/login.feature",
        "features/login.feature",
        "features/cart.feature",
    ]


def test_merge_groups_features_and_keeps_duplicates(cja: Cja, fixtures: Path) -> None:
    data = cja.json(fixtures / "jvm/run1.json", fixtures / "jvm/run2.json")
    assert [f["uri"] for f in data] == ["features/login.feature", "features/cart.feature"]
    login = data[0]
    assert len(login["elements"]) == 10  # 2 + 3 scenarios, each with a background
    assert login["description"] == "run1"  # first occurrence wins
    assert [t["name"] for t in login["tags"]] == ["@auth", "@smoke"]  # union


def test_merge_is_the_default(cja: Cja, fixtures: Path) -> None:
    args = (fixtures / "js/run1.json", fixtures / "js/run2.json")
    assert cja.json(*args) == cja.json(*args, "--strategy", "merge")


def test_dedupe_last(cja: Cja, fixtures: Path) -> None:
    data = cja.json(fixtures / "jvm/run1.json", fixtures / "jvm/run2.json", "--strategy", "dedupe")
    login = scenarios(data, "features/login.feature")
    assert list(login) == ["login;valid-login", "login;invalid-login", "login;locked"]
    assert login["login;invalid-login"]["steps"][0]["result"]["status"] == "passed"
    # backgrounds stay attached: one per scenario
    assert [e["type"] for e in data[0]["elements"]] == ["background", "scenario"] * 3


def test_dedupe_worst_keeps_failure(cja: Cja, fixtures: Path) -> None:
    data = cja.json(
        fixtures / "jvm/run1.json",
        fixtures / "jvm/run2.json",
        "--strategy",
        "dedupe",
        "--dedupe-policy",
        "worst",
    )
    login = scenarios(data, "features/login.feature")
    assert login["login;invalid-login"]["steps"][0]["result"]["status"] == "failed"


def test_dedupe_pass_prefers_passing_copy(cja: Cja, fixtures: Path) -> None:
    # run2 first so the failing copy from run1 is the *later* one.
    data = cja.json(
        fixtures / "jvm/run2.json",
        fixtures / "jvm/run1.json",
        "--strategy",
        "dedupe",
        "--dedupe-policy",
        "pass",
    )
    login = scenarios(data, "features/login.feature")
    assert login["login;invalid-login"]["steps"][0]["result"]["status"] == "passed"


def test_dedupe_last_takes_later_file(cja: Cja, fixtures: Path) -> None:
    data = cja.json(fixtures / "jvm/run2.json", fixtures / "jvm/run1.json", "--strategy", "dedupe")
    login = scenarios(data, "features/login.feature")
    assert login["login;invalid-login"]["steps"][0]["result"]["status"] == "failed"


def test_worst_severity_order() -> None:
    def feature(status: str) -> list[dict[str, Any]]:
        step = {"result": {"status": status}}
        return [
            {
                "uri": "u",
                "keyword": "Feature",
                "elements": [{"id": "s", "line": 1, "type": "scenario", "steps": [step]}],
            }
        ]

    order = ["passed", "skipped", "ambiguous", "pending", "undefined", "failed"]
    for i, worse in enumerate(order):
        for better in order[:i]:
            for reports in ([feature(better), feature(worse)], [feature(worse), feature(better)]):
                out = aggregate(reports, Strategy.dedupe, DedupePolicy.worst)
                status = out.features[0]["elements"][0]["steps"][0]["result"]["status"]
                assert status == worse


def test_hook_failure_counts_towards_status() -> None:
    def feature(hook_status: str) -> list[dict[str, Any]]:
        return [
            {
                "uri": "u",
                "keyword": "Feature",
                "elements": [
                    {
                        "id": "s",
                        "line": 1,
                        "type": "scenario",
                        "before": [{"result": {"status": hook_status}}],
                        "steps": [{"result": {"status": "passed"}}],
                    }
                ],
            }
        ]

    out = aggregate([feature("failed"), feature("passed")], Strategy.dedupe, DedupePolicy.worst)
    assert out.features[0]["elements"][0]["before"][0]["result"]["status"] == "failed"
    assert out.duplicates_removed == 1


def test_scenario_key_falls_back_to_name_and_line() -> None:
    def feature(name: str, line: int) -> list[dict[str, Any]]:
        return [
            {
                "uri": "u",
                "keyword": "Feature",
                "elements": [{"name": name, "line": line, "type": "scenario"}],
            }
        ]

    out = aggregate(
        [feature("a", 1), feature("a", 1), feature("a", 2), feature("b", 1)], Strategy.dedupe
    )
    assert len(out.features[0]["elements"]) == 3
    assert out.duplicates_removed == 1


def test_scenarios_are_ordered_by_first_seen() -> None:
    def feature(*lines: int) -> list[dict[str, Any]]:
        return [
            {
                "uri": "u",
                "keyword": "Feature",
                "elements": [{"id": f"s{n}", "line": n, "type": "scenario"} for n in lines],
            }
        ]

    out = aggregate([feature(3, 1), feature(2, 3)], Strategy.dedupe)
    assert [e["line"] for e in out.features[0]["elements"]] == [3, 1, 2]


def test_unknown_fields_are_preserved(cja: Cja, fixtures: Path) -> None:
    data = cja.json(fixtures / "js/run1.json", fixtures / "js/run2.json", "--strategy", "dedupe")
    original = json.loads((fixtures / "js/run1.json").read_text())
    basic = scenarios(data, "features/search.feature")["search;basic-search"]
    # run2's copy won ("last") and has no embeddings; run1 with last-wins shows it too
    assert "embeddings" not in basic
    kept = cja.json(fixtures / "js/run1.json", "--strategy", "dedupe")
    assert kept == original


def test_durations_pass_through_untouched(cja: Cja, fixtures: Path) -> None:
    data = cja.json(fixtures / "edge/sparse_scenarios.json")
    steps = data[0]["elements"][2]["steps"]
    assert "duration" not in steps[0]["result"]
    data = cja.json(fixtures / "jvm/run1.json")
    assert data[0]["elements"][1]["steps"][0]["result"]["duration"] == 1000000


def test_feature_key_fallbacks(cja: Cja, fixtures: Path, tmp_path: Path) -> None:
    original = fixtures / "edge/missing_keys.json"
    copy = tmp_path / "copy.json"
    copy.write_bytes(original.read_bytes())
    data = cja.json(original, copy)
    # "nouri" (id) and "Only Name" (name) merge; keyless features never merge
    assert [f.get("name") for f in data] == ["No Uri", "Only Name", None, None]
    assert len(data[0]["elements"]) == 2


def test_features_without_elements(cja: Cja, fixtures: Path) -> None:
    data = cja.json(
        fixtures / "edge/no_elements.json",
        fixtures / "edge/null_elements.json",
        "--strategy",
        "dedupe",
    )
    assert [f["name"] for f in data] == ["None", "Null"]
    assert "elements" not in data[0]
    assert data[1]["elements"] is None


def test_scenario_outline_rows_are_not_collapsed(cja: Cja, fixtures: Path) -> None:
    path = fixtures / "edge/outline.json"
    data = cja.json(path, path, "--strategy", "dedupe")
    assert len(data[0]["elements"]) == 2
