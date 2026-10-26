import { useEffect, useState } from "react";
import { api } from "./api.js";
import DayView from "./DayView.jsx";
import AccuracyView from "./AccuracyView.jsx";

export default function App() {
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("day");
  const [cutoff, setCutoff] = useState(9);
  const [selectedDate, setSelectedDate] = useState(null);

  useEffect(() => {
    api.meta().then((m) => { setMeta(m); setCutoff(m.default_cutoff_hour); setSelectedDate(m.dates[Math.min(4, m.dates.length - 1)]); }).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="page"><p className="err">Could not load data: {error}</p></div>;
  if (!meta) return <div className="page"><p>Loading…</p></div>;

  return (
    <div className="page">
      <header>
        <div>
          <div className="brand"><img src="/wind-mark.svg" alt="" /><span>Wind intelligence</span></div>
          <h1>UK Wind Generation – Day-Ahead Forecast Portal</h1>
          <p className="sub">
            National wind forecasts (Elexon WINDFOR) vs outturn (FUELHH) · January 2026 deliveries
          </p>
          <div className="status-row"><span className="status-dot" /> Live snapshot · 31 delivery days · Europe/London</div>
        </div>
        <label className="cutoff">
          Gate closure (UK time, D-1)
          <select value={cutoff} onChange={(e) => setCutoff(Number(e.target.value))}>
            {[7, 8, 9, 10, 11, 12].map((h) => <option key={h} value={h}>{String(h).padStart(2, "0")}:00</option>)}
          </select>
        </label>
      </header>
      <nav>
        <button className={tab === "day" ? "on" : ""} onClick={() => setTab("day")}><span>◈</span> Day-ahead decision</button>
        <button className={tab === "acc" ? "on" : ""} onClick={() => setTab("acc")}><span>⌁</span> Forecast accuracy</button>
      </nav>
      {tab === "day" ? <DayView meta={meta} cutoff={cutoff} date={selectedDate} onDateChange={setSelectedDate} /> : <AccuracyView cutoff={cutoff} />}
      <footer>Contains BMRS data © Elexon Limited.</footer>
    </div>
  );
}
