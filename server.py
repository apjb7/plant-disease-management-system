import sys
import os

# Fix Windows console encoding — PDF text contains Unicode chars that crash cp1252
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from pathlib import Path
import json
import re
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from app.config import BASE_DIR, UPLOADS_DIR
from app.utils import ensure_directories
from app.predictor import DiseasePredictor
from app.recommendation import RecommendationEngine
from app.pipeline import PlantDiseasePipeline
from app.logbook import save_logbook_entry, read_logbook_entries
from app.rag_recommender import RAGRecommender

WEB_DIR = BASE_DIR / "web"
PAPERS_DIR = BASE_DIR / "research_papers"
CHROMA_DIR = BASE_DIR / "chroma_db"

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

llm_recommender = RAGRecommender()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def serve_index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/history")
def serve_history():
    return send_from_directory(WEB_DIR, "history.html")


@app.route("/admin")
def serve_admin():
    return send_from_directory(WEB_DIR, "admin.html")


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


# ═══════════════════════════════════════════════════════
# Admin API Endpoints
# ═══════════════════════════════════════════════════════

DISEASE_KEYWORDS = {
    "Mango_Anthracnose": [
        "anthracnose", "colletotrichum", "gloeosporioides", "mango anthracnose", "mangifera"
    ],
    "Mango_Powdery_Mildew": [
        "powdery mildew mango", "oidium mangiferae", "mango powdery", "mango mildew"
    ],
    "Pepper_Bacterial_Spot": [
        "bacterial spot pepper", "xanthomonas", "capsicum bacterial", "pepper bacterial", "vesicatoria"
    ],
    "Tomato_Leaf_Mold": [
        "leaf mold", "cladosporium fulvum", "fulvia fulva", "passalora fulva", "cf-16"
    ],
    "Tomato_Early_Blight": [
        "early blight tomato", "alternaria solani tomato", "tomato early blight"
    ],
    "Tomato_Late_Blight": [
        "late blight tomato", "phytophthora infestans tomato", "tomato late blight"
    ],
    "Tomato_Yellow_Leaf_Curl_Virus": [
        "yellow leaf curl", "tylcv", "tomato yellow", "bemisia tabaci tomato", "whitefly tomato"
    ],
    "Potato_Early_Blight": [
        "early blight potato", "alternaria solani potato", "potato early blight"
    ],
    "Potato_Late_Blight": [
        "late blight potato", "phytophthora infestans potato", "potato late blight"
    ],
}


def classify_disease_from_text(filename: str, text: str, override: str = None) -> list[str]:
    """Classify which disease class(es) a paper belongs to."""
    if override:
        return [override]

    combined = (filename + " " + text[:3000]).lower()
    matched = []
    for disease, keywords in DISEASE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score >= 2:
            matched.append(disease)

    if not matched:
        for disease, keywords in DISEASE_KEYWORDS.items():
            for kw in keywords:
                if kw in combined:
                    matched.append(disease)
                    break

    return matched if matched else ["General_Plant_Disease"]


@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    """Return system overview stats."""
    try:
        collection = llm_recommender.collection
        total_chunks = collection.count()

        # Count papers from PDF files
        pdf_files = list(PAPERS_DIR.glob("*.pdf")) if PAPERS_DIR.exists() else []

        # Get unique disease classes from metadata
        all_meta = collection.get(include=["metadatas"])
        disease_set = set()
        for m in all_meta.get("metadatas", []):
            if m and "disease_classes" in m:
                for d in m["disease_classes"].split(","):
                    d = d.strip()
                    if d:
                        disease_set.add(d)

        # Build coverage map
        coverage = {}
        for m in all_meta.get("metadatas", []):
            if m and "disease_classes" in m:
                for d in m["disease_classes"].split(","):
                    d = d.strip()
                    if d:
                        coverage[d] = coverage.get(d, 0) + 1

        return jsonify({
            "total_papers": len(pdf_files),
            "total_chunks": total_chunks,
            "disease_classes": len(disease_set),
            "embedding_model": "MiniLM-L6-v2",
            "coverage": coverage,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/papers", methods=["GET"])
def admin_papers():
    """List all ingested papers with metadata."""
    try:
        pdf_files = sorted(PAPERS_DIR.glob("*.pdf")) if PAPERS_DIR.exists() else []

        collection = llm_recommender.collection
        all_meta = collection.get(include=["metadatas"])

        # Build per-file chunk counts and disease info
        file_info = {}
        for m in all_meta.get("metadatas", []):
            if not m:
                continue
            src = m.get("source_file", "")
            if src not in file_info:
                file_info[src] = {"chunks": 0, "diseases": set()}
            file_info[src]["chunks"] += 1
            for d in m.get("disease_classes", "").split(","):
                d = d.strip()
                if d:
                    file_info[src]["diseases"].add(d)

        papers = []
        for pdf in pdf_files:
            info = file_info.get(pdf.name, {"chunks": 0, "diseases": set()})
            papers.append({
                "filename": pdf.name,
                "size_kb": round(pdf.stat().st_size / 1024),
                "chunks": info["chunks"],
                "diseases": sorted(info["diseases"]),
            })

        return jsonify(papers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/upload", methods=["POST"])
def admin_upload():
    """Upload a PDF and ingest it into ChromaDB."""
    if "pdf" not in request.files:
        return jsonify({"error": "No PDF file provided."}), 400

    file = request.files["pdf"]
    if file.filename == "" or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a valid PDF file."}), 400

    disease_override = request.form.get("disease_class", "").strip() or None

    try:
        from PyPDF2 import PdfReader
        from sentence_transformers import SentenceTransformer

        # Save the PDF
        PAPERS_DIR.mkdir(parents=True, exist_ok=True)
        filename = secure_filename(file.filename)
        save_path = PAPERS_DIR / filename
        file.save(save_path)

        # Extract text
        reader = PdfReader(str(save_path))
        raw_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                raw_text += page_text + "\n"

        if len(raw_text.strip()) < 100:
            save_path.unlink()
            return jsonify({"error": "Could not extract meaningful text from this PDF."}), 400

        # Clean text
        cleaned = re.sub(r'\s+', ' ', raw_text)
        cleaned = re.sub(r'[^\x20-\x7E\n\t]', ' ', cleaned)
        cleaned = re.sub(r' +', ' ', cleaned).strip()

        # Classify disease
        diseases = classify_disease_from_text(filename, cleaned, disease_override)

        # Chunk text (~500 words, 100 word overlap)
        words = cleaned.split()
        chunk_size, overlap = 500, 100
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            if len(chunk.strip()) > 50:
                chunks.append(chunk)
            start += chunk_size - overlap

        if not chunks:
            save_path.unlink()
            return jsonify({"error": "PDF text could not be chunked."}), 400

        # Embed chunks using the already-loaded model
        embeddings = llm_recommender.embed_model.encode(chunks, show_progress_bar=False).tolist()

        # Store in ChromaDB
        collection = llm_recommender.collection
        stem = save_path.stem[:50]
        ids = [f"{stem}_{j}" for j in range(len(chunks))]
        metadatas = [
            {
                "source_file": filename,
                "disease_classes": ",".join(diseases),
                "chunk_index": j,
                "total_chunks": len(chunks),
            }
            for j in range(len(chunks))
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        print(f"[ADMIN] Ingested {filename}: {len(chunks)} chunks, diseases={diseases}")

        return jsonify({
            "filename": filename,
            "chunks_added": len(chunks),
            "disease_classes": diseases,
            "text_length": len(cleaned),
        })

    except Exception as e:
        return jsonify({"error": f"Ingestion failed: {str(e)}"}), 500


@app.route("/api/admin/delete", methods=["POST"])
def admin_delete():
    """Remove a paper and its chunks from the system."""
    data = request.get_json()
    filename = data.get("filename", "").strip()

    if not filename:
        return jsonify({"error": "No filename provided."}), 400

    try:
        collection = llm_recommender.collection

        # Find all chunk IDs for this file
        all_data = collection.get(include=["metadatas"])
        ids_to_delete = []
        for doc_id, meta in zip(all_data["ids"], all_data["metadatas"]):
            if meta and meta.get("source_file") == filename:
                ids_to_delete.append(doc_id)

        chunks_removed = len(ids_to_delete)

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)

        # Delete PDF file
        pdf_path = PAPERS_DIR / filename
        if pdf_path.exists():
            pdf_path.unlink()

        print(f"[ADMIN] Deleted {filename}: {chunks_removed} chunks removed")

        return jsonify({
            "filename": filename,
            "chunks_removed": chunks_removed,
        })

    except Exception as e:
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)