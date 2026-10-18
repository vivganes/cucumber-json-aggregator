"""Aggregate multiple Cucumber JSON reports into a single report."""

from __future__ import annotations

try:
    from ._version import __version__
except ImportError:  # pragma: no cover - only when running from an unbuilt checkout
    __version__ = "0.0.0"

__all__ = ["__version__"]
