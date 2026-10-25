"""All the maths lives here, free of any web/IO code so it is easy to test.

Key idea: a day-ahead buyer standing at gate closure on D-1 only knows forecasts
published *before* that moment. For every target half-hour we therefore take the
most recent forecast with publishTime <= decision time. Accuracy is measured on
exactly those "decision forecasts" (plus a separate view across all horizons).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def build_frames(actuals: list[dict], forecasts: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    a = pd.DataFrame(actuals).rename(columns={"startTime": "start", "generation": "actual"})
    a["start"] = pd.to_datetime(a["start"], utc=True)
    a = a.drop_duplicates("start").sort_values("start")

    f = pd.DataFrame(forecasts).rename(
        columns={"startTime": "start", "publishTime": "publish", "generation": "forecast"}
    )
    f["start"] = pd.to_datetime(f["start"], utc=True)
    f["publish"] = pd.to_datetime(f["publish"], utc=True)
    f["horizon_h"] = (f["start"] - f["publish"]).dt.total_seconds() / 3600
    return a, f


def decision_time(start: pd.Series, cutoff_hour: int) -> pd.Series:
    """Gate closure for each target: 'cutoff_hour' o'clock UK time on the day before delivery."""
    local = start.dt.tz_convert(config.TIMEZONE).dt.tz_localize(None)
    dec_local = local.dt.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)
    dec = dec_local.dt.tz_localize(config.TIMEZONE, ambiguous="NaT", nonexistent="shift_forward")
    return dec.dt.tz_convert("UTC")


def decision_forecasts(a: pd.DataFrame, f: pd.DataFrame, cutoff_hour: int) -> pd.DataFrame:
    """Latest forecast available at gate closure for each half-hour, joined to actuals."""
    f = f.copy()
    f["decision"] = decision_time(f["start"], cutoff_hour)
    eligible = f[f["publish"] <= f["decision"]]
    latest = eligible.sort_values("publish").groupby("start", as_index=False).tail(1)
    df = latest.merge(a, on="start", how="left").sort_values("start").reset_index(drop=True)
    df["error"] = df["forecast"] - df["actual"]  # + means over-forecast (risk of under-buying)
    local = df["start"].dt.tz_convert(config.TIMEZONE)
    df["target_date"] = local.dt.strftime("%Y-%m-%d")
    df["hour"] = local.dt.hour
    return df


def metrics(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["actual", "forecast"])
    if d.empty:
        return {"n": 0}
    err = d["forecast"] - d["actual"]
    ae = err.abs()
    total_actual = float(d["actual"].sum())
    return {
        "n": int(len(d)),
        "mean_actual_mw": round(float(d["actual"].mean()), 1),
        "mae_mw": round(float(ae.mean()), 1),
        "rmse_mw": round(float(np.sqrt((err**2).mean())), 1),
        "bias_mw": round(float(err.mean()), 1),
        # weighted abs % error: robust where actual wind is near zero (plain MAPE explodes)
        "wape_pct": round(float(ae.sum()) / total_actual * 100, 1) if total_actual else None,
        "p50_abs_error_mw": round(float(ae.quantile(0.5)), 1),
        "p90_abs_error_mw": round(float(ae.quantile(0.9)), 1),
        # How far wind may undershoot the forecast in a bad-but-plausible case (P90 of signed error)
        "p90_overforecast_mw": round(float(max(err.quantile(0.9), 0)), 1),
    }


def grouped(df: pd.DataFrame, key: str) -> list[dict]:
    out = []
    for k, g in df.dropna(subset=["actual"]).groupby(key):
        m = metrics(g)
        m[key] = k.item() if hasattr(k, "item") else k
        out.append(m)
    return out


def by_horizon(a: pd.DataFrame, f: pd.DataFrame, bucket_h: int = 6) -> list[dict]:
    """Accuracy of *all* forecasts, bucketed by how far ahead they were issued."""
    d = f.merge(a, on="start", how="inner")
    d["bucket"] = (np.floor(d["horizon_h"] / bucket_h) * bucket_h).astype(int)
    rows = grouped(d, "bucket")
    for r in rows:
        r["label"] = f"{r['bucket']}-{r['bucket'] + bucket_h}h"
    return sorted(rows, key=lambda r: r["bucket"])


def histogram(df: pd.DataFrame, bins: int = 24) -> list[dict]:
    e = (df["forecast"] - df["actual"]).dropna()
    if e.empty:
        return []
    counts, edges = np.histogram(e, bins=bins)
    return [
        {"from_mw": round(float(edges[i])), "to_mw": round(float(edges[i + 1])), "count": int(c)}
        for i, c in enumerate(counts)
    ]


def risk_buffer_for(dec: pd.DataFrame, target_date: str) -> dict:
    """Error statistics usable *on the day of the decision* - no look-ahead.

    A decision for delivery day D is taken on D-1 morning, when day D-1 actuals are
    incomplete, so we only learn from delivery days <= D-2.
    """
    cutoff = (pd.Timestamp(target_date) - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    hist = dec[dec["target_date"] <= cutoff]
    m = metrics(hist)
    return {"based_on_days_up_to": cutoff, **m} if m.get("n") else {"n": 0}
