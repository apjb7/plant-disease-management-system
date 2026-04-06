const historyContainer = document.getElementById("historyContainer");

async function loadHistory() {
  historyContainer.innerHTML = "Loading history...";

  try {
    const response = await fetch("/api/history");
    const data = await response.json();

    if (!Array.isArray(data) || data.length === 0) {
      historyContainer.innerHTML = "<p>No logbook entries yet.</p>";
      return;
    }

    historyContainer.innerHTML = "";

    data.forEach(entry => {
      const div = document.createElement("div");
      div.className = "history-item";

      div.innerHTML = `
        <p><strong>Timestamp:</strong> ${entry.timestamp || "-"}</p>
        <p><strong>Predicted class:</strong> ${entry.predicted_class || "-"}</p>
        <p><strong>Confidence:</strong> ${entry.confidence !== undefined ? Number(entry.confidence).toFixed(4) : "-"}</p>
        <p><strong>Severity:</strong> ${entry.severity_label || "Not applicable"}</p>
        <p><strong>Severity percent:</strong> ${
          entry.severity_percent !== null && entry.severity_percent !== undefined
            ? Number(entry.severity_percent).toFixed(2) + "%"
            : "Not applicable"
        }</p>
        <p><strong>Recommendation:</strong> ${entry.recommendation?.summary || "-"}</p>
      `;

      historyContainer.appendChild(div);
    });
  } catch (error) {
    historyContainer.innerHTML = `<p>Error loading history: ${error.message}</p>`;
  }
}

loadHistory();