import { useEffect, useState } from "react";
import axios from "axios";

export default function Dashboard() {
  const [trades, setTrades] = useState([]);
  const [alignments, setAlignments] = useState([]);

  useEffect(() => {
    axios.get("/api/trades/").then(r => setTrades(r.data)).catch(() => {});
    axios.get("/api/alignments/?status=pending&limit=5").then(r => setAlignments(r.data)).catch(() => {});
  }, []);

  const pips = trades.map(t => t.pips_4day).filter(Boolean);
  const avgPips = pips.length ? (pips.reduce((a, b) => a + b, 0) / pips.length).toFixed(0) : "—";

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{trades.length}</div>
          <div className="stat-label">Verified Trades</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{avgPips}</div>
          <div className="stat-label">Avg Pips (4-day)</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{alignments.length}</div>
          <div className="stat-label">Pending Alignments</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{trades.filter(t => t.direction === "sell").length}</div>
          <div className="stat-label">Sells</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{trades.filter(t => t.direction === "buy").length}</div>
          <div className="stat-label">Buys</div>
        </div>
      </div>

      <h2>Pending Alignments</h2>
      <div className="card">
        {alignments.length === 0 ? <p style={{color:"#64748b"}}>No pending alignments.</p> : (
          <table>
            <thead><tr><th>Date</th><th>Type</th><th>Match</th><th>Diff</th></tr></thead>
            <tbody>
              {alignments.map(a => (
                <tr key={a.id}>
                  <td>{a.today_date}</td>
                  <td><span className="badge badge-x">{a.match_type}</span></td>
                  <td>{a.today_level} → {a.prior_date} {a.prior_level}</td>
                  <td>{a.diff}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
