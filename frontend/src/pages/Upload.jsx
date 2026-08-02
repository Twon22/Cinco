import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function Upload() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleFile = async (file) => {
    if (!file) return;
    setLoading(true);
    setStatus(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const r = await axios.post("/api/upload/", form);
      setStatus({ ok: true, data: r.data });
    } catch (e) {
      setStatus({ ok: false, message: e.response?.data?.detail || "Upload failed." });
    } finally {
      setLoading(false);
    }
  };

  const d = status?.data;

  return (
    <div>
      <h1>Upload MT4 Export</h1>
      <p style={{ color: "#64748b", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
        Export H1 bars from MT4 → Tools → History Center → select instrument → H1 → Export.
        Upload immediately after the first 3 H1 bars close each day. Levels and
        alignments are recomputed automatically.
      </p>

      <div
        className="upload-zone"
        onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); }}
        onClick={() => !loading && document.getElementById("file-input").click()}
        style={loading ? { opacity: 0.6, cursor: "wait" } : {}}
      >
        {loading
          ? "Uploading and running the pipeline…"
          : "Drag & drop your CSV here, or click to browse"}
        <input id="file-input" type="file" accept=".csv" style={{ display: "none" }}
          onChange={e => handleFile(e.target.files[0])} />
      </div>

      {status && !status.ok && (
        <div style={{
          marginTop: "1rem", padding: "0.75rem 1rem", borderRadius: "8px",
          background: "#3b1c1c", color: "#f87171",
        }}>
          {status.message}
        </div>
      )}

      {status?.ok && d && (
        <div style={{ marginTop: "1.5rem" }}>
          <div style={{
            padding: "0.75rem 1rem", borderRadius: "8px",
            background: "#14532d", color: "#4ade80", marginBottom: "1.25rem",
          }}>
            {d.message} Covering {d.date_range?.from} to {d.date_range?.to}.
          </div>

          {d.pipeline && (
            <>
              <h2>Pipeline results</h2>
              <div className="stat-grid">
                <div className="stat-card">
                  <div className="stat-value">{d.pipeline.levels.computed}</div>
                  <div className="stat-label">Days computed</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{d.pipeline.levels.ties}</div>
                  <div className="stat-label">Tie days</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{d.pipeline.levels.gaps}</div>
                  <div className="stat-label">Gap days</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{d.pipeline.alignments.x_to_x}</div>
                  <div className="stat-label">x == x matches</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{d.pipeline.alignments.x_to_boundary}</div>
                  <div className="stat-label">x == boundary</div>
                </div>
              </div>

              {d.pipeline.levels.errors?.length > 0 && (
                <div className="card" style={{ marginBottom: "1rem" }}>
                  <h2 style={{ color: "#fbbf24" }}>Warnings</h2>
                  {d.pipeline.levels.errors.map((err, i) => (
                    <p key={i} style={{ fontSize: "0.8rem", color: "#94a3b8" }}>{err}</p>
                  ))}
                </div>
              )}

              <button className="btn-primary" onClick={() => navigate("/alignments")}>
                View alignments →
              </button>
            </>
          )}

          {d.pipeline_error && (
            <div style={{
              padding: "0.75rem 1rem", borderRadius: "8px",
              background: "#3b1c1c", color: "#f87171",
            }}>
              Upload succeeded but the pipeline failed: {d.pipeline_error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
