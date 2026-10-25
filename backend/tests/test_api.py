"""API smoke test against synthetic data (no network)."""
import json
import math

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import config

    actuals, forecasts = [], []
    for day in range(1, 6):
        for slot in range(48):
            h, m = divmod(slot * 30, 60)
            st = f"2026-01-{day:02d}T{h:02d}:{m:02d}:00Z"
            truth = 5000 + 3000 * math.sin(slot / 8 + day)
            actuals.append({"startTime": st, "generation": round(truth)})
            for hrs_before in range(6, 49, 6):  # a forecast every 6h, up to 48h ahead
                from datetime import datetime, timedelta

                t = datetime.fromisoformat(st.replace("Z", "+00:00")) - timedelta(hours=hrs_before)
                forecasts.append(
                    {
                        "startTime": st,
                        "publishTime": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "generation": round(truth + 100 * hrs_before / 6),
                    }
                )
    f = tmp_path / "snap.json"
    f.write_text(json.dumps({"fetchedAt": "test", "actuals": actuals, "forecasts": forecasts}))
    monkeypatch.setattr(config, "DATA_FILE", f)

    from app import main

    main._state.clear()
    main._decision.cache_clear()
    return TestClient(main.app)


def test_meta_and_day(client):
    meta = client.get("/api/meta").json()
    assert "2026-01-03" in meta["dates"]
    d = client.get("/api/day/2026-01-03?cutoff_hour=9").json()
    assert len(d["rows"]) == 48
    assert d["decision_time"].startswith("2026-01-02T09:00")
    assert all(r["published"] <= d["decision_time"] for r in d["rows"])


def test_accuracy(client):
    a = client.get("/api/accuracy").json()
    assert a["summary"]["n"] > 0
    assert len(a["daily"]) >= 3
    assert a["by_horizon"]


def test_unknown_day_404(client):
    assert client.get("/api/day/2030-01-01").status_code == 404
