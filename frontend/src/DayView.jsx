import { useEffect, useMemo } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, fmtMW, fmtTime, hhmm } from "./api.js";
import Kpi from "./Kpi.jsx";

export default function DayView({ meta, cutoff, date, onDateChange }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null); setError(null);
    api.day(date, cutoff).then(setData).catch((e) => setError(e.message));
  }, [date, cutoff]);

  const chart = useMemo(() => {
    if (!data) return [];
    const buf = data.risk?.p90_overforecast_mw;
    return data.rows.map((r) => ({
      time: hhmm(r.start),
      Forecast: r.forecast_mw,
      "Cautious (forecast − P90 shortfall)": buf != null && r.forecast_mw != null ? Math.max(0, r.forecast_mw - buf) : null,
      Actual: r.actual_mw,
    }));
  }, [data]);

  const risk = data?.risk;
  const acc = data?.day_accuracy;

  return (
    <section>
      <div className="section-intro"><div><span className="eyebrow">Decision workspace</span><h2>Plan tomorrow with the latest wind view</h2></div><span className="data-badge">● Elexon data</span></div>
      <div className="toolbar">
        <label>
          Delivery day
          <select value={date ?? ""} onChange={(e) => onDateChange(e.target.value)}>
            {meta.dates.map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>
        {data && (
          <span className="note">
            Decision taken <b>{fmtTime(data.decision_time)}</b> · latest forecast used was published{" "}
            <b>{fmtTime(data.latest_forecast_publish)}</b>
          </span>
        )}
      </div>

      {error && <p className="err">{error}</p>}
      {!data && !error && <div className="loading-card"><span className="spinner" /> Loading forecast workspace…</div>}

      {data && (
        <>
          <div className="kpis">
            <Kpi label="Forecast wind energy" value={`${data.forecast_total_mwh.toLocaleString("en-GB")} MWh`} hint="Sum over the delivery day" />
            <Kpi label="Forecast range" value={`${fmtMW(data.forecast_min_mw)} – ${fmtMW(data.forecast_max_mw)}`} hint="Min – max half-hour" />
            <Kpi
              label="Suggested safety buffer"
              value={risk?.n ? fmtMW(risk.p90_overforecast_mw) : "—"}
              hint={risk?.n ? `P90 over-forecast · history through ${risk.based_on_days_up_to}` : "Builds after earlier delivery days are available"}
            />
            <Kpi
              label="Typical error (MAE)"
              value={risk?.n ? fmtMW(risk.mae_mw) : "—"}
              hint={risk?.n ? `${risk.wape_pct}% of generation · no look-ahead` : "No prior-day history for this decision"}
            />
          </div>

          <div className="card">
            <h3>Half-hourly wind: forecast known at decision time vs outturn</h3>
            <ResponsiveContainer width="100%" height={340}>
              <LineChart data={chart} margin={{ left: 10, right: 20, top: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" interval={3} />
                <YAxis tickFormatter={(v) => `${v / 1000}k`} unit=" MW" width={80} />
                <Tooltip formatter={(v) => fmtMW(v)} />
                <Legend />
                <Line type="monotone" dataKey="Forecast" stroke="#0b6bcb" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="Cautious (forecast − P90 shortfall)" stroke="#d97706" dot={false} strokeDasharray="5 4" />
                <Line type="monotone" dataKey="Actual" stroke="#16a34a" dot={false} strokeWidth={2} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
            <p className="note">
              Procurement from thermal/other sources = demand − wind. Plan on the dashed line if you want to
              be covered in 9 out of 10 half-hours historically. Actuals appear once Elexon has published them.
            </p>
          </div>

          {acc?.n > 0 && (
            <p className="note">
              Hindsight check for this day: MAE {fmtMW(acc.mae_mw)}, bias {fmtMW(acc.bias_mw)} (positive = forecast too high).
            </p>
          )}

          <details className="card">
            <summary>Show every forecast row (with the publish time of the forecast used)</summary>
            <div className="tablewrap">
              <table>
                <thead><tr><th>Half-hour</th><th>Forecast</th><th>Actual</th><th>Published</th><th>Lead time</th></tr></thead>
                <tbody>
                  {data.rows.map((r) => (
                    <tr key={r.start}>
                      <td>{hhmm(r.start)}</td><td>{fmtMW(r.forecast_mw)}</td><td>{fmtMW(r.actual_mw)}</td>
                      <td>{fmtTime(r.published)}</td><td>{r.horizon_h} h</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}
