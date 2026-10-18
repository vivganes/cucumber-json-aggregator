"""Resolve input arguments to files and parse them into Cucumber features."""

from __future__ import annotations

import glob
import json
from dataclasses import dataclass, field
from pathlib import Path

from .models import JsonDict


@dataclass
class LoadedFile:
    path: Path
    features: list[JsonDict]


@dataclass
class LoadResult:
    files: list[LoadedFile] = field(default_factory=list)
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def expand_inputs(inputs: list[str]) -> tuple[list[Path], list[str]]:
    """Expand files, globs and directories; de-duplicate by resolved path."""
    paths: list[Path] = []
    seen: set[Path] = set()
    warnings: list[str] = []

    def add(candidates: list[Path]) -> None:
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                paths.append(candidate)

    for arg in inputs:
        path = Path(arg)
        if path.is_file():
            add([path])
        elif path.is_dir():
            found = sorted((p for p in path.rglob("*.json") if p.is_file()), key=str)
            if not found:
                warnings.append(f"directory '{arg}' contains no *.json files")
            add(found)
        elif glob.has_magic(arg):
            matches = sorted((Path(m) for m in glob.glob(arg, recursive=True)), key=str)
            files = [m for m in matches if m.is_file()]
            if not files:
                warnings.append(f"pattern '{arg}' matched no files")
            add(files)
        else:
            warnings.append(f"input '{arg}' does not exist")
    return paths, warnings


def _is_feature(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    if "elements" not in item and "keyword" not in item:
        return False
    elements = item.get("elements")
    return elements is None or (
        isinstance(elements, list) and all(isinstance(e, dict) for e in elements)
    )


def load_file(path: Path) -> tuple[list[JsonDict] | None, list[str]]:
    """Parse one report. Returns ``(None, warnings)`` if the file must be skipped."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, [f"{path}: cannot read file ({exc.strerror or exc}); skipped"]
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, [f"{path}: not valid UTF-8; skipped"]
    if not text.strip():
        return [], []
    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as exc:
        return None, [f"{path}: invalid JSON ({exc}); skipped"]
    if not isinstance(data, list):
        return None, [f"{path}: root is {type(data).__name__}, expected an array; skipped"]

    features: list[JsonDict] = []
    warnings: list[str] = []
    for index, item in enumerate(data):
        if _is_feature(item):
            features.append(item)
        else:
            warnings.append(f"{path}: item {index} is not a Cucumber feature; skipped")
    return features, warnings


def load_files(paths: list[Path]) -> LoadResult:
    result = LoadResult()
    for path in paths:
        features, warnings = load_file(path)
        result.warnings.extend(warnings)
        if features is None:
            result.skipped += 1
        else:
            result.files.append(LoadedFile(path, features))
    return result
