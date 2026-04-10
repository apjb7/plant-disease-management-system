from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from app.config import BASE_DIR, UPLOADS_DIR
from app.utils import ensure_directories
from app.predictor import DiseasePredictor
from app.recommendation import RecommendationEngine
from app.pipeline import PlantDiseasePipeline
from app.logbook import save_logbook_entry, read_logbook_entries
from app.nvidia_llm_recommender import NvidiaLLMRecommender

WEB_DIR = BASE_DIR / "web"

print("BASE_DIR =", BASE_DIR)
print("WEB_DIR =", WEB_DIR)
print("INDEX PATH =", WEB_DIR / "index.html")
print("CSS PATH =", WEB_DIR / "styles.css")
print("INDEX EXISTS =", (WEB_DIR / "index.html").exists())
print("CSS EXISTS =", (WEB_DIR / "styles.css").exists())

app = Flask(
    __name__,
    static_folder=str(WEB_DIR),
    static_url_path=""
)

ensure_directories([UPLOADS_DIR])

predictor = DiseasePredictor()
recommender = RecommendationEngine()

pipeline = PlantDiseasePipeline(
    predictor=predictor,
    recommender=recommender,
    save_logs=False
)

llm_recommender = NvidiaLLMRecommender(
    "/Users/adrianpothanah/Plant_Disease_Management_System/Plant-Disease-Management-System/data/final_recommendation_knowledge_base.json"
)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def serve_index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/history")
def serve_history():
    return send_from_directory(WEB_DIR, "history.html")


@app.route("/api/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Use JPG, JPEG, or PNG."}), 400

    filename = secure_filename(file.filename)
    upload_path = UPLOADS_DIR / filename
    file.save(upload_path)

    try:
        result = pipeline.run_analysis(upload_path)

        print("RAW PIPELINE RESULT =", result)
        print("PREDICTED CLASS =", repr(result.get("predicted_class")))
        print("SEVERITY LABEL =", repr(result.get("severity_label") or result.get("severity")))

        predicted_class = result.get("predicted_class")
        severity_label = result.get("severity_label") or result.get("severity")

        llm_output = llm_recommender.generate(predicted_class, severity_label)

        research_evidence = llm_output.get("research_evidence", {})
        home_gardener_guidance = llm_output.get("home_gardener_guidance", {})

        result["research_evidence"] = research_evidence
        result["home_gardener_guidance"] = home_gardener_guidance

        result["summary"] = home_gardener_guidance.get("summary", "")
        result["what_to_do_now"] = home_gardener_guidance.get("what_to_do_now", [])
        result["monitoring"] = home_gardener_guidance.get("monitoring", [])
        result["caution"] = home_gardener_guidance.get("caution", [])
        result["follow_up"] = home_gardener_guidance.get("follow_up", "")
        result["references_used"] = research_evidence.get("references_used", [])

        print("FINAL RESULT BEFORE SAVE =", result)

        save_logbook_entry(result)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def history():
    entries = read_logbook_entries()
    entries = sorted(entries, key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify(entries)


@app.route("/outputs/<path:subpath>")
def serve_outputs(subpath):
    return send_from_directory(BASE_DIR / "outputs", subpath)


@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOADS_DIR, filename)


@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory(WEB_DIR, "manifest.json")


@app.route("/service-worker.js")
def serve_sw():
    return send_from_directory(WEB_DIR, "service-worker.js")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)