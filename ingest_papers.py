"""
PDF Ingestion Pipeline — Builds ChromaDB vector store from research papers
============================================================================
Reads all PDFs from research_papers/, extracts text, chunks it,
embeds with sentence-transformers, and stores in ChromaDB.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PAPERS_DIR = BASE_DIR / "research_papers"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "plant_disease_research"

# Chunking parameters
CHUNK_SIZE = 500       # words per chunk
CHUNK_OVERLAP = 100    # overlapping words between consecutive chunks

# Disease class mapping based on keywords in paper titles/content
DISEASE_KEYWORDS = {
    "Mango_Anthracnose": [
        "anthracnose", "colletotrichum", "gloeosporioides", "mango anthracnose",
        "mangifera", "postharvest mango"
    ],
    "Mango_Powdery_Mildew": [
        "powdery mildew mango", "oidium mangiferae", "mango powdery",
        "mango mildew", "sulfur nanoparticle mango"
    ],
    "Pepper_Bacterial_Spot": [
        "bacterial spot pepper", "xanthomonas", "capsicum bacterial",
        "pepper bacterial", "vesicatoria", "bacillus pumilus pepper",
        "bs5", "bs6"
    ],
    "Tomato_Leaf_Mold": [
        "leaf mold", "cladosporium fulvum", "fulvia fulva", "passalora fulva",
        "cf-16", "tomato mold"
    ],
    "Tomato_Early_Blight": [
        "early blight tomato", "alternaria solani tomato", "trichoderma early blight",
        "tomato early blight", "alternaria tomato"
    ],
    "Tomato_Late_Blight": [
        "late blight tomato", "phytophthora infestans tomato",
        "tomato late blight", "tomato phytophthora"
    ],
    "Tomato_Yellow_Leaf_Curl_Virus": [
        "yellow leaf curl", "tylcv", "tomato yellow", "bemisia tabaci tomato",
        "whitefly tomato", "begomovirus tomato"
    ],
    "Potato_Early_Blight": [
        "early blight potato", "alternaria solani potato",
        "potato early blight", "alternaria potato"
    ],
    "Potato_Late_Blight": [
        "late blight potato", "phytophthora infestans potato",
        "potato late blight", "potato phytophthora", "potato resistance blight"
    ],
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF using PyPDF2."""
    from PyPDF2 import PdfReader
    
    try:
        reader = PdfReader(str(pdf_path))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"  [ERROR] Could not read {pdf_path.name}: {e}")
        return ""


def clean_text(text: str) -> str:
    """Clean extracted PDF text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove non-printable characters (except newlines)
    text = re.sub(r'[^\x20-\x7E\n\t]', ' ', text)
    # Remove very long strings of characters (corrupted text)
    text = re.sub(r'(\S{80,})', ' ', text)
    # Normalize whitespace
    text = re.sub(r' +', ' ', text).strip()
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    
    if len(words) <= chunk_size:
        return [text] if words else []
    
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 50:  # Minimum chunk quality
            chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks


def classify_disease(filename: str, text: str) -> list[str]:
    """Determine which disease class(es) a paper belongs to based on filename and content."""
    combined = (filename + " " + text[:3000]).lower()
    
    matched = []
    for disease, keywords in DISEASE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in combined:
                score += 1
        if score >= 2:  # Need at least 2 keyword matches
            matched.append(disease)
    
    # Fallback: if "early blight" matches both potato and tomato,
    # check more carefully
    if not matched:
        for disease, keywords in DISEASE_KEYWORDS.items():
            for kw in keywords:
                if kw in combined:
                    matched.append(disease)
                    break
    
    return matched if matched else ["General_Plant_Disease"]


def main():
    print("=" * 70)
    print("  ChromaDB Ingestion Pipeline")
    print("=" * 70)
    
    # Import here so failure messages are clearer
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    
    # 1) Load embedding model
    print("\n[1/4] Loading sentence-transformers model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"  Model loaded (dimension: {model.get_sentence_embedding_dimension()})")
    
    # 2) Initialize ChromaDB
    print("\n[2/4] Initializing ChromaDB...")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    # Delete existing collection if it exists (fresh build)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass
    
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Plant disease research papers for RAG system"}
    )
    print(f"  Created collection '{COLLECTION_NAME}'")
    
    # 3) Process PDFs
    print("\n[3/4] Processing PDFs...")
    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    print(f"  Found {len(pdf_files)} PDF files")
    
    total_chunks = 0
    ingestion_log = []
    
    for i, pdf_path in enumerate(pdf_files):
        print(f"\n  [{i+1}/{len(pdf_files)}] {pdf_path.name[:65]}...")
        
        # Extract text
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text or len(raw_text) < 100:
            print(f"    SKIP - No meaningful text extracted ({len(raw_text)} chars)")
            continue
        
        cleaned = clean_text(raw_text)
        print(f"    Extracted: {len(cleaned)} chars")
        
        # Classify disease
        diseases = classify_disease(pdf_path.stem, cleaned)
        print(f"    Diseases: {', '.join(diseases)}")
        
        # Chunk
        chunks = chunk_text(cleaned)
        print(f"    Chunks: {len(chunks)}")
        
        if not chunks:
            continue
        
        # Embed and store
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()
        
        ids = [f"{pdf_path.stem[:50]}_{j}" for j in range(len(chunks))]
        metadatas = [
            {
                "source_file": pdf_path.name,
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
        
        total_chunks += len(chunks)
        ingestion_log.append({
            "file": pdf_path.name,
            "text_length": len(cleaned),
            "chunks": len(chunks),
            "diseases": diseases,
        })
        
        print(f"    >> Stored {len(chunks)} chunks in ChromaDB")
    
    # 4) Save ingestion log
    log_path = CHROMA_DIR / "ingestion_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_pdfs_processed": len(ingestion_log),
            "total_chunks_stored": total_chunks,
            "collection_name": COLLECTION_NAME,
            "embedding_model": "all-MiniLM-L6-v2",
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "papers": ingestion_log,
        }, f, indent=2, ensure_ascii=False)
    
    # Summary
    print("\n" + "=" * 70)
    print("  INGESTION SUMMARY")
    print("=" * 70)
    print(f"  PDFs processed:    {len(ingestion_log)}")
    print(f"  Total chunks:      {total_chunks}")
    print(f"  ChromaDB path:     {CHROMA_DIR}")
    print(f"  Collection:        {COLLECTION_NAME}")
    print(f"  Embedding model:   all-MiniLM-L6-v2")
    print(f"  Ingestion log:     {log_path}")
    
    # Disease coverage
    disease_counts = {}
    for entry in ingestion_log:
        for d in entry["diseases"]:
            disease_counts[d] = disease_counts.get(d, 0) + entry["chunks"]
    
    print(f"\n  Chunks per disease class:")
    for disease, count in sorted(disease_counts.items()):
        print(f"    {disease}: {count} chunks")
    
    print("=" * 70)
    print("\nDone! ChromaDB is ready for RAG queries.")


if __name__ == "__main__":
    main()
