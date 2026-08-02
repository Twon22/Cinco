import { useEffect, useState } from "react";
import axios from "axios";

export default function Alignments() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("pending");

  const load = (s) => axios.get(`/api/alignments/?status=${s}&limit=100`)
    .then(r => setRows(r.data)).catch(() => {});

  useEffect(() => { load(filter); }, [filter]);

  const updateStatus = (id, status) => {
    axios.patch(`/api/alignments/${id}/status?status=${status}`)
      .then(() => load(filter));
  };

  return (
    <div>
      <h1>Alignments</h1>
      <div style={{display:"flex", gap:"0.5rem", marginBottom:"1rem"}}>
        {["pending","reviewed","removed"].map(s => (
          <button key={s} className={filter === s ? "btn-primary" : "btn-secondary"}
            onClick={() => setFilter(s)}>{s}</button>
        ))}
      </div>
      <table>
        <thead>
          <tr>
            <th>Date</th><th>Day</th><th>Type</th><th>Today Level</th>
            <th>Prior Date</th><th>Prior Level</th><th>Diff</th><th>Boundary</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(a => (
            <tr key={a.id}>
              <td>{a.today_date}</td>
              <td>{new Date(a.today_date).toLocaleDateString("en",{weekday:"short"})}</td>
              <td><span className="badge badge-x">{a.match_type}</span></td>
              <td>{a.today_level} ({a.today_price})</td>
              <td>{a.prior_date}</td>
              <td>{a.prior_level} ({a.prior_price})</td>
              <td>{a.diff}</td>
              <td>{a.is_boundary_day ? "✓" : ""}</td>
              <td style={{display:"flex", gap:"0.25rem"}}>
                {a.status !== "reviewed" && (
                  <button className="btn-primary" style={{fontSize:"0.75rem",padding:"0.2rem 0.6rem"}}
                    onClick={() => updateStatus(a.id, "reviewed")}>✓</button>
                )}
                {a.status !== "removed" && (
                  <button className="btn-secondary" style={{fontSize:"0.75rem",padding:"0.2rem 0.6rem"}}
                    onClick={() => updateStatus(a.id, "removed")}>✕</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
