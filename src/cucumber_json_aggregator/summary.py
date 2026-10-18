"""Run statistics and their stderr rendering."""

from __future__ import annotations

from dataclasses import dataclass

from .models import JsonDict, is_scenario, split_units, unit_status


@dataclass
class Summary:
    files_read: int = 0
    files_skipped: int = 0
    features: int = 0
    scenarios: int = 0
    passed: int = 0
    failed: int = 0
    other: int = 0
    duplicates_removed: int = 0


def summarize(
    features: list[JsonDict],
    files_read: int,
    files_skipped: int,
    duplicates_removed: int,
) -> Summary:
    summary = Summary(
        files_read=files_read,
        files_skipped=files_skipped,
        features=len(features),
        duplicates_removed=duplicates_removed,
    )
    for feature in features:
        for unit in split_units(feature.get("elements") or []):
            if not is_scenario(unit):
                continue
            summary.scenarios += 1
            status = unit_status(unit)
            if status == "passed":
                summary.passed += 1
            elif status == "failed":
                summary.failed += 1
            else:
                summary.other += 1
    return summary


def format_summary(s: Summary) -> str:
    scenarios = f"scenarios: {s.scenarios} (passed: {s.passed}, failed: {s.failed}"
    if s.other:
        scenarios += f", other: {s.other}"
    scenarios += ")"
    return "\n".join(
        [
            f"files: {s.files_read} read, {s.files_skipped} skipped",
            f"features: {s.features}",
            scenarios,
            f"duplicates removed: {s.duplicates_removed}",
        ]
    )
