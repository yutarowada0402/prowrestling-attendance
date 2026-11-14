import shutil
from pathlib import Path

import pytest


@pytest.fixture
def root(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    for directory in ("dbt", "config", "data/seeds", "data/overrides"):
        shutil.copytree(
            repo / directory, tmp_path / directory, ignore=shutil.ignore_patterns("target", "logs")
        )
    return tmp_path


@pytest.fixture
def html():
    return (Path(__file__).parent / "fixtures/synthetic_event.html").read_text()
