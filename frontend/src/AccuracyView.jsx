import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, fmtMW } from "./api.js";
import Kpi from "./Kpi.jsx";

function Chart({ title, note, children }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={280}>{children}</ResponsiveContainer>
      {note && <p className="note">{note}</p>}
    </div>
  );
}

export default function AccuracyView({ cutoff }) {
  const [d, setD] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setD(null); setError(null);
    api.accuracy(cutoff).then(setD).catch((e) => setError(e.message));
  }, [cutoff]);

  if (error) return <p className="err">{error}</p>;
  if (!d) return <p>Loading…</p>;
  const s = d.summary;

  return (
    <section>
      <p className="note">
        Scored on the forecast that was actually available at gate closure ({String(cutoff).padStart(2, "0")}:00 on D-1) for every
        January half-hour that has an outturn.
      </p>
      <div className="kpis">
        <Kpi label="Mean absolute error" value={fmtMW(s.mae_mw)} hint={`${s.wape_pct}% of generation`} />
        <Kpi label="RMSE" value={fmtMW(s.rmse_mw)} hint="Penalises big misses" />
        <Kpi label="Bias" value={fmtMW(s.bias_mw)} hint="Positive = forecast too high" />
        <Kpi label="P90 absolute error" value={fmtMW(s.p90_abs_error_mw)} hint="9 in 10 slots miss by less" />
        <Kpi label="P90 over-forecast" value={fmtMW(s.p90_overforecast_mw)} hint="Under-buying risk buffer" />
        <Kpi label="Half-hours scored" value={s.n.toLocaleString("en-GB")} />
      </div>

      <Chart title="Daily MAE and bias" note="Spot the days where the forecast struggled (e.g. storms, ramps).">
        <LineChart data={d.daily}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="target_date" tickFormatter={(v) => v.slice(8)} />
          <YAxis unit=" MW" width={80} />
          <Tooltip formatter={(v) => fmtMW(v)} />
          <Legend />
          <Line dataKey="mae_mw" name="MAE" stroke="#0b6bcb" strokeWidth={2} />
          <Line dataKey="bias_mw" name="Bias" stroke="#d97706" strokeWidth={2} />
        </LineChart>
      </Chart>

      <Chart title="Error vs forecast lead time (all forecasts)" note="Shows how much accuracy improves as the forecast gets closer to delivery.">
        <BarChart data={d.by_horizon}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis unit=" MW" width={80} />
          <Tooltip formatter={(v) => fmtMW(v)} />
          <Legend />
          <Bar dataKey="mae_mw" name="MAE" fill="#0b6bcb" />
          <Bar dataKey="p90_abs_error_mw" name="P90 abs error" fill="#93c5fd" />
        </BarChart>
      </Chart>

      <Chart title="Error by hour of delivery day (UK time)">
        <BarChart data={d.by_hour}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="hour" />
          <YAxis unit=" MW" width={80} />
          <Tooltip formatter={(v) => fmtMW(v)} />
          <Legend />
          <Bar dataKey="mae_mw" name="MAE" fill="#0b6bcb" />
          <Bar dataKey="bias_mw" name="Bias" fill="#d97706" />
        </BarChart>
      </Chart>

      <Chart title="Distribution of forecast error (forecast − actual)" note="Right of zero = over-forecast, i.e. you would have bought too little.">
        <BarChart data={d.error_histogram}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="from_mw" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" name="Half-hours" fill="#16a34a" />
        </BarChart>
      </Chart>
    </section>
  );
}
