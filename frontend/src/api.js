async function get(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}
export const api = {
  meta: () => get("/api/meta"),
  day: (date, cutoff) => get(`/api/day/${date}?cutoff_hour=${cutoff}`),
  accuracy: (cutoff) => get(`/api/accuracy?cutoff_hour=${cutoff}`),
};

export const fmtMW = (v) => (v == null ? "–" : Math.round(v).toLocaleString("en-GB") + " MW");
export const fmtTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString("en-GB", {
        timeZone: "Europe/London", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
      })
    : "–";
export const hhmm = (iso) =>
  new Date(iso).toLocaleTimeString("en-GB", { timeZone: "Europe/London", hour: "2-digit", minute: "2-digit" });
