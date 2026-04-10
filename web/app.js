const imageInput = document.getElementById("imageInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const statusDiv = document.getElementById("status");

const resultSection = document.getElementById("resultSection");
const visualSection = document.getElementById("visualSection");

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

analyzeBtn.addEventListener("click", async () => {
  const file = imageInput.files[0];

  if (!file) {
    statusDiv.textContent = "Please select an image first.";
    return;
  }

  statusDiv.textContent = "Analyzing image and preparing your care report...";
  resultSection.classList.add("hidden");
  visualSection.classList.add("hidden");

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
      statusDiv.textContent = data.error || "An error occurred.";
      return;
    }

    statusDiv.textContent = "Analysis report generated successfully.";

    predictedClass.textContent = prettifyClassName(data.predicted_class);
    confidence.textContent = Number(data.confidence).toFixed(4);

    const severityLabel = data.severity_label || data.severity || null;
    setSeverityPill(severityLabel);

    if (!severityLabel) {
      severityPercent.textContent = "Not applicable";
    } else {
      severityPercent.textContent = `${Number(data.severity_percent).toFixed(2)}%`;
    }

    top3List.innerHTML = "";
    (data.top3 || []).forEach(item => {
      const li = document.createElement("li");
      li.textContent = `${prettifyClassName(item.class)}: ${Number(item.confidence).toFixed(4)}`;
      top3List.appendChild(li);
    });

    const research = data.research_evidence || {};
    fillList(researchPathogenNotes, research.pathogen_notes || []);
    fillList(researchFindings, research.research_findings || []);
    fillList(researchActions, research.supported_actions || []);
    fillList(researchMonitoring, research.monitoring_points || []);
    fillList(researchCautions, research.cautions || []);
    researchFollowUp.textContent = research.follow_up || "";

    const home = data.home_gardener_guidance || {};
    summary.textContent = home.summary || "";
    fillList(treatmentList, home.what_to_do_now || []);
    fillList(monitoringList, home.monitoring || []);
    fillList(cautionList, home.caution || []);
    followUpText.textContent = home.follow_up || "";

    setImageFromOutputPath(gradcamImage, data.gradcam_overlay_path);
    setImageFromOutputPath(affectedImage, data.affected_overlay_path);

    resultSection.classList.remove("hidden");
    visualSection.classList.remove("hidden");
  } catch (error) {
    statusDiv.textContent = `Error: ${error.message}`;
  }
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js");
  });
}