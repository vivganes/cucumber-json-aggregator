"""Merge strategies for combining features from several reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import (
    DedupePolicy,
    JsonDict,
    Strategy,
    Unit,
    feature_key,
    scenario_key,
    severity,
    split_units,
    unit_status,
)


@dataclass
class MergeResult:
    features: list[JsonDict]
    duplicates_removed: int = 0


@dataclass
class _Group:
    base: JsonDict
    units: list[Unit] = field(default_factory=list)
    index: dict[tuple[str, str, str], int] = field(default_factory=dict)
    tags: list[Any] | None = None
    tag_keys: set[str] = field(default_factory=set)


def _tag_id(tag: Any) -> str:
    if isinstance(tag, dict) and "name" in tag:
        return str(tag["name"])
    return repr(tag)


def _union_tags(group: _Group, tags: Any) -> None:
    if not isinstance(tags, list):
        return
    if group.tags is None:
        group.tags = []
    for tag in tags:
        tid = _tag_id(tag)
        if tid not in group.tag_keys:
            group.tag_keys.add(tid)
            group.tags.append(tag)


def _replaces(old: Unit, new: Unit, policy: DedupePolicy) -> bool:
    if policy is DedupePolicy.last:
        return True
    new_status, old_status = unit_status(new), unit_status(old)
    if policy is DedupePolicy.pass_:
        return new_status == "passed" or old_status != "passed"
    return severity(new_status) >= severity(old_status)


def _build(group: _Group) -> JsonDict:
    feature = dict(group.base)
    if group.units or isinstance(feature.get("elements"), list):
        feature["elements"] = [element for unit in group.units for element in unit]
    if group.tags is not None:
        feature["tags"] = group.tags
    return feature


def aggregate(
    reports: list[list[JsonDict]],
    strategy: Strategy,
    policy: DedupePolicy = DedupePolicy.last,
) -> MergeResult:
    """Combine features from ``reports`` (given in file order)."""
    if strategy is Strategy.concat:
        return MergeResult([feature for report in reports for feature in report])

    dedupe = strategy is Strategy.dedupe
    groups: dict[object, _Group] = {}
    duplicates = 0
    for report in reports:
        for feature in report:
            key = feature_key(feature)
            # Features without any usable key are never merged with each other.
            group_key: object = key if key is not None else object()
            group = groups.get(group_key)
            if group is None:
                group = groups[group_key] = _Group(base=feature)
            _union_tags(group, feature.get("tags"))
            elements = feature.get("elements") or []
            for unit in split_units(elements):
                if not dedupe:
                    group.units.append(unit)
                    continue
                ukey = scenario_key(unit)
                existing = group.index.get(ukey)
                if existing is None:
                    group.index[ukey] = len(group.units)
                    group.units.append(unit)
                else:
                    duplicates += 1
                    if _replaces(group.units[existing], unit, policy):
                        group.units[existing] = unit
    return MergeResult([_build(g) for g in groups.values()], duplicates)
