import { useState } from "react";
import axios from "axios";

export default function Upload() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFile = async (file) => {
    if (!file) return;
    setLoading(true);
    setStatus(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await axios.post("/api/upload/", form);
      setStatus({ ok: true, message: r.data.message });
    } catch (e) {
      setStatus({ ok: false, message: e.response?.data?.detail || "Upload failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Upload MT4 Export</h1>
      <p style={{color:"#64748b", marginBottom:"1.5rem", fontSize:"0.9rem"}}>
        Export H1 bars from MT4 → Tools → History Center → select instrument → H1 → Export.
        Upload immediately after the first 3 H1 bars close each day.
      </p>
      <div
        className="upload-zone"
        onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); }}
        onClick={() => document.getElementById("file-input").click()}
      >
        {loading ? "Processing…" : "Drag & drop your CSV here, or click to browse"}
        <input id="file-input" type="file" accept=".csv" style={{display:"none"}}
          onChange={e => handleFile(e.target.files[0])} />
      </div>
      {status && (
        <div style={{marginTop:"1rem", padding:"0.75rem 1rem", borderRadius:"8px",
          background: status.ok ? "#14532d" : "#3b1c1c",
          color: status.ok ? "#4ade80" : "#f87171"}}>
          {status.message}
        </div>
      )}
    </div>
  );
}
