import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest

pytest.importorskip("flask")
pytest.importorskip("sqlalchemy")

import app  # type: ignore
from routes.api import ADMIN_TOKEN


def test_add_puzzle_requires_token():
    client = app.app.test_client()
    resp = client.post("/api/puzzles", json={"start_title": "A", "goal_title": "B"})
    assert resp.status_code == 401


def test_add_puzzle_success():
    client = app.app.test_client()
    resp = client.post(
        "/api/puzzles",
        json={"start_title": "A", "goal_title": "B"},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 201
    assert "puzzle_id" in resp.get_json()
