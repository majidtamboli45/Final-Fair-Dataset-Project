import React, { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [downloadReady, setDownloadReady] = useState(false);
  const [loading, setLoading] = useState(false);

  const API = process.env.REACT_APP_API_URL;

  // ================= INSPECT =================
  const handleInspect = async () => {
    if (!file) {
      alert("Please upload a file first");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);

    try {
      const res = await fetch(`${API}/inspect`, {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      if (res.ok) {
        alert(`✅ Processed!\nRows: ${data.rows}`);
        setDownloadReady(true);
      } else {
        alert(data.error);
      }
    } catch (err) {
      alert("❌ Server error");
    }

    setLoading(false);
  };

  // ================= DOWNLOAD =================
  const handleDownload = () => {
    window.open(`${API}/download`, "_blank");
  };

  return (
    <div style={container}>
      <h1 style={title}>🎬 FairAI Premium Dashboard</h1>

      <div style={card}>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
        />

        <button style={btn} onClick={handleInspect}>
          {loading ? "Processing..." : "Inspect"}
        </button>

        {downloadReady && (
          <button style={downloadBtn} onClick={handleDownload}>
            ⬇ Download Fixed Dataset
          </button>
        )}
      </div>
    </div>
  );
}

export default App;


// ================= STYLES =================

const container = {
  height: "100vh",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  background: "linear-gradient(135deg,#000000,#1c1c1c)",
  color: "white"
};

const title = {
  marginBottom: "30px"
};

const card = {
  background: "rgba(255,255,255,0.08)",
  padding: "30px",
  borderRadius: "15px",
  display: "flex",
  gap: "15px",
  alignItems: "center"
};

const btn = {
  padding: "10px 20px",
  border: "none",
  borderRadius: "8px",
  background: "#ff416c",
  color: "white",
  cursor: "pointer"
};

const downloadBtn = {
  padding: "10px 20px",
  border: "none",
  borderRadius: "8px",
  background: "#28a745",
  color: "white",
  cursor: "pointer"
};
