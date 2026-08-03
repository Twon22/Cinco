import { useState } from "react";
import axios from "axios";

export default function Journey() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ran, setRan] = useState(false);
  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    hold_days: 8,
  });

  const set = (k, v) => setFilters(f => ({ ...f, [k]: v }));

  const run = () => {
    setLoading(true);
    const params = { hold_days: filters.hold_days };
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;

    axios.get("/api/journey/candidates", { params })
      .then(r => setRows(r.data.candidates || []))
      .catch(() => setRows([]))
      .finally(() => { setLoading(false); setRan(true); });
  };

  const exact = rows.filter(r => r.diff <= 0.5).length;

  return (
    <div>
      <h1>Journey vs. Trade</h1>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "1rem", lineHeight: 1.5 }}>
          An alignment flags a day worth watching, not necessarily a day worth trading.
          When a day's move runs into a <em>later</em> day's own open-range boundary,
          that day was likely the approach into the later setup — not an independent trade.
          Counting both would double-count one move.
        </p>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: "0.75rem", alignItems: "end",
        }}>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#64748b" }}>From (optional)</label>
            <input type="date" value={filters.start_date}
              onChange={e => set("start_date", e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#64748b" }}>To (optional)</label>
            <input type="date" value={filters.end_date}
              onChange={e => set("end_date", e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Look-ahead (trading days)</label>
            <input type="number" min={2} max={20} value={filters.hold_days}
              onChange={e => set("hold_days", Number(e.target.value))} />
          </div>
          <div>
            <button className="btn-primary" onClick={run} disabled={loading}>
              {loading ? "Scanning…" : "Find candidates"}
            </button>
          </div>
        </div>

        <div style={{
          marginTop: "0.9rem", paddingTop: "0.75rem",
          borderTop: "1px solid #2d3148",
          fontSize: "0.78rem", color: "#fbbf24", lineHeight: 1.5,
        }}>
          The look-ahead matters and no single value is right. Apr 1 → Apr 2 only
          appears at 4 days; Jan 22 → Jan 29 needs 6. Vary it and compare rather
          than trusting one setting.
        </div>
      </div>

      {ran && (
        <div style={{ marginBottom: "1rem", fontSize: "0.85rem", color: "#64748b" }}>
          <strong style={{ color: "#a78bfa" }}>{rows.length}</strong> candidates
          {" · "}<strong style={{ color: "#d8b4fe" }}>{exact}</strong> landing within 0.5 points
        </div>
      )}

      {loading ? (
        <p style={{ color: "#64748b" }}>Scanning…</p>
      ) : ran && rows.length === 0 ? (
        <p style={{ color: "#64748b" }}>No journey candidates found for these settings.</p>
      ) : rows.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>Journey day</th><th>Dir</th><th>Break bar</th>
              <th>Ran to</th><th>Destination</th><th>Dest. level</th>
              <th>Diff</th><th>Days ahead</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.journey_date}</td>
                <td>
                  <span className={`badge badge-${r.direction === "up" ? "buy" : "sell"}`}>
                    {r.direction}
                  </span>
                </td>
                <td>{r.break_bar}</td>
                <td>{r.extreme}</td>
                <td style={{ color: "#a78bfa" }}>{r.destination_date}</td>
                <td>{r.destination_level} ({r.destination_price})</td>
                <td style={{ color: r.diff <= 0.5 ? "#4ade80" : "#94a3b8" }}>{r.diff}</td>
                <td>{r.trading_days_ahead}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: "#64748b" }}>
          Set a date range and run the scan. Leave the dates blank to check every day.
        </p>
      )}
    </div>
  );
}
