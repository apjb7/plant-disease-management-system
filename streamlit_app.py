import streamlit as st
from pathlib import Path
import tempfile

from app.predictor import DiseasePredictor
from app.recommendation import RecommendationEngine
from app.logbook import save_logbook_entry
from app.pipeline import PlantDiseasePipeline

st.set_page_config(page_title="Plant Disease Management System", layout="wide")

@st.cache_resource
def load_system():
    predictor = DiseasePredictor()
    recommender = RecommendationEngine()
    pipeline = PlantDiseasePipeline(
        predictor=predictor,
        recommender=recommender,
        save_logs=True
    )
    return pipeline

pipeline = load_system()

st.title("Plant Disease Management System")
st.write("Upload a leaf image to analyse disease, severity, and recommendations.")

uploaded_file = st.file_uploader(
    "Upload a leaf image",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
        tmp.write(uploaded_file.read())
        temp_path = tmp.name

    result = pipeline.run_analysis(temp_path, save_log_fn=save_logbook_entry)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Prediction")
        st.write("**Predicted class:**", result["predicted_class"])
        st.write("**Confidence:**", f"{result['confidence']:.4f}")

        st.write("**Top 3 predictions:**")
        for item in result["top3"]:
            st.write(f"- {item['class']}: {item['confidence']:.4f}")

        st.subheader("Severity")
        if result["severity_label"] is None:
            st.write("Healthy class detected — severity not applicable.")
        else:
            st.write("**Severity label:**", result["severity_label"])
            st.write("**Severity percent:**", f"{result['severity_percent']:.2f}%")

    with col2:
        st.subheader("Recommendation")
        rec = result["recommendation"]
        st.write("**Summary:**", rec.get("summary", ""))

        st.write("**Treatment**")
        for item in rec.get("treatment", []):
            st.write(f"- {item}")

        st.write("**Prevention**")
        for item in rec.get("prevention", []):
            st.write(f"- {item}")

        st.write("**Monitoring**")
        for item in rec.get("monitoring", []):
            st.write(f"- {item}")

        st.write("**Caution**")
        for item in rec.get("caution", []):
            st.write(f"- {item}")

    if result["gradcam_overlay_path"]:
        st.subheader("Grad-CAM")
        st.image(result["gradcam_overlay_path"], caption="Grad-CAM Overlay", use_container_width=True)

    if result["affected_overlay_path"]:
        st.subheader("Affected Area Overlay")
        st.image(result["affected_overlay_path"], caption="Affected Area Overlay", use_container_width=True)