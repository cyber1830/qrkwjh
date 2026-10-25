# Wind Forecast Portal (UK day-ahead buying)

Web app that helps a UK utility's day-ahead desk (1) see the **latest wind forecast available at gate closure** and
(2) **quantify how wrong those forecasts have been**, using only Elexon national wind data for **January 2026**.

- **Backend:** Python 3.12, FastAPI, pandas
- **Frontend:** React 18 (Vite), Recharts
- **Packaging:** Docker (single image, API serves the built UI)
- **Live app:** `<ADD VERCEL/HEROKU LINK HERE>`

## Data used

| Purpose | Dataset | Fields |
|---|---|---|
| Actual generation | `FUELHH` (stream), `fuelType=WIND` | `startTime`, `generation` |
| Forecasts | `WINDFOR` (stream) | `startTime`, `publishTime`, `generation` |

Base URL `https://data.elexon.co.uk/bmrs/api/v1` (public, no key). Only deliveries from 1–31 Jan 2026 are used.
Forecasts issued more than 72 h before the target half-hour are dropped (irrelevant to a day-ahead decision).

## Key analysis decisions

1. **"Latest forecast available when deciding."** Day-ahead orders are placed on D-1 before gate closure
   (default **09:00 UK**, selectable 07:00–12:00 in the UI). For each target half-hour we take the forecast with the
   greatest `publishTime <= gate closure`. Later forecasts are ignored (they would be look-ahead).
2. **Accuracy is measured on those same decision-time forecasts.** Metrics: MAE, RMSE, bias (forecast − actual),
   WAPE (sum |err| / sum actual; used instead of MAPE because wind can be near 0), P50/P90 absolute error and
   **P90 over-forecast** (the amount wind undershot the forecast in the worst 10% of slots – the relevant risk for a buyer
   who under-buys when the forecast is too high).
3. **Error by lead time** across *all* forecasts, so the user sees how much accuracy improves closer to delivery.
4. **No look-ahead in the suggested safety buffer.** For delivery day D the buffer uses only delivery days ≤ D-2
   (day D-1 outturn is not complete at D-1 morning). The "Cautious" line = forecast − P90 over-forecast.
5. Timestamps are UTC from Elexon and displayed in `Europe/London`.

Limitations: national-level only; no demand data (so we show wind available, not the MW to buy); error buffer is a
simple empirical quantile, not a probabilistic model.

## Repository layout

```
backend/app/config.py     constants (date window, gate closure, paths)
backend/app/elexon.py     Elexon client + local JSON snapshot (python -m app.elexon refreshes it)
backend/app/analysis.py   pure pandas logic: decision forecast, metrics, horizon analysis
backend/app/main.py       FastAPI routes (/api/meta, /api/day/{date}, /api/accuracy) + serves the UI
backend/tests/            pytest unit + API tests (synthetic data, no network)
frontend/src/             React app (DayView, AccuracyView, API helpers)
data/                     cached Elexon snapshot (jan2026.json)
Dockerfile, heroku.yml    container build and Heroku container deploy
```

## Run it

**Docker (recommended)**
```bash
docker compose up --build        # http://localhost:8000
```

**Local dev**
```bash
cd backend && pip install -r requirements.txt
python -m app.elexon             # downloads data/jan2026.json (needs internet)
uvicorn app.main:app --reload    # API on :8000

cd ../frontend && npm install && npm run dev   # UI on :5173, proxies /api to :8000
```

**Tests:** `cd backend && python -m pytest -q`

## Deploy (Heroku, container stack)

```bash
heroku create <anonymous-name>
heroku stack:set container
git push heroku main
```

## API

- `GET /api/meta` – available delivery days, data freshness
- `GET /api/day/{YYYY-MM-DD}?cutoff_hour=9` – forecast at gate closure vs actual, risk buffer
- `GET /api/accuracy?cutoff_hour=9` – summary, daily, by-hour, by-lead-time, error histogram
