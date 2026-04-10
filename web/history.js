const historyContainer = document.getElementById("historyContainer");

function prettifyClassName(name) {
  if (!name) return "";

  return name
    .replace(/_/g, " ")
    .replace(/\btylcv\b/gi, "TYLCV")
    .replace(/\b([a-z])/g, (match) => match.toUpperCase());
}

function createList(title, items) {
  if (!items || items.length === 0) return "";

  const liItems = items.map(item => `<li>${item}</li>`).join("");

  return `
    <div class="history-block">
      <h4>${title}</h4>
      <ul>${liItems}</ul>
    </div>
  `;
}

function createReferenceList(refs) {
  if (!refs || refs.length === 0) return "";

  const liItems = refs.map(ref => `<li>${ref}</li>`).join("");

  return `
    <div class="history-block">
      <h4>References Used</h4>
      <ul>${liItems}</ul>
    </div>
  `;
}

function toWebImagePath(pathValue) {
  if (!pathValue) return "";

  // Already a web path
  if (pathValue.startsWith("/outputs/") || pathValue.startsWith("/uploads/")) {
    return pathValue;
  }

  // Convert absolute outputs path to Flask outputs route
  if (pathValue.includes("/outputs/")) {
    const rel = pathValue.split("/outputs/")[1];
    return `/outputs/${rel}`;
  }

  // Convert absolute uploads path to Flask uploads route
  if (pathValue.includes("/uploads/")) {
    const rel = pathValue.split("/uploads/")[1];
    return `/uploads/${rel}`;
  }

  return "";
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    const entries = await response.json();

    if (!entries || entries.length === 0) {
      historyContainer.innerHTML = "<p>No saved reports yet.</p>";
      return;
    }

    historyContainer.innerHTML = entries.map(entry => {
      const uploadedImagePath = toWebImagePath(entry.uploaded_image_path || entry.image_path);
      const gradcamPath = toWebImagePath(entry.gradcam_overlay_path);
      const affectedPath = toWebImagePath(entry.affected_overlay_path);

      const uploadedImage = uploadedImagePath
        ? `<img class="history-thumb" src="${uploadedImagePath}" alt="Uploaded leaf image" />`
        : "";

      const gradcamImage = gradcamPath
        ? `<img class="history-thumb" src="${gradcamPath}" alt="Grad-CAM image" />`
        : "";

      const affectedImage = affectedPath
        ? `<img class="history-thumb" src="${affectedPath}" alt="Affected area image" />`
        : "";

      return `
        <article class="history-entry card">
          <div class="history-header">
            <div>
              <span class="section-label">Saved Report</span>
              <h3>${prettifyClassName(entry.predicted_class)}</h3>
              <p class="history-date">${entry.timestamp || ""}</p>
            </div>
          </div>

          <div class="history-summary-grid">
            <div class="metric-box">
              <span class="metric-label">Confidence</span>
              <div class="metric-value-small">${Number(entry.confidence || 0).toFixed(4)}</div>
            </div>

            <div class="metric-box">
              <span class="metric-label">Severity</span>
              <div class="metric-value-small">${entry.severity_label || "Healthy"}</div>
            </div>

            <div class="metric-box">
              <span class="metric-label">Affected area</span>
              <div class="metric-value-small">
                ${entry.severity_label ? `${Number(entry.severity_percent || 0).toFixed(2)}%` : "Not applicable"}
              </div>
            </div>
          </div>

          <div class="history-block">
            <h4>What this means</h4>
            <p>${entry.summary || "No summary available."}</p>
          </div>

          ${createList("What To Do Now", entry.what_to_do_now)}
          ${createList("Monitoring", entry.monitoring)}
          ${createList("Caution", entry.caution)}

          <div class="history-block">
            <h4>Follow-Up</h4>
            <p>${entry.follow_up || "No follow-up available."}</p>
          </div>

          ${createReferenceList(entry.references_used)}

          <div class="history-images">
            ${uploadedImage}
            ${gradcamImage}
            ${affectedImage}
          </div>
        </article>
      `;
    }).join("");
  } catch (error) {
    historyContainer.innerHTML = `<p>Error loading history: ${error.message}</p>`;
  }
}

loadHistory();