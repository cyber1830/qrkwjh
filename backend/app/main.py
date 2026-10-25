"""FastAPI app: JSON API under /api, built React bundle served from /."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import analysis, config, elexon

app = FastAPI(title="Wind Forecast Portal", version="1.0.0")

_state: dict = {}


def _load() -> dict:
    if not _state:
        payload = elexon.load_or_download()
        a, f = analysis.build_frames(payload["actuals"], payload["forecasts"])
        _state.update(payload=payload, actuals=a, forecasts=f)
    return _state


@lru_cache(maxsize=48)
def _decision(cutoff_hour: int) -> pd.DataFrame:
    s = _load()
    return analysis.decision_forecasts(s["actuals"], s["forecasts"], cutoff_hour)


def _iso(ts) -> str | None:
    return None if pd.isna(ts) else ts.isoformat().replace("+00:00", "Z")


def _num(x):
    return None if pd.isna(x) else round(float(x), 1)


CutoffQ = Query(config.DEFAULT_CUTOFF_HOUR, ge=0, le=23, description="Gate closure hour (UK time) on D-1")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    s = _load()
    dec = _decision(config.DEFAULT_CUTOFF_HOUR)
    return {
        "dates": sorted(dec["target_date"].unique().tolist()),
        "default_cutoff_hour": config.DEFAULT_CUTOFF_HOUR,
        "latest_actual": _iso(s["actuals"]["start"].max()),
        "latest_forecast_publish": _iso(s["forecasts"]["publish"].max()),
        "data_fetched_at": s["payload"].get("fetchedAt"),
    }


@app.get("/api/day/{target_date}")
def day(target_date: str, cutoff_hour: int = CutoffQ):
    """What the buyer sees at gate closure for one delivery day."""
    dec = _decision(cutoff_hour)
    d = dec[dec["target_date"] == target_date]
    if d.empty:
        raise HTTPException(404, f"No forecast available for {target_date}")
    decided_at = d["decision"].iloc[0]
    return {
        "target_date": target_date,
        "decision_time": _iso(decided_at),
        "latest_forecast_publish": _iso(d["publish"].max()),
        "rows": [
            {
                "start": _iso(r.start),
                "forecast_mw": _num(r.forecast),
                "actual_mw": _num(r.actual),
                "published": _iso(r.publish),
                "horizon_h": round(float(r.horizon_h), 1),
            }
            for r in d.itertuples()
        ],
        "forecast_total_mwh": round(float(d["forecast"].sum() / 2), 0),  # MW per half-hour -> MWh
        "forecast_min_mw": _num(d["forecast"].min()),
        "forecast_max_mw": _num(d["forecast"].max()),
        "day_accuracy": analysis.metrics(d),
        "risk": analysis.risk_buffer_for(dec, target_date),
    }


@app.get("/api/accuracy")
def accuracy(cutoff_hour: int = CutoffQ):
    s = _load()
    dec = _decision(cutoff_hour)
    scored = dec.dropna(subset=["actual"])
    return {
        "cutoff_hour": cutoff_hour,
        "summary": analysis.metrics(scored),
        "daily": analysis.grouped(scored, "target_date"),
        "by_hour": analysis.grouped(scored, "hour"),
        "by_horizon": analysis.by_horizon(s["actuals"], s["forecasts"]),
        "error_histogram": analysis.histogram(scored),
    }


# --- static front-end (only present in the Docker / production build) ---
if config.STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=config.STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = config.STATIC_DIR / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(config.STATIC_DIR / "index.html")
