/**
 * Admin Portal — JavaScript
 * Manages paper uploads, library listing, stats, and coverage chart
 */

document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  loadPapers();

  // Upload button
  const uploadBtn = document.getElementById("uploadBtn");
  const pdfInput = document.getElementById("pdfInput");
  const dropZone = document.getElementById("dropZone");
  const refreshBtn = document.getElementById("refreshBtn");

  pdfInput.addEventListener("change", () => {
    uploadBtn.disabled = !pdfInput.files.length;
    if (pdfInput.files.length) {
      document.getElementById("dropLabel").textContent = pdfInput.files[0].name;
    }
  });

  // Drag-and-drop
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer.files.length && e.dataTransfer.files[0].type === "application/pdf") {
      pdfInput.files = e.dataTransfer.files;
      uploadBtn.disabled = false;
      document.getElementById("dropLabel").textContent = e.dataTransfer.files[0].name;
    }
  });

  uploadBtn.addEventListener("click", uploadPaper);
  refreshBtn.addEventListener("click", () => {
    loadStats();
    loadPapers();
  });
});


// ─── Status Helper ───────────────────────────────────
function showStatus(msg, type = "loading") {
  const el = document.getElementById("uploadStatus");
  el.className = "status-bar";
  if (type === "loading") el.classList.add("loading");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideStatus() {
  document.getElementById("uploadStatus").classList.add("hidden");
}


// ─── Upload Paper ────────────────────────────────────
async function uploadPaper() {
  const pdfInput = document.getElementById("pdfInput");
  const diseaseSelect = document.getElementById("diseaseSelect");
  const uploadBtn = document.getElementById("uploadBtn");

  if (!pdfInput.files.length) return;

  const file = pdfInput.files[0];
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showStatus("Please select a PDF file.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("pdf", file);
  if (diseaseSelect.value) {
    formData.append("disease_class", diseaseSelect.value);
  }

  uploadBtn.disabled = true;
  showStatus(`Uploading and ingesting "${file.name}"... This may take a moment.`, "loading");

  try {
    const response = await fetch("/api/admin/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (response.ok) {
      showStatus(
        `✓ Successfully ingested "${data.filename}" — ${data.chunks_added} chunks added (${data.disease_classes.join(", ")})`,
        "success"
      );
      // Reset form
      pdfInput.value = "";
      diseaseSelect.value = "";
      document.getElementById("dropLabel").textContent = "Drop PDF here or click to browse";

      // Refresh data
      loadStats();
      loadPapers();
    } else {
      showStatus(data.error || "Upload failed.", "error");
    }
  } catch (err) {
    showStatus(`Error: ${err.message}`, "error");
  }

  uploadBtn.disabled = false;
}


// ─── Load Stats ──────────────────────────────────────
async function loadStats() {
  try {
    const response = await fetch("/api/admin/stats");
    const data = await response.json();

    document.getElementById("statPapers").textContent = data.total_papers;
    document.getElementById("statChunks").textContent = data.total_chunks;
    document.getElementById("statDiseases").textContent = data.disease_classes;
    document.getElementById("statModel").textContent = data.embedding_model || "MiniLM";

    // Render coverage chart
    renderCoverageChart(data.coverage || {});
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}


// ─── Load Papers ─────────────────────────────────────
async function loadPapers() {
  const container = document.getElementById("papersList");
  container.innerHTML = '<div class="admin-loading"><div class="logbook-spinner"></div><p>Loading papers...</p></div>';

  try {
    const response = await fetch("/api/admin/papers");
    const papers = await response.json();

    if (!papers.length) {
      container.innerHTML = '<div class="empty-message">No papers ingested yet. Upload your first paper above.</div>';
      return;
    }

    container.innerHTML = papers
      .map(
        (p) => `
      <div class="paper-item">
        <div class="paper-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        </div>
        <div class="paper-info">
          <span class="paper-name" title="${escapeHtml(p.filename)}">${escapeHtml(p.filename)}</span>
          <div class="paper-meta">
            ${p.diseases.map((d) => `<span class="paper-tag tag-disease">${d.replace(/_/g, " ")}</span>`).join("")}
            <span class="paper-tag tag-chunks">${p.chunks} chunks</span>
            ${p.size_kb ? `<span class="paper-tag tag-size">${p.size_kb} KB</span>` : ""}
          </div>
        </div>
        <button class="paper-delete" onclick="deletePaper('${escapeHtml(p.filename)}')">Remove</button>
      </div>
    `
      )
      .join("");
  } catch (err) {
    container.innerHTML = `<div class="empty-message">Error loading papers: ${err.message}</div>`;
  }
}


// ─── Delete Paper ────────────────────────────────────
async function deletePaper(filename) {
  if (!confirm(`Remove "${filename}" from the knowledge base?\n\nThis will delete the PDF and remove all its chunks from ChromaDB.`)) {
    return;
  }

  try {
    const response = await fetch("/api/admin/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });

    const data = await response.json();

    if (response.ok) {
      showStatus(`✓ Removed "${filename}" — ${data.chunks_removed} chunks deleted.`, "success");
      loadStats();
      loadPapers();
    } else {
      showStatus(data.error || "Delete failed.", "error");
    }
  } catch (err) {
    showStatus(`Error: ${err.message}`, "error");
  }
}


// ─── Coverage Chart ──────────────────────────────────
function renderCoverageChart(coverage) {
  const container = document.getElementById("coverageChart");
  const entries = Object.entries(coverage).sort((a, b) => b[1] - a[1]);

  if (!entries.length) {
    container.innerHTML = '<div class="empty-message">No coverage data available.</div>';
    return;
  }

  const maxCount = Math.max(...entries.map((e) => e[1]));

  container.innerHTML = entries
    .map(
      ([disease, count]) => `
    <div class="coverage-bar-row">
      <div class="coverage-label">${disease.replace(/_/g, " ")}</div>
      <div class="coverage-bar-bg">
        <div class="coverage-bar-fill" style="width: ${(count / maxCount) * 100}%"></div>
      </div>
      <div class="coverage-count">${count}</div>
    </div>
  `
    )
    .join("");
}


// ─── Utility ─────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
