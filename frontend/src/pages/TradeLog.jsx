import { useEffect, useState } from "react";
import axios from "axios";

const empty = {
  trade_date:"", entry_time:"", entry_price:"", direction:"sell",
  sr_reference:"", entry_type:"watch_forward", pips_3day:"", pips_4day:"",
  hold_days:"", notes:""
};

export default function TradeLog() {
  const [trades, setTrades] = useState([]);
  const [form, setForm] = useState(empty);
  const [showForm, setShowForm] = useState(false);

  const load = () => axios.get("/api/trades/").then(r => setTrades(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const submit = () => {
    const payload = { ...form };
    ["pips_3day","pips_4day","hold_days","entry_price"].forEach(k => {
      if (payload[k] !== "") payload[k] = Number(payload[k]);
    });
    axios.post("/api/trades/", payload).then(() => { load(); setForm(empty); setShowForm(false); });
  };

  return (
    <div>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1rem"}}>
        <h1>Trade Log</h1>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Log Trade"}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{marginBottom:"1.5rem", display:"grid", gridTemplateColumns:"1fr 1fr", gap:"0.75rem"}}>
          {[["trade_date","Date","date"],["entry_time","Entry Time","time"],
            ["entry_price","Entry Price","number"],["sr_reference","SR Reference","text"]].map(([k,l,t]) => (
            <div key={k}>
              <label style={{fontSize:"0.75rem",color:"#64748b"}}>{l}</label>
              <input type={t} value={form[k]} onChange={e => setForm({...form,[k]:e.target.value})} />
            </div>
          ))}
          <div>
            <label style={{fontSize:"0.75rem",color:"#64748b"}}>Direction</label>
            <select value={form.direction} onChange={e => setForm({...form,direction:e.target.value})}>
              <option value="sell">Sell</option><option value="buy">Buy</option>
            </select>
          </div>
          <div>
            <label style={{fontSize:"0.75rem",color:"#64748b"}}>Entry Type</label>
            <select value={form.entry_type} onChange={e => setForm({...form,entry_type:e.target.value})}>
              <option value="immediate">Immediate</option>
              <option value="watch_forward">Watch Forward</option>
            </select>
          </div>
          {[["pips_3day","Pips 3-day"],["pips_4day","Pips 4-day"],["hold_days","Hold Days"]].map(([k,l]) => (
            <div key={k}>
              <label style={{fontSize:"0.75rem",color:"#64748b"}}>{l}</label>
              <input type="number" value={form[k]} onChange={e => setForm({...form,[k]:e.target.value})} />
            </div>
          ))}
          <div style={{gridColumn:"1/-1"}}>
            <label style={{fontSize:"0.75rem",color:"#64748b"}}>Notes</label>
            <textarea rows={2} value={form.notes} onChange={e => setForm({...form,notes:e.target.value})} />
          </div>
          <div style={{gridColumn:"1/-1"}}>
            <button className="btn-primary" onClick={submit}>Save Trade</button>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr><th>Date</th><th>Dir</th><th>Entry</th><th>SR Reference</th>
            <th>3-day pips</th><th>4-day pips</th><th>Hold</th><th>Notes</th></tr>
        </thead>
        <tbody>
          {trades.map(t => (
            <tr key={t.id}>
              <td>{t.trade_date}</td>
              <td><span className={`badge badge-${t.direction}`}>{t.direction}</span></td>
              <td>{t.entry_time} @ {t.entry_price}</td>
              <td>{t.sr_reference}</td>
              <td>{t.pips_3day ?? "—"}</td>
              <td>{t.pips_4day ?? "—"}</td>
              <td>{t.hold_days ?? "—"}</td>
              <td style={{color:"#64748b",fontSize:"0.8rem"}}>{t.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
