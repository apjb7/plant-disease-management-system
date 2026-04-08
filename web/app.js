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
const preventionList = document.getElementById("preventionList");
const monitoringList = document.getElementById("monitoringList");
const cautionList = document.getElementById("cautionList");

const referencesCard = document.getElementById("referencesCard");
const referencesList = document.getElementById("referencesList");

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
  element.innerHTML = "";
  (items || []).forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function fillReferences(references) {
  referencesList.innerHTML = "";

  if (!references || references.length === 0) {
    referencesCard.classList.add("hidden");
    return;
  }

  references.forEach(ref => {
    const li = document.createElement("li");
    const parts = [];
    if (ref.authors) parts.push(ref.authors);
    if (ref.year) parts.push(`(${ref.year})`);
    if (ref.title) parts.push(ref.title);
    if (ref.type) parts.push(`[${ref.type}]`);
    li.textContent = parts.join(" ");
    referencesList.appendChild(li);
  });

  referencesCard.classList.remove("hidden");
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
  referencesCard.classList.add("hidden");

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

    severity.innerHTML = "";
    if (!data.severity_label) {
      severity.innerHTML = '<span class="result-pill healthy">Healthy</span>';
      severityPercent.textContent = "Not applicable";
    } else {
      const pill = document.createElement("span");
      pill.classList.add("result-pill");

      const label = data.severity_label.toLowerCase();
      if (label === "mild") pill.classList.add("mild");
      else if (label === "moderate") pill.classList.add("moderate");
      else if (label === "severe") pill.classList.add("severe");

      pill.textContent = data.severity_label;
      severity.appendChild(pill);

      severityPercent.textContent = `${Number(data.severity_percent).toFixed(2)}%`;
    }

    top3List.innerHTML = "";
    (data.top3 || []).forEach(item => {
      const li = document.createElement("li");
      li.textContent = `${prettifyClassName(item.class)}: ${Number(item.confidence).toFixed(4)}`;
      top3List.appendChild(li);
    });

    const rec = data.recommendation || {};
    summary.textContent = rec.summary || "";

    fillList(treatmentList, rec.treatment);
    fillList(preventionList, rec.prevention);
    fillList(monitoringList, rec.monitoring);
    fillList(cautionList, rec.caution);
    fillReferences(rec.references);

    if (data.gradcam_overlay_path) {
      const rel = data.gradcam_overlay_path.split("/outputs/")[1];
      gradcamImage.src = `/outputs/${rel}`;
    } else {
      gradcamImage.removeAttribute("src");
    }

    if (data.affected_overlay_path) {
      const rel = data.affected_overlay_path.split("/outputs/")[1];
      affectedImage.src = `/outputs/${rel}`;
    } else {
      affectedImage.removeAttribute("src");
    }

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