import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest
app = pytest.importorskip("app")


def test_root_returns_index_html():
    client = app.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Wikipedia Race" in resp.data
