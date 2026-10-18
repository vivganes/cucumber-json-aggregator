from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner, Result

from cucumber_json_aggregator.cli import app

FIXTURES = Path(__file__).parent / "fixtures"


class Cja:
    def __init__(self) -> None:
        self.runner = CliRunner()

    def run(self, *args: object) -> Result:
        return self.runner.invoke(app, [str(a) for a in args])

    def json(self, *args: object) -> list[dict[str, Any]]:
        result = self.run(*args)
        assert result.exit_code == 0, result.stderr
        data: list[dict[str, Any]] = json.loads(result.stdout_bytes)
        return data


@pytest.fixture
def cja() -> Cja:
    return Cja()


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES
