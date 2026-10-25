"""Thin client for the Elexon BMRS Insights API (public, no key needed)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

import httpx

from . import config


def _get(client: httpx.Client, path: str, params: dict, retries: int = 3) -> list[dict]:
    url = f"{config.ELEXON_BASE}{path}"
    for attempt in range(retries):
        try:
            r = client.get(url, params=params, timeout=120)
            r.raise_for_status()
            body = r.json()
            # Stream endpoints return a bare list; non-stream ones wrap in {"data": [...]}.
            return body["data"] if isinstance(body, dict) else body
        except (httpx.HTTPError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return []


def fetch_actuals(client: httpx.Client) -> list[dict]:
    """FUELHH, WIND only. Returns [{startTime, generation}]."""
    rows = _get(
        client,
        "/datasets/FUELHH/stream",
        {
            "settlementDateFrom": config.TARGET_START,
            "settlementDateTo": config.TARGET_END,
            "fuelType": "WIND",
        },
    )
    return [
        {"startTime": r["startTime"], "generation": r["generation"]}
        for r in rows
        if r.get("fuelType", "WIND") == "WIND" and r.get("generation") is not None
    ]


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def fetch_forecasts(client: httpx.Client, window_days: int = 2) -> list[dict]:
    """WINDFOR, fetched in small publish-time windows to stay within API limits."""
    start = _parse(config.PUBLISH_START)
    end = _parse(config.PUBLISH_END)
    t_lo = _parse(config.TARGET_START + "T00:00:00Z")
    t_hi = _parse(config.TARGET_END + "T23:59:59Z")
    out: dict[tuple[str, str], dict] = {}
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=window_days), end)
        rows = _get(
            client,
            "/datasets/WINDFOR/stream",
            {
                "publishDateTimeFrom": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "publishDateTimeTo": nxt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        for r in rows:
            if r.get("generation") is None:
                continue
            st, pt = _parse(r["startTime"]), _parse(r["publishTime"])
            horizon_h = (st - pt).total_seconds() / 3600
            if not (t_lo <= st <= t_hi) or horizon_h < 0 or horizon_h > config.MAX_HORIZON_H:
                continue
            out[(r["startTime"], r["publishTime"])] = {
                "startTime": r["startTime"],
                "publishTime": r["publishTime"],
                "generation": r["generation"],
            }
        cur = nxt
    return list(out.values())


def download_all() -> dict:
    with httpx.Client() as client:
        return {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "actuals": fetch_actuals(client),
            "forecasts": fetch_forecasts(client),
        }


def save(payload: dict) -> None:
    config.DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.DATA_FILE.write_text(json.dumps(payload))


def load_or_download() -> dict:
    """Serve from the local snapshot if present; otherwise pull live and cache it."""
    if config.DATA_FILE.exists():
        return json.loads(config.DATA_FILE.read_text())
    payload = download_all()
    save(payload)
    return payload


if __name__ == "__main__":  # python -m app.elexon  -> refresh the snapshot
    p = download_all()
    save(p)
    print(f"actuals={len(p['actuals'])} forecasts={len(p['forecasts'])} -> {config.DATA_FILE}")
