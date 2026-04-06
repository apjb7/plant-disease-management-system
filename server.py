from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from app.config import BASE_DIR, UPLOADS_DIR
from app.utils import ensure_directories
from app.predictor import DiseasePredictor
from app.recommendation import RecommendationEngine
from app.pipeline import PlantDiseasePipeline
from app.logbook import save_logbook_entry, read_logbook_entries

WEB_DIR = BASE_DIR / "web"

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
    save_logs=True
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
        result = pipeline.run_analysis(upload_path, save_log_fn=save_logbook_entry)
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
    app.run(debug=True)