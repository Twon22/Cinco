import { useState } from "react";
import axios from "axios";

const SWEEPS = {
  "boundary-lookback": {
    label: "Boundary lookback",
    unit: "trading days",
    key: "boundary_lookback",
    blurb: "How long a month-boundary level stays checkable. Set from a single confirmed example, so it is the least validated parameter in the framework.",
  },
  "intraday-window": {
    label: "Short window",
    unit: "trading days",
    key: "intraday_window",
    blurb: "The everyday lookback. This is the rule validated hardest against hand-checked cases.",
  },
  "tolerance": {
    label: "Price tolerance",
    unit: "points",
    key: "tolerance",
    blurb: "How close two levels must be to count as aligned. Calibrated against confirmed matches, which ran 0.09 to 2.89 points apart.",
  },
};

export default function Calibration() {
  const [which, setWhich] = useState("boundary-lookback");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ran, setRan] = useState(false);

  const run = (endpoint) => {
    setWhich(endpoint);
    setLoading(true);
    setResults([]);
    axios.get(`/api/calibration/${endpoint}`)
      .then(r => setResults(r.data.results || []))
      .catch(() => setResults([]))
      .finally(() => { setLoading(false); setRan(true); });
  };

  const cfg = SWEEPS[which];
  const maxPct = Math.max(...results.map(r => r.pct_days_flagged), 1);

  return (
    <div>
      <h1>Calibration</h1>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "1rem", lineHeight: 1.5 }}>
          Runs the scanner repeatedly at different settings over the same data.
          If almost every day gets flagged, "alignment" stops distinguishing anything —
          so the share of days flagged is the number that matters most here.
        </p>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {Object.entries(SWEEPS).map(([k, v]) => (
            <button key={k}
              className={which === k && ran ? "btn-primary" : "btn-secondary"}
              onClick={() => run(k)} disabled={loading}>
              {v.label}
            </button>
          ))}
        </div>
        {ran && (
          <p style={{ fontSize: "0.78rem", color: "#64748b", marginTop: "0.8rem", lineHeight: 1.5 }}>
            {cfg.blurb}
          </p>
        )}
      </div>

      {loading && <p style={{ color: "#64748b" }}>Running sweep…</p>}

      {results.length > 0 && (
        <>
          <h2>Share of days flagged</h2>
          <div className="card" style={{ marginBottom: "1.25rem" }}>
            {results.map((r, i) => {
              const pct = r.pct_days_flagged;
              const alarming = pct >= 50;
              return (
                <div key={i} style={{ marginBottom: "0.6rem" }}>
                  <div style={{
                    display: "flex", justifyContent: "space-between",
                    fontSize: "0.8rem", marginBottom: "0.2rem",
                  }}>
                    <span style={{ color: "#94a3b8" }}>
                      {cfg.label} = {r[cfg.key]} {cfg.unit}
                    </span>
                    <span style={{ color: alarming ? "#f87171" : "#4ade80", fontWeight: 600 }}>
                      {pct}%
                    </span>
                  </div>
                  <div style={{ background: "#1e2235", borderRadius: "4px", height: "18px" }}>
                    <div style={{
                      width: `${(pct / maxPct) * 100}%`,
                      height: "100%", borderRadius: "4px",
                      background: alarming ? "#7f1d1d" : "#7c3aed",
                    }} />
                  </div>
                </div>
              );
            })}
            <p style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.8rem" }}>
              Red marks settings where over half of all days get flagged.
            </p>
          </div>

          <h2>Full results</h2>
          <table>
            <thead>
              <tr>
                <th>{cfg.label}</th><th>Total</th><th>x==x</th><th>x==boundary</th>
                <th>Days flagged</th><th>% of days</th>
                <th>From short window</th><th>From boundary rule</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td style={{ color: "#a78bfa" }}>{r[cfg.key]}</td>
                  <td>{r.total_matches}</td>
                  <td>{r.x_to_x}</td>
                  <td>{r.x_to_boundary}</td>
                  <td>{r.days_with_match} / {r.scannable_days}</td>
                  <td style={{ color: r.pct_days_flagged >= 50 ? "#f87171" : "#4ade80" }}>
                    {r.pct_days_flagged}%
                  </td>
                  <td>{r.from_short_window}</td>
                  <td>{r.from_boundary_rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {ran && results.length === 0 && !loading && (
        <p style={{ color: "#64748b" }}>
          No results. Make sure bars are uploaded and the pipeline has run.
        </p>
      )}
    </div>
  );
}
