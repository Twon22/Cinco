import { useEffect, useState } from "react";
import axios from "axios";

const empty = {
  trade_date: "", entry_time: "", entry_price: "", direction: "sell",
  sr_reference: "", entry_type: "watch_forward", pips_3day: "", pips_4day: "",
  hold_days: "", notes: "",
};

export default function TradeLog() {
  const [trades, setTrades] = useState([]);
  const [form, setForm] = useState(empty);
  const [showForm, setShowForm] = useState(false);
  const [suggestion, setSuggestion] = useState(null);
  const [computing, setComputing] = useState(false);
  const [breakBar, setBreakBar] = useState(null);

  const load = () => axios.get("/api/trades/").then(r => setTrades(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  // Look up where price first closed outside the day's own open range
  const findBreakBar = () => {
    if (!form.trade_date) return;
    setBreakBar(null);
    axios.get(`/api/outcomes/break-bar/${form.trade_date}`)
      .then(r => setBreakBar(r.data))
      .catch(e => setBreakBar({ error: e.response?.data?.detail || "Lookup failed." }));
  };

  // Compute the outcome at both 3- and 4-day holds
  const computeOutcome = () => {
    if (!form.trade_date || !form.entry_time || !form.entry_price) return;
    setComputing(true);
    setSuggestion(null);

    axios.get("/api/outcomes/compare-holds", {
      params: {
        entry_date: form.trade_date,
        entry_time: form.entry_time.length === 5 ? form.entry_time + ":00" : form.entry_time,
        entry_price: Number(form.entry_price),
        direction: form.direction,
      },
    })
      .then(r => setSuggestion(r.data))
      .catch(e => setSuggestion({ error: e.response?.data?.detail || "Computation failed." }))
      .finally(() => setComputing(false));
  };

  const acceptSuggestion = () => {
    if (!suggestion) return;
    const three = suggestion.hold_3day;
    const four = suggestion.hold_4day;
    setForm(f => ({
      ...f,
      pips_3day: three?.pips ?? "",
      pips_4day: four?.pips ?? "",
      hold_days: four?.hold_days ?? "",
    }));
  };

  const submit = () => {
    const payload = { ...form };
    ["pips_3day", "pips_4day", "hold_days", "entry_price"].forEach(k => {
      payload[k] = payload[k] === "" ? null : Number(payload[k]);
    });
    if (payload.entry_time && payload.entry_time.length === 5) {
      payload.entry_time += ":00";
    }
    axios.post("/api/trades/", payload).then(() => {
      load();
      setForm(empty);
      setSuggestion(null);
      setBreakBar(null);
      setShowForm(false);
    });
  };

  const pips = trades.map(t => Number(t.pips_4day)).filter(n => !isNaN(n) && n);
  const avg = pips.length ? (pips.reduce((a, b) => a + b, 0) / pips.length).toFixed(0) : "—";
  const median = pips.length
    ? [...pips].sort((a, b) => a - b)[Math.floor(pips.length / 2)].toFixed(0)
    : "—";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1>Trade Log</h1>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Log Trade"}
        </button>
      </div>

      {trades.length > 0 && (
        <div className="stat-grid">
          <div className="stat-card">
            <div className="stat-value">{trades.length}</div>
            <div className="stat-label">Trades</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{avg}</div>
            <div className="stat-label">Avg pips (4-day)</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{median}</div>
            <div className="stat-label">Median pips</div>
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
      )}

      {showForm && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h2>1 · The day and the entry</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Date</label>
              <input type="date" value={form.trade_date}
                onChange={e => set("trade_date", e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Entry time (server)</label>
              <input type="time" value={form.entry_time}
                onChange={e => set("entry_time", e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Entry price</label>
              <input type="number" step="0.01" value={form.entry_price}
                onChange={e => set("entry_price", e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Direction</label>
              <select value={form.direction} onChange={e => set("direction", e.target.value)}>
                <option value="sell">Sell</option>
                <option value="buy">Buy</option>
              </select>
            </div>
            <div style={{ display: "flex", alignItems: "end" }}>
              <button className="btn-secondary" onClick={findBreakBar}
                disabled={!form.trade_date}>Find break bar</button>
            </div>
          </div>

          {breakBar && (
            <div style={{
              padding: "0.6rem 0.9rem", borderRadius: "8px", marginBottom: "1rem",
              background: breakBar.error || !breakBar.break_bar ? "#3b1c1c" : "#1e2235",
              fontSize: "0.85rem",
              color: breakBar.error || !breakBar.break_bar ? "#f87171" : "#94a3b8",
            }}>
              {breakBar.error ? breakBar.error
                : breakBar.break_bar
                  ? <>First close outside the open range: <strong style={{ color: "#a78bfa" }}>{breakBar.break_bar}</strong> (bar {breakBar.bar_number}) at {breakBar.close}, direction {breakBar.direction}. This is the break, not necessarily the entry.</>
                  : breakBar.message}
            </div>
          )}

          <h2>2 · Suggested outcome</h2>
          <p style={{ fontSize: "0.8rem", color: "#64748b", marginBottom: "0.6rem" }}>
            Computed from bar data. Check it against the chart before accepting —
            finding the real entry stays a judgement call.
          </p>
          <button className="btn-secondary" onClick={computeOutcome}
            disabled={computing || !form.trade_date || !form.entry_time || !form.entry_price}>
            {computing ? "Computing…" : "Compute outcome"}
          </button>

          {suggestion && !suggestion.error && (
            <div style={{ marginTop: "0.9rem" }}>
              <table style={{ marginBottom: "0.6rem" }}>
                <thead>
                  <tr><th>Hold</th><th>Pips</th><th>Extreme</th><th>Reached</th><th>Invalidated</th></tr>
                </thead>
                <tbody>
                  {[["3-day", suggestion.hold_3day], ["4-day", suggestion.hold_4day]].map(([label, s]) => (
                    <tr key={label}>
                      <td>{label}</td>
                      <td style={{ color: "#a78bfa", fontWeight: 600 }}>{s?.pips ?? "—"}</td>
                      <td>{s?.extreme?.price ?? "—"}</td>
                      <td>{s?.extreme?.date} {s?.extreme?.time}</td>
                      <td style={{ color: s?.invalidated ? "#fbbf24" : "#64748b" }}>
                        {s?.invalidated ? `yes — ${s.invalidated_at}` : "no"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button className="btn-primary" onClick={acceptSuggestion}>
                Accept into form ↓
              </button>
            </div>
          )}

          {suggestion?.error && (
            <div style={{ marginTop: "0.75rem", color: "#f87171", fontSize: "0.85rem" }}>
              {suggestion.error}
            </div>
          )}

          <h2 style={{ marginTop: "1.25rem" }}>3 · Confirm and log</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.75rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>SR reference</label>
              <input type="text" placeholder="e.g. Mar 17's 1 (4998.0)"
                value={form.sr_reference} onChange={e => set("sr_reference", e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Entry type</label>
              <select value={form.entry_type} onChange={e => set("entry_type", e.target.value)}>
                <option value="immediate">Immediate (own boundary)</option>
                <option value="watch_forward">Watch forward</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Pips 3-day</label>
              <input type="number" step="0.1" value={form.pips_3day}
                onChange={e => set("pips_3day", e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Pips 4-day</label>
              <input type="number" step="0.1" value={form.pips_4day}
                onChange={e => set("pips_4day", e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Hold days</label>
              <input type="number" value={form.hold_days}
                onChange={e => set("hold_days", e.target.value)} />
            </div>
          </div>
          <div style={{ marginTop: "0.75rem" }}>
            <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Notes</label>
            <textarea rows={2} value={form.notes} onChange={e => set("notes", e.target.value)}
              placeholder="e.g. fake-out with overthrow, reversed hard" />
          </div>
          <div style={{ marginTop: "0.9rem" }}>
            <button className="btn-primary" onClick={submit}>Save trade</button>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Date</th><th>Dir</th><th>Entry</th><th>Type</th>
            <th>SR Reference</th><th>3-day</th><th>4-day</th><th>Hold</th><th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {trades.map(t => (
            <tr key={t.id}>
              <td>{t.trade_date}</td>
              <td><span className={`badge badge-${t.direction}`}>{t.direction}</span></td>
              <td>{t.entry_time} @ {t.entry_price}</td>
              <td style={{ fontSize: "0.8rem", color: "#64748b" }}>{t.entry_type}</td>
              <td>{t.sr_reference}</td>
              <td>{t.pips_3day ?? "—"}</td>
              <td style={{ color: "#a78bfa" }}>{t.pips_4day ?? "—"}</td>
              <td>{t.hold_days ?? "—"}</td>
              <td style={{ color: "#64748b", fontSize: "0.8rem" }}>{t.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
