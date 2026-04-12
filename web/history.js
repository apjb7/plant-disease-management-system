/* ═══════════════════════════════════════════════════════
   PlantGuard AI — Logbook Page Logic
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
  if (!label) return '<span class="severity-chip severity-healthy">Healthy</span>';
  const l = label.toLowerCase();
  let cls = "severity-low";
  if (l.includes("severe") || l.includes("high")) cls = "severity-high";
  else if (l.includes("moderate") || l.includes("medium")) cls = "severity-moderate";
  return `<span class="severity-chip ${cls}">${label}</span>`;
}

function buildListHTML(title, items, icon) {
  if (!items || items.length === 0) return "";
  const lis = items.map(i => `<li>${i}</li>`).join("");
  return `
    <div class="logbook-detail-block">
      <h4 class="detail-heading">
        ${icon || ""}
        ${title}
      </h4>
      <ul class="detail-list">${lis}</ul>
    </div>
  `;
}

function renderEntries(entries) {
  entryCount.textContent = `${entries.length} report${entries.length !== 1 ? "s" : ""}`;

  if (!entries || entries.length === 0) {
    historyContainer.innerHTML = `
      <div class="logbook-empty">
        <div class="logbook-empty-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        </div>
        <h3>No saved reports yet</h3>
        <p>Analyze a leaf on the <a href="/">Home</a> page to generate your first report.</p>
      </div>`;
    return;
  }

  historyContainer.innerHTML = entries.map((entry, idx) => {
    const uploadedPath = toWebImagePath(entry.uploaded_image_path || entry.image_path);
    const gradcamPath = toWebImagePath(entry.gradcam_overlay_path);
    const affectedPath = toWebImagePath(entry.affected_overlay_path);

    const images = [uploadedPath, gradcamPath, affectedPath].filter(Boolean);
    const imagesHTML = images.length
      ? `<div class="logbook-images">${images.map((src, i) =>
          `<div class="logbook-img-wrap"><img src="${src}" alt="Analysis image ${i + 1}" loading="lazy" /></div>`
        ).join("")}</div>`
      : "";

    const conf = Number(entry.confidence || 0);
    const pct = Number(entry.severity_percent || 0);

    return `
      <article class="logbook-card glass-card animate-in" style="animation-delay:${idx * 0.05}s">
        <div class="logbook-card-header">
          <div class="logbook-card-title-row">
            <h3 class="logbook-disease-name">${prettifyClassName(entry.predicted_class)}</h3>
            ${severityChip(entry.severity_label)}
          </div>
          <span class="logbook-date">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            ${entry.timestamp || "Unknown date"}
          </span>
        </div>

        <div class="logbook-metrics">
          <div class="logbook-metric">
            <span class="logbook-metric-label">Confidence</span>
            <span class="logbook-metric-value">${conf.toFixed(4)}</span>
            <div class="logbook-bar"><div class="logbook-bar-fill" style="width:${(conf * 100).toFixed(1)}%"></div></div>
          </div>
          <div class="logbook-metric">
            <span class="logbook-metric-label">Affected Area</span>
            <span class="logbook-metric-value">${entry.severity_label ? pct.toFixed(2) + "%" : "N/A"}</span>
            <div class="logbook-bar"><div class="logbook-bar-fill bar-amber" style="width:${pct.toFixed(1)}%"></div></div>
          </div>
        </div>

        ${entry.summary ? `
        <div class="logbook-detail-block">
          <h4 class="detail-heading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/></svg>
            Summary
          </h4>
          <p class="detail-text">${entry.summary}</p>
        </div>` : ""}

        ${buildListHTML("What To Do Now", entry.what_to_do_now, '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>')}
        ${buildListHTML("Monitoring", entry.monitoring, '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>')}
        ${buildListHTML("Caution", entry.caution, '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>')}

        ${entry.follow_up ? `
        <div class="logbook-detail-block">
          <h4 class="detail-heading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Follow-Up
          </h4>
          <p class="detail-text">${entry.follow_up}</p>
        </div>` : ""}

        ${buildListHTML("References Used", entry.references_used, '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>')}

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
    <div class="logbook-loading">
      <div class="logbook-spinner"></div>
      <p>Loading reports...</p>
    </div>`;

  try {
    const response = await fetch("/api/history");
    const entries = await response.json();
    allEntries = entries || [];
    renderEntries(allEntries);
  } catch (error) {
    historyContainer.innerHTML = `
      <div class="logbook-empty">
        <h3>Could not load reports</h3>
        <p>${error.message}</p>
      </div>`;
  }
}

loadHistory();