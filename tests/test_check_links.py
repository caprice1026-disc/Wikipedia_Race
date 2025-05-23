import types
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest
app = pytest.importorskip("app")

def test_check_link_exists_pagination(monkeypatch):
    responses = [
        {
            "batchcomplete": "",
            "continue": {"plcontinue": "next", "continue": "-||"},
            "query": {"pages": {"1": {"links": [{"title": "Other"}]}}},
        },
        {
            "batchcomplete": "",
            "query": {"pages": {"1": {"links": [{"title": "TARGET"}]}}},
        },
    ]

    def fake_get(url, params=None, headers=None):
        resp = types.SimpleNamespace()
        resp.raise_for_status = lambda: None
        resp.json = lambda: responses.pop(0)
        return resp

    monkeypatch.setattr(app, "requests.get", fake_get)
    assert app.check_link_exists("SRC", "TARGET") is True
