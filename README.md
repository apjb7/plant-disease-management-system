# 🌿 Plant Disease Management System

An AI-powered plant disease detection and management system that combines deep learning image classification, Grad-CAM visual explanations, severity analysis, and a Retrieval-Augmented Generation (RAG) pipeline backed by ChromaDB and an NVIDIA-hosted LLM to provide research-grounded, home-gardener-friendly recommendations.

---

## 🎯 Features

| Feature | Description |
|---|---|
| Disease Classification | EfficientNet-B0 model for classifying 13 plant disease and healthy classes |
| Grad-CAM Heatmaps | Visual explanation showing which leaf regions influenced the prediction |
| Severity Analysis | HSV-based leaf segmentation with heatmap overlap to estimate Mild, Moderate, or Severe cases |
| RAG Recommendations | ChromaDB vector store of peer-reviewed papers used to retrieve evidence and generate guidance |
| Admin Dashboard | Upload or delete research papers, view system stats, and manage the knowledge base |
| Scan History | Stores previous diagnoses with images, severity, and recommendations |
| Progressive Web App | Installable on mobile and supports an offline UI shell |

---

## 📁 Project Structure

```text
Plant-Disease-Management-System/
├── app/                          # Core Python modules
│   ├── config.py                 # Paths, model config, thresholds
│   ├── predictor.py              # TensorFlow model inference
│   ├── gradcam.py                # Grad-CAM heatmap generation
│   ├── severity.py               # Leaf segmentation + severity scoring
│   ├── pipeline.py               # Full analysis flow
│   ├── recommendation.py         # Static JSON-based fallback recommendations
│   ├── rag_recommender.py        # RAG pipeline: ChromaDB + LLM
│   ├── logbook.py                # Scan history persistence
│   └── utils.py                  # Image loading, resizing, saving helpers
│
├── web/                          # Frontend (HTML/CSS/JS)
│   ├── index.html                # Main diagnosis page
│   ├── styles.css                # Styles
│   ├── app.js                    # Upload and result rendering logic
│   ├── admin.html / admin.js     # Admin dashboard
│   ├── history.html / history.js # Scan history viewer
│   └── manifest.json             # PWA manifest
│
├── models_second/                # Active trained model files
│   ├── best_stage1_model_tuned.keras
│   ├── class_names_tuned.txt
│   ├── confusion_matrix.png
│   └── classification_report.txt
│
├── chroma_db/                    # Persistent ChromaDB vector store
│   ├── chroma.sqlite3
│   └── ingestion_log.json
│
├── research_papers/              # Source PDF research papers for RAG
├── data/                         # Runtime data
│   ├── recommendations.json      # Fallback recommendation file
│   └── logbook.json              # Scan history storage
│
├── unseen_test_dataset_final/    # Example unseen test images
├── server.py                     # Flask server entry point
├── streamlit_app.py              # Alternative Streamlit interface
├── ingest_papers.py              # PDF to ChromaDB ingestion pipeline
├── batch_test.py                 # Batch testing script
├── main_test.py                  # Main test runner
├── cleaning.ipynb                # Data cleaning notebook
├── cleaning2.ipynb               # Data cleaning notebook (v2)
├── training_two.ipynb            # Model training notebook
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
└── .gitignore
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or later
- `pip`
- NVIDIA API key

### 1. Clone the repository

```bash
git clone https://github.com/APJB7/Plant-Disease-Management-System.git
cd Plant-Disease-Management-System
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows**
```bash
.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`.

Example:

```env
NVIDIA_API_KEY=nvapi-YOUR_KEY_HERE
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=openai/gpt-oss-20b
```

### 5. Run the Flask server

```bash
python server.py
```

The application should be available at:

```text
http://127.0.0.1:5000
```

---

## 🧠 How the RAG System Works

The recommendation module uses Retrieval-Augmented Generation to return research-backed advice.

```text
User uploads leaf image
        ↓
EfficientNet-B0 predicts disease class
        ↓
Grad-CAM generates visual explanation
        ↓
Severity module estimates Mild / Moderate / Severe
        ↓
RAG pipeline:
  1. Build disease-aware query
  2. Embed query using sentence-transformers
  3. Retrieve top relevant chunks from ChromaDB
  4. LLM extracts structured research evidence
  5. LLM converts evidence into home-gardener guidance
        ↓
Final output returned:
prediction + confidence + severity + visuals + recommendation + references
```

---

## 📚 ChromaDB Vector Store

The project uses a local ChromaDB database to store embedded text chunks from peer-reviewed research papers.

If the pre-built vector store is already included, the recommendation module can work immediately.

To rebuild the vector store:

```bash
python ingest_papers.py
```

You can also manage papers through the Admin Dashboard.

---

## 🌱 Supported Disease Classes

| # | Class | Type |
|---|---|---|
| 1 | Mango Anthracnose | Fungal |
| 2 | Mango Powdery Mildew | Fungal |
| 3 | Mango Healthy | Healthy |
| 4 | Pepper Bacterial Spot | Bacterial |
| 5 | Pepper Healthy | Healthy |
| 6 | Tomato Early Blight | Fungal |
| 7 | Tomato Late Blight | Oomycete |
| 8 | Tomato Leaf Mold | Fungal |
| 9 | Tomato Yellow Leaf Curl Virus | Viral |
| 10 | Tomato Healthy | Healthy |
| 11 | Potato Early Blight | Fungal |
| 12 | Potato Late Blight | Oomycete |
| 13 | Potato Healthy | Healthy |

---

## 📊 Model Information

- **Architecture:** EfficientNet-B0
- **Input Size:** 300 × 300 RGB
- **Training Strategy:** Transfer learning with staged fine-tuning
- **Evaluation Files:**  
  - `models_second/classification_report.txt`  
  - `models_second/confusion_matrix.png`

---

## 🛠️ Admin Dashboard

The Admin Dashboard allows the knowledge base to be updated without changing the core system.

Main functions include:

- viewing paper and chunk statistics
- uploading new PDF papers
- deleting existing papers
- refreshing the recommendation knowledge base

Access it at:

```text
http://127.0.0.1:5000/admin
```

---

## 📖 Alternative Streamlit UI

A simpler Streamlit-based interface may also be available:

```bash
streamlit run streamlit_app.py
```

Note: this version may use the fallback recommendation method instead of the full RAG pipeline, depending on your implementation.

---

## 🔧 Troubleshooting

| Issue | Solution |
|---|---|
| `NVIDIA_API_KEY is missing` | Create a `.env` file and add your API key |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the virtual environment |
| ChromaDB collection not found | Run `python ingest_papers.py` |
| Port 5000 already in use | Change the port in `server.py` |
| Flask not found | Make sure the virtual environment is active, then install dependencies |

---

## 📄 License

This project was developed as part of an academic research project.  
Please check with the author before reuse or redistribution.

---

## 👤 Author

**Adrian Pothanah**

Academic project developed for plant disease detection, severity estimation, and research-backed plant care decision support.
