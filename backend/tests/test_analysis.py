"""Unit tests on a tiny hand-made dataset so the expected answers are obvious."""
import pandas as pd

from app import analysis


def _frames():
    # Target: 2026-01-03 12:00Z. Three forecasts issued at different times; actual = 1000.
    actuals = [{"startTime": "2026-01-03T12:00:00Z", "generation": 1000}]
    forecasts = [
        {"startTime": "2026-01-03T12:00:00Z", "publishTime": "2026-01-02T06:00:00Z", "generation": 900},
        {"startTime": "2026-01-03T12:00:00Z", "publishTime": "2026-01-02T08:30:00Z", "generation": 1200},  # latest before 09:00
        {"startTime": "2026-01-03T12:00:00Z", "publishTime": "2026-01-02T10:00:00Z", "generation": 5000},  # after gate closure
    ]
    return analysis.build_frames(actuals, forecasts)


def test_decision_forecast_ignores_forecasts_after_gate_closure():
    a, f = _frames()
    dec = analysis.decision_forecasts(a, f, cutoff_hour=9)
    assert len(dec) == 1
    assert dec.loc[0, "forecast"] == 1200
    assert dec.loc[0, "error"] == 200  # over-forecast by 200 MW


def test_later_cutoff_picks_later_forecast():
    a, f = _frames()
    dec = analysis.decision_forecasts(a, f, cutoff_hour=11)
    assert dec.loc[0, "forecast"] == 5000


def test_metrics_values():
    df = pd.DataFrame({"forecast": [110.0, 90.0, 130.0], "actual": [100.0, 100.0, 100.0]})
    m = analysis.metrics(df)
    assert m["n"] == 3
    assert m["mae_mw"] == round((10 + 10 + 30) / 3, 1)
    assert m["bias_mw"] == round((10 - 10 + 30) / 3, 1)
    assert m["wape_pct"] == round(50 / 300 * 100, 1)


def test_metrics_empty_is_safe():
    assert analysis.metrics(pd.DataFrame({"forecast": [], "actual": []})) == {"n": 0}


def test_risk_buffer_has_no_lookahead():
    a, f = _frames()
    dec = analysis.decision_forecasts(a, f, 9)
    # Decision for 4 Jan may only learn from days <= 2 Jan -> nothing yet
    assert analysis.risk_buffer_for(dec, "2026-01-04") == {"n": 0}
    # Decision for 5 Jan may learn from 3 Jan
    assert analysis.risk_buffer_for(dec, "2026-01-05")["n"] == 1


def test_horizon_buckets():
    a, f = _frames()
    rows = analysis.by_horizon(a, f, bucket_h=6)
    labels = {r["label"] for r in rows}
    assert "24-30h" in labels or "30-36h" in labels
