"""Shared types and helpers for reasoning about Cucumber JSON structures."""

from __future__ import annotations

from enum import Enum
from typing import Any

JsonDict = dict[str, Any]
Unit = list[JsonDict]
"""A scenario together with the background element(s) that precede it."""


class Strategy(str, Enum):
    concat = "concat"
    merge = "merge"
    dedupe = "dedupe"


class DedupePolicy(str, Enum):
    last = "last"
    pass_ = "pass"
    worst = "worst"


# Higher is more severe.
SEVERITY: dict[str, int] = {
    "failed": 5,
    "undefined": 4,
    "pending": 3,
    "ambiguous": 2,
    "skipped": 1,
    "passed": 0,
}
_UNKNOWN_SEVERITY = 1  # unrecognised statuses rank like "skipped"


def severity(status: str) -> int:
    return SEVERITY.get(status, _UNKNOWN_SEVERITY)


def feature_key(feature: JsonDict) -> str | None:
    """Return ``uri`` -> ``id`` -> ``name``, or None when none is usable."""
    for field in ("uri", "id", "name"):
        value = feature.get(field)
        if value not in (None, ""):
            return str(value)
    return None


def split_units(elements: list[JsonDict]) -> list[Unit]:
    """Group elements so each background stays attached to the scenario after it."""
    units: list[Unit] = []
    pending: Unit = []
    for element in elements:
        if element.get("type") == "background":
            pending.append(element)
        else:
            units.append([*pending, element])
            pending = []
    if pending:
        units.append(pending)
    return units


def scenario_key(unit: Unit) -> tuple[str, str, str]:
    """``id`` + ``line``, falling back to ``name`` + ``line``."""
    target = unit[-1]
    line = str(target.get("line"))
    scenario_id = target.get("id")
    if scenario_id not in (None, ""):
        return ("id", str(scenario_id), line)
    return ("name", str(target.get("name")), line)


def is_scenario(unit: Unit) -> bool:
    return unit[-1].get("type") != "background"


def _result_status(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    result = item.get("result")
    if isinstance(result, dict):
        status = result.get("status")
        if isinstance(status, str):
            return status
    return None


def unit_status(unit: Unit) -> str:
    """Most severe status across before hooks, steps and after hooks.

    A unit without any result at all is reported as ``skipped``.
    """
    worst: str | None = None
    for element in unit:
        for section in ("before", "steps", "after"):
            items = element.get(section)
            if not isinstance(items, list):
                continue
            for item in items:
                status = _result_status(item)
                if status is not None and (worst is None or severity(status) > severity(worst)):
                    worst = status
    return worst if worst is not None else "skipped"
