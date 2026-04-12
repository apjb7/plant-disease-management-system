/* ═══════════════════════════════════════════════════════
   PlantGuard AI — App Logic
   ═══════════════════════════════════════════════════════ */

const imageInput = document.getElementById("imageInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const statusDiv = document.getElementById("status");

const resultSection = document.getElementById("resultSection");
const emptyState = document.getElementById("emptyState");
const appGrid = document.getElementById("appGrid");

const predictedClass = document.getElementById("predictedClass");
const confidence = document.getElementById("confidence");
const severity = document.getElementById("severity");
const severityPercent = document.getElementById("severityPercent");
const top3List = document.getElementById("top3List");
const summary = document.getElementById("summary");

const treatmentList = document.getElementById("treatmentList");
const monitoringList = document.getElementById("monitoringList");
const cautionList = document.getElementById("cautionList");
const followUpText = document.getElementById("followUpText");

const researchPathogenNotes = document.getElementById("researchPathogenNotes");
const researchFindings = document.getElementById("researchFindings");
const researchActions = document.getElementById("researchActions");
const researchMonitoring = document.getElementById("researchMonitoring");
const researchCautions = document.getElementById("researchCautions");
const researchFollowUp = document.getElementById("researchFollowUp");

const uploadedPreview = document.getElementById("uploadedPreview");
const gradcamImage = document.getElementById("gradcamImage");
const affectedImage = document.getElementById("affectedImage");

// Upload zone elements
const uploadZone = document.getElementById("uploadZone");
const uploadZoneInner = document.getElementById("uploadZoneInner");
const uploadPreviewWrap = document.getElementById("uploadPreviewWrap");
const filePreviewImg = document.getElementById("filePreviewImg");
const clearPreviewBtn = document.getElementById("clearPreviewBtn");


/* ── Helpers ── */

function prettifyClassName(name) {
  if (!name) return "";
  return name
    .replace(/_/g, " ")
    .replace(/\btylcv\b/gi, "TYLCV")
    .replace(/\b([a-z])/g, (match) => match.toUpperCase());
}

function fillList(element, items) {
  if (!element) return;
  element.innerHTML = "";
  (items || []).forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function setSeverityPill(severityLabel) {
  severity.innerHTML = "";

  if (!severityLabel) {
    severity.innerHTML = '<span class="result-pill healthy">Healthy</span>';
    return;
  }

  const pill = document.createElement("span");
  pill.classList.add("result-pill");

  const label = severityLabel.toLowerCase();
  if (label === "mild") pill.classList.add("mild");
  else if (label === "moderate") pill.classList.add("moderate");
  else if (label === "severe") pill.classList.add("severe");
  else pill.classList.add("healthy");

  pill.textContent = severityLabel;
  severity.appendChild(pill);
}

function setImageFromOutputPath(imgElement, fullPath) {
  if (!imgElement) return;
  if (fullPath) {
    const rel = fullPath.split("/outputs/")[1];
    imgElement.src = `/outputs/${rel}`;
  } else {
    imgElement.removeAttribute("src");
  }
}

function showStatus(message, isLoading = false) {
  statusDiv.textContent = message;
  statusDiv.classList.remove("hidden");
  if (isLoading) {
    statusDiv.classList.add("loading");
  } else {
    statusDiv.classList.remove("loading");
  }
}


/* ── Tab System ── */

function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.dataset.tab;

      // Deactivate all
      tabBtns.forEach(b => b.classList.remove("active"));
      tabPanels.forEach(p => {
        p.classList.remove("active");
        p.style.animation = "none";
      });

      // Activate clicked
      btn.classList.add("active");
      const targetPanel = document.querySelector(`.tab-panel[data-tab="${targetTab}"]`);
      if (targetPanel) {
        targetPanel.classList.add("active");
        // Re-trigger animation
        void targetPanel.offsetWidth;
        targetPanel.style.animation = "";
      }
    });
  });
}

initTabs();


/* ── Drag & Drop Upload ── */

function showFilePreview(file) {
  filePreviewImg.src = URL.createObjectURL(file);
  uploadPreviewWrap.classList.remove("hidden");
  uploadZoneInner.style.opacity = "0";
  uploadZoneInner.style.pointerEvents = "none";
}

function clearFilePreview() {
  imageInput.value = "";
  uploadPreviewWrap.classList.add("hidden");
  uploadZoneInner.style.opacity = "";
  uploadZoneInner.style.pointerEvents = "";
  filePreviewImg.src = "";
}

// File input change
imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (file) showFilePreview(file);
});

// Clear button
clearPreviewBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  clearFilePreview();
});

// Drag events
["dragenter", "dragover"].forEach(evt => {
  uploadZone.addEventListener(evt, (e) => {
    e.preventDefault();
    uploadZone.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach(evt => {
  uploadZone.addEventListener(evt, (e) => {
    e.preventDefault();
    uploadZone.classList.remove("drag-over");
  });
});

uploadZone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    imageInput.files = dt.files;
    showFilePreview(file);
  }
});


/* ── Analyze ── */

analyzeBtn.addEventListener("click", async () => {
  const file = imageInput.files[0];

  if (!file) {
    showStatus("Please select an image first.");
    return;
  }

  showStatus("Analyzing image and preparing your care report…", true);
  resultSection.classList.add("hidden");

  const formData = new FormData();
  formData.append("image", file);

  uploadedPreview.src = URL.createObjectURL(file);

  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      showStatus(data.error || "An error occurred.");
      return;
    }

    showStatus("✓ Analysis report generated successfully.");

    // Populate results
    predictedClass.textContent = prettifyClassName(data.predicted_class);
    confidence.textContent = Number(data.confidence).toFixed(4);

    const severityLabel = data.severity_label || data.severity || null;
    setSeverityPill(severityLabel);

    if (!severityLabel) {
      severityPercent.textContent = "Not applicable";
    } else {
      severityPercent.textContent = `${Number(data.severity_percent).toFixed(2)}%`;
    }

    // Top 3
    top3List.innerHTML = "";
    (data.top3 || []).forEach(item => {
      const li = document.createElement("li");
      li.textContent = `${prettifyClassName(item.class)}: ${Number(item.confidence).toFixed(4)}`;
      top3List.appendChild(li);
    });

    // Research evidence
    const research = data.research_evidence || {};
    fillList(researchPathogenNotes, research.pathogen_notes || []);
    fillList(researchFindings, research.research_findings || []);
    fillList(researchActions, research.supported_actions || []);
    fillList(researchMonitoring, research.monitoring_points || []);
    fillList(researchCautions, research.cautions || []);
    researchFollowUp.textContent = research.follow_up || "";

    // Home gardener guidance
    const home = data.home_gardener_guidance || {};
    summary.textContent = home.summary || "";
    fillList(treatmentList, home.what_to_do_now || []);
    fillList(monitoringList, home.monitoring || []);
    fillList(cautionList, home.caution || []);
    followUpText.textContent = home.follow_up || "";

    // Visual images
    setImageFromOutputPath(gradcamImage, data.gradcam_overlay_path);
    setImageFromOutputPath(affectedImage, data.affected_overlay_path);

    // Switch to 2-column layout and show results
    if (appGrid) appGrid.classList.add("has-results");
    if (emptyState) emptyState.style.display = "none";
    resultSection.classList.remove("hidden");

    // Activate first tab
    const firstBtn = document.querySelector(".tab-btn");
    if (firstBtn) firstBtn.click();

    // Scroll to results on mobile (single-column)
    if (window.innerWidth <= 960) {
      resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

  } catch (error) {
    showStatus(`Error: ${error.message}`);
  }
});


/* ── Service Worker ── */

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js");
  });
}