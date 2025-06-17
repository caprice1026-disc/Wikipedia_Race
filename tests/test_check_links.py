import types
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# requests がインストールされていない環境用のダミーモジュール
if "requests" not in sys.modules:
    dummy = types.ModuleType("requests")
    dummy.get = lambda *a, **k: None
    sys.modules["requests"] = dummy

import pytest
wiki = pytest.importorskip("services.wiki")

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

    def fake_get(url, params=None, headers=None, **kw):
        resp = types.SimpleNamespace()
        resp.raise_for_status = lambda: None
        resp.json = lambda: responses.pop(0)
        return resp

    monkeypatch.setattr(wiki.requests, "get", fake_get)
    assert wiki.check_link_exists("SRC", "TARGET") is True
