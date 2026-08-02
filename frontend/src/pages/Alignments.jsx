import { useEffect, useState } from "react";
import axios from "axios";

export default function Alignments() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [range, setRange] = useState({ min_date: null, max_date: null, total: 0 });

  const [filters, setFilters] = useState({
    status: "pending",
    match_type: "",
    start_date: "",
    end_date: "",
    boundary_only: false,
  });

  // Fetch the available date bounds once, to seed the pickers
  useEffect(() => {
    axios.get("/api/alignments/date-range")
      .then(r => {
        setRange(r.data);
        if (r.data.min_date && r.data.max_date) {
          setFilters(f => ({
            ...f,
            start_date: r.data.min_date,
            end_date: r.data.max_date,
          }));
        }
      })
      .catch(() => {});
  }, []);

  const load = () => {
    setLoading(true);
    const params = {};
    if (filters.status) params.status = filters.status;
    if (filters.match_type) params.match_type = filters.match_type;
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.boundary_only) params.boundary_only = true;

    axios.get("/api/alignments/", { params })
      .then(r => setRows(r.data))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filters]);

  const set = (key, value) => setFilters(f => ({ ...f, [key]: value }));

  const updateStatus = (id, status) => {
    axios.patch(`/api/alignments/${id}/status?status=${status}`).then(load);
  };

  const resetDates = () => {
    setFilters(f => ({
      ...f,
      start_date: range.min_date || "",
      end_date: range.max_date || "",
    }));
  };

  const xCount = rows.filter(r => r.match_type === "x==x").length;

  return (
    <div>
      <h1>Alignments</h1>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: "0.75rem",
          alignItems: "end",
        }}>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#64748b" }}>From</label>
            <input type="date" value={filters.start_date}
              min={range.min_date || undefined}
              max={range.max_date || undefined}
              onChange={e => set("start_date", e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#64748b" }}>To</label>
            <input type="date" value={filters.end_date}
              min={range.min_date || undefined}
              max={range.max_date || undefined}
              onChange={e => set("end_date", e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Match type</label>
            <select value={filters.match_type} onChange={e => set("match_type", e.target.value)}>
              <option value="">All types</option>
              <option value="x==x">x == x only</option>
              <option value="x==boundary">x == boundary</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Status</label>
            <select value={filters.status} onChange={e => set("status", e.target.value)}>
              <option value="pending">Pending</option>
              <option value="reviewed">Reviewed</option>
              <option value="removed">Removed</option>
              <option value="all">All</option>
            </select>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <label style={{
              fontSize: "0.8rem", color: "#94a3b8",
              display: "flex", alignItems: "center", gap: "0.4rem", cursor: "pointer",
            }}>
              <input type="checkbox" style={{ width: "auto" }}
                checked={filters.boundary_only}
                onChange={e => set("boundary_only", e.target.checked)} />
              Boundary only
            </label>
          </div>
          <div>
            <button className="btn-secondary" onClick={resetDates}>Reset dates</button>
          </div>
        </div>

        <div style={{
          marginTop: "0.9rem", paddingTop: "0.75rem",
          borderTop: "1px solid #2d3148",
          fontSize: "0.8rem", color: "#64748b",
        }}>
          Showing <strong style={{ color: "#a78bfa" }}>{rows.length}</strong> alignments
          {" · "}<strong style={{ color: "#d8b4fe" }}>{xCount}</strong> are x==x
          {range.min_date && (
            <> {" · "}data spans {range.min_date} to {range.max_date}</>
          )}
        </div>
      </div>

      {loading ? (
        <p style={{ color: "#64748b" }}>Loading…</p>
      ) : rows.length === 0 ? (
        <p style={{ color: "#64748b" }}>
          No alignments match these filters. Try widening the date range or switching status to "All".
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Date</th><th>Day</th><th>Type</th><th>Today Level</th>
              <th>Prior Date</th><th>Prior Level</th><th>Diff</th>
              <th>Boundary</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(a => (
              <tr key={a.id}>
                <td>{a.today_date}</td>
                <td>{new Date(a.today_date + "T12:00").toLocaleDateString("en", { weekday: "short" })}</td>
                <td>
                  <span className="badge badge-x"
                    style={a.match_type === "x==x"
                      ? {}
                      : { background: "#1e2235", color: "#94a3b8" }}>
                    {a.match_type}
                  </span>
                </td>
                <td>{a.today_level} ({a.today_price})</td>
                <td>{a.prior_date}</td>
                <td>{a.prior_level} ({a.prior_price})</td>
                <td>{a.diff}</td>
                <td>{a.is_boundary_day ? "✓" : ""}</td>
                <td style={{ display: "flex", gap: "0.25rem" }}>
                  {a.status !== "reviewed" && (
                    <button className="btn-primary"
                      style={{ fontSize: "0.75rem", padding: "0.2rem 0.6rem" }}
                      onClick={() => updateStatus(a.id, "reviewed")}>✓</button>
                  )}
                  {a.status !== "removed" && (
                    <button className="btn-secondary"
                      style={{ fontSize: "0.75rem", padding: "0.2rem 0.6rem" }}
                      onClick={() => updateStatus(a.id, "removed")}>✕</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
