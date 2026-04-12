/* ═══════════════════════════════════════════════════════
   Plant Disease Management System — Logbook Page Logic
   ═══════════════════════════════════════════════════════ */

const historyContainer = document.getElementById("historyContainer");
const logbookSearch = document.getElementById("logbookSearch");
const entryCount = document.getElementById("entryCount");

let allEntries = [];

function prettifyClassName(name) {
  if (!name) return "";
  return name
    .replace(/_/g, " ")
    .replace(/\btylcv\b/gi, "TYLCV")
    .replace(/\b([a-z])/g, (m) => m.toUpperCase());
}

function toWebImagePath(pathValue) {
  if (!pathValue) return "";
  if (pathValue.startsWith("/outputs/") || pathValue.startsWith("/uploads/")) return pathValue;
  if (pathValue.includes("/outputs/")) return `/outputs/${pathValue.split("/outputs/")[1]}`;
  if (pathValue.includes("/uploads/")) return `/uploads/${pathValue.split("/uploads/")[1]}`;
  return "";
}

function severityChip(label) {
  if (!label) return '<span class="result-pill healthy">Healthy</span>';
  const l = label.toLowerCase();
  let cls = "mild";
  if (l.includes("severe") || l.includes("high")) cls = "severe";
  else if (l.includes("moderate") || l.includes("medium")) cls = "moderate";
  return `<span class="result-pill ${cls}">${label}</span>`;
}

function buildListHTML(title, items) {
  if (!items || items.length === 0) return "";
  const lis = items.map(i => `<li>${i}</li>`).join("");
  return `
    <div class="logbook-detail-block">
      <h4>${title}</h4>
      <ul class="action-list">${lis}</ul>
    </div>
  `;
}

function renderEntries(entries) {
  entryCount.textContent = `${entries.length} report${entries.length !== 1 ? "s" : ""}`;

  if (!entries || entries.length === 0) {
    historyContainer.innerHTML = `
      <div class="card" style="text-align:center; padding:40px 24px;">
        <h2>No saved reports yet</h2>
        <p class="subtitle">Analyze a leaf on the <a href="/">Home</a> page to generate your first report.</p>
      </div>`;
    return;
  }

  historyContainer.innerHTML = entries.map((entry) => {
    const uploadedPath = toWebImagePath(entry.uploaded_image_path || entry.image_path);
    const gradcamPath = toWebImagePath(entry.gradcam_overlay_path);
    const affectedPath = toWebImagePath(entry.affected_overlay_path);

    const images = [uploadedPath, gradcamPath, affectedPath].filter(Boolean);
    const imagesHTML = images.length
      ? `<div class="visual-grid" style="margin-top:12px">${images.map((src, i) =>
          `<div class="visual-item"><img src="${src}" alt="Analysis image ${i + 1}" loading="lazy" /></div>`
        ).join("")}</div>`
      : "";

    const conf = Number(entry.confidence || 0);
    const pct = Number(entry.severity_percent || 0);

    return `
      <article class="card">
        <div class="logbook-card-header">
          <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            <h2 style="margin-bottom:0">${prettifyClassName(entry.predicted_class)}</h2>
            ${severityChip(entry.severity_label)}
          </div>
          <span class="logbook-date">${entry.timestamp || "Unknown date"}</span>
        </div>

        <div class="metrics-row" style="margin-top:12px">
          <div class="metric">
            <span class="label">Confidence</span>
            <span class="metric-val">${conf.toFixed(4)}</span>
          </div>
          <div class="metric">
            <span class="label">Affected Area</span>
            <span class="metric-val">${entry.severity_label ? pct.toFixed(2) + "%" : "N/A"}</span>
          </div>
        </div>

        ${entry.summary ? `
        <div class="guidance-box" style="margin-top:12px">
          <span class="label">Summary</span>
          <p>${entry.summary}</p>
        </div>` : ""}

        ${buildListHTML("What To Do Now", entry.what_to_do_now)}
        ${buildListHTML("Monitoring", entry.monitoring)}
        ${buildListHTML("Caution", entry.caution)}

        ${entry.follow_up ? `
        <div class="logbook-detail-block">
          <h4>Follow-Up</h4>
          <p style="font-size:0.9rem; color:var(--gray-700)">${entry.follow_up}</p>
        </div>` : ""}

        ${buildListHTML("References Used", entry.references_used)}

        ${imagesHTML}
      </article>
    `;
  }).join("");
}

/* ── Search/filter ── */
function filterEntries() {
  const q = logbookSearch.value.toLowerCase().trim();
  if (!q) {
    renderEntries(allEntries);
    return;
  }
  const filtered = allEntries.filter(e => {
    const name = (e.predicted_class || "").toLowerCase();
    const summary = (e.summary || "").toLowerCase();
    const sev = (e.severity_label || "").toLowerCase();
    return name.includes(q) || summary.includes(q) || sev.includes(q);
  });
  renderEntries(filtered);
}

logbookSearch.addEventListener("input", filterEntries);

/* ── Load history ── */
async function loadHistory() {
  historyContainer.innerHTML = `
    <div class="card" style="text-align:center; padding:40px">
      <div class="logbook-spinner" style="margin:0 auto"></div>
      <p style="margin-top:12px; color:var(--gray-500)">Loading reports...</p>
    </div>`;

  try {
    const response = await fetch("/api/history");
    const entries = await response.json();
    allEntries = entries || [];
    renderEntries(allEntries);
  } catch (error) {
    historyContainer.innerHTML = `
      <div class="card" style="text-align:center; padding:40px">
        <h2>Could not load reports</h2>
        <p class="subtitle">${error.message}</p>
      </div>`;
  }
}

loadHistory();