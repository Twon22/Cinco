import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Alignments from "./pages/Alignments";
import Journey from "./pages/Journey";
import Calibration from "./pages/Calibration";
import TradeLog from "./pages/TradeLog";
import Upload from "./pages/Upload";
import "./index.css";

function Nav() {
  const link = ({ isActive }) => (isActive ? "nav-link active" : "nav-link");
  return (
    <nav className="navbar">
      <span className="nav-brand">Cinco</span>
      <NavLink to="/" className={link} end>Dashboard</NavLink>
      <NavLink to="/alignments" className={link}>Alignments</NavLink>
      <NavLink to="/journey" className={link}>Journey</NavLink>
      <NavLink to="/trades" className={link}>Trade Log</NavLink>
      <NavLink to="/calibration" className={link}>Calibration</NavLink>
      <NavLink to="/upload" className={link}>Upload</NavLink>
    </nav>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Nav />
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/alignments" element={<Alignments />} />
          <Route path="/journey" element={<Journey />} />
          <Route path="/trades" element={<TradeLog />} />
          <Route path="/calibration" element={<Calibration />} />
          <Route path="/upload" element={<Upload />} />
        </Routes>
      </main>
    </BrowserRouter>
  </React.StrictMode>
);
