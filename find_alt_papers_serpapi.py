"""
SerpAPI Alternative Paper Finder
=================================
Finds and downloads ALTERNATIVE open-access papers for disease topics
that are still underrepresented in the research database.
Uses Google Scholar via SerpAPI to find highly-cited OA papers.
"""

import json
import re
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "research_papers"

SERPAPI_KEY = "d9db4c6cd62cb586f6a558b55bb4f33e2906069e78324fdcc1d0df2bb7e58028"
SERPAPI_URL = "https://serpapi.com/search.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Disease topics still needing more papers, with targeted search queries
# Each query is carefully designed to find relevant, downloadable OA papers
DISEASE_QUERIES = [
    # MANGO ANTHRACNOSE — 0 papers! Critical gap
    {
        "disease": "Mango_Anthracnose",
        "query": "mango anthracnose Colletotrichum gloeosporioides disease management review",
        "needed": 3,
    },
    {
        "disease": "Mango_Anthracnose", 
        "query": "Colletotrichum mango postharvest anthracnose biological control",
        "needed": 3,
    },
    {
        "disease": "Mango_Anthracnose",
        "query": "anthracnose mango integrated disease management fungicide",
        "needed": 3,
    },
    # PEPPER BACTERIAL SPOT — 3 papers, want 1-2 more
    {
        "disease": "Pepper_Bacterial_Spot",
        "query": "pepper bacterial spot Xanthomonas disease management copper alternatives",
        "needed": 1,
    },
    # TOMATO LEAF MOLD — 2 papers, want 1 more
    {
        "disease": "Tomato_Leaf_Mold",
        "query": "tomato leaf mold Cladosporium fulvum Fulvia fulva resistance management",
        "needed": 1,
    },
    # TOMATO LATE BLIGHT — 2 papers, want 1-2 more
    {
        "disease": "Tomato_Late_Blight",
        "query": "Phytophthora infestans tomato late blight integrated management review",
        "needed": 2,
    },
    # TOMATO TYLCV — 2 papers, want 1 more
    {
        "disease": "Tomato_TYLCV",
        "query": "tomato yellow leaf curl virus TYLCV management whitefly control strategies",
        "needed": 1,
    },
    # POTATO EARLY BLIGHT — 1 paper, need 2+ more
    {
        "disease": "Potato_Early_Blight",
        "query": "potato early blight Alternaria solani management biological control review",
        "needed": 2,
    },
    {
        "disease": "Potato_Early_Blight",
        "query": "Alternaria solani potato integrated pest management fungicide resistance",
        "needed": 2,
    },
    # POTATO LATE BLIGHT — 1 paper, need 2+ more
    {
        "disease": "Potato_Late_Blight",
        "query": "potato late blight Phytophthora infestans management resistance breeding",
        "needed": 3,
    },
    {
        "disease": "Potato_Late_Blight",
        "query": "Phytophthora infestans potato biological control biocontrol agents",
        "needed": 3,
    },
    {
        "disease": "Potato_Late_Blight",
        "query": "potato late blight integrated disease management fungicide decision support",
        "needed": 3,
    },
]


def sanitize_filename(title: str) -> str:
    clean = re.sub(r'[^\w\s-]', '', title)
    clean = re.sub(r'\s+', '_', clean.strip())
    return clean[:100]


def download_pdf(url: str, save_path: Path) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True, stream=True)
        if resp.status_code != 200:
            return False
        first_bytes = b""
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if not first_bytes:
                    first_bytes = chunk[:10]
                f.write(chunk)
        if first_bytes[:5] == b"%PDF-" and save_path.stat().st_size > 10000:
            return True
        if save_path.exists():
            save_path.unlink()
        return False
    except Exception:
        if save_path.exists():
            save_path.unlink()
        return False


def is_relevant_title(title: str, disease: str) -> bool:
    """Check if the paper title is actually relevant to the disease topic."""
    title_lower = title.lower()
    
    relevance_keywords = {
        "Mango_Anthracnose": ["mango", "anthracnose", "colletotrichum", "gloeosporioides", "mangifera"],
        "Pepper_Bacterial_Spot": ["pepper", "bacterial spot", "xanthomonas", "capsicum"],
        "Tomato_Leaf_Mold": ["tomato", "leaf mold", "cladosporium", "fulvum", "fulvia"],
        "Tomato_Late_Blight": ["tomato", "late blight", "phytophthora", "infestans"],
        "Tomato_TYLCV": ["tomato", "yellow leaf curl", "tylcv", "begomovirus", "whitefly", "bemisia"],
        "Potato_Early_Blight": ["potato", "early blight", "alternaria", "solani"],
        "Potato_Late_Blight": ["potato", "late blight", "phytophthora", "infestans"],
    }
    
    keywords = relevance_keywords.get(disease, [])
    if not keywords:
        return True

    # Need at least 2 keyword matches for relevance
    matches = sum(1 for kw in keywords if kw in title_lower)
    return matches >= 2


def search_google_scholar(query: str, num: int = 10) -> list[dict]:
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num,
    }
    try:
        resp = requests.get(SERPAPI_URL, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"    SerpAPI HTTP {resp.status_code}")
            return []
        data = resp.json()
        return data.get("organic_results", [])
    except Exception as e:
        print(f"    [SerpAPI error] {e}")
        return []


def find_pdf_link(result: dict) -> str | None:
    """Extract PDF link from Google Scholar result."""
    # Direct PDF resources
    for resource in result.get("resources", []):
        link = resource.get("link", "")
        fmt = resource.get("file_format", "").lower()
        if ("pdf" in fmt or link.endswith(".pdf")) and "researchgate.net" not in link:
            return link
    
    # Check main link for direct PDF
    link = result.get("link", "")
    if link and link.endswith(".pdf"):
        return link

    return None


def try_publisher_pdf(link: str, save_path: Path) -> bool:
    """Try to get PDF from a publisher page."""
    if not link:
        return False
    
    # Frontiers articles
    if "frontiersin.org" in link:
        pdf_url = link.rstrip("/") + "/pdf" if "/pdf" not in link else link
        return download_pdf(pdf_url, save_path)
    
    # MDPI articles
    if "mdpi.com" in link:
        pdf_url = link.rstrip("/") + "/pdf" if "/pdf" not in link else link
        return download_pdf(pdf_url, save_path)
    
    # PMC articles
    if "ncbi.nlm.nih.gov/pmc" in link or "pmc.ncbi" in link:
        pdf_url = link.rstrip("/") + "/pdf/" if "/pdf" not in link else link
        return download_pdf(pdf_url, save_path)
    
    # PLoS articles
    if "plosone.org" in link or "journals.plos.org" in link:
        # Convert article URL to PDF URL
        if "id=" in link:
            pdf_url = link.replace("article?", "article/file?") + "&type=printable"
            return download_pdf(pdf_url, save_path)
    
    # Nature (some OA)
    if "nature.com" in link:
        pdf_url = link.rstrip("/") + ".pdf"
        return download_pdf(pdf_url, save_path)
    
    # Hindawi OA
    if "hindawi.com" in link:
        pdf_url = link.rstrip("/") + "/pdf"
        return download_pdf(pdf_url, save_path)

    # NepJOL
    if "nepjol.info" in link:
        return download_pdf(link, save_path)
    
    return False


def main():
    print("=" * 70)
    print("  SerpAPI Alternative Paper Finder")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Track already existing files and downloaded titles to avoid duplicates
    existing_pdfs = {f.stem.lower() for f in OUTPUT_DIR.glob("*.pdf")}
    seen_titles = set()
    
    downloaded_per_disease = {}
    alt_papers = []
    total_downloaded = 0

    for entry in DISEASE_QUERIES:
        disease = entry["disease"]
        query = entry["query"]
        needed = entry["needed"]

        current = downloaded_per_disease.get(disease, 0)
        if current >= needed:
            continue

        still_needed = needed - current
        print(f"\n{'='*70}")
        print(f"  [{disease}] Searching: {query[:55]}...")
        print(f"  Need {still_needed} more paper(s)")
        print(f"{'='*70}")

        results = search_google_scholar(query, num=10)
        time.sleep(2)  # SerpAPI rate limit

        if not results:
            print("  No results found")
            continue

        for result in results:
            if downloaded_per_disease.get(disease, 0) >= needed:
                break

            title = result.get("title", "")
            if not title:
                continue

            # Skip if title already seen or not relevant
            title_clean = re.sub(r'<[^>]+>', '', title)  # Remove HTML tags
            if title_clean.lower() in seen_titles:
                continue

            if not is_relevant_title(title_clean, disease):
                print(f"  SKIP (irrelevant): {title_clean[:60]}...")
                continue

            filename = sanitize_filename(title_clean) + ".pdf"
            if filename.lower().replace(".pdf", "") in existing_pdfs:
                print(f"  SKIP (exists): {title_clean[:60]}...")
                continue

            save_path = OUTPUT_DIR / filename
            print(f"\n  Trying: {title_clean[:65]}...")

            success = False

            # Try PDF link from Scholar
            pdf_link = find_pdf_link(result)
            if pdf_link:
                print(f"    PDF link: {pdf_link[:60]}...")
                if download_pdf(pdf_link, save_path):
                    success = True
                    print(f"    >> Downloaded ({save_path.stat().st_size / 1024:.0f} KB)")

            # Try publisher page
            if not success:
                main_link = result.get("link", "")
                if main_link:
                    print(f"    Publisher: {main_link[:60]}...")
                    if try_publisher_pdf(main_link, save_path):
                        success = True
                        print(f"    >> Downloaded ({save_path.stat().st_size / 1024:.0f} KB)")
                    elif download_pdf(main_link, save_path):
                        success = True
                        print(f"    >> Downloaded ({save_path.stat().st_size / 1024:.0f} KB)")

            if success:
                total_downloaded += 1
                downloaded_per_disease[disease] = downloaded_per_disease.get(disease, 0) + 1
                seen_titles.add(title_clean.lower())
                existing_pdfs.add(filename.lower().replace(".pdf", ""))
                alt_papers.append({
                    "title": title_clean,
                    "disease_class": disease,
                    "filename": filename,
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                })
            else:
                print(f"    >> Could not download")

            time.sleep(1)

    # Save manifest
    alt_manifest_path = OUTPUT_DIR / "serpapi_alternatives_manifest.json"
    with open(alt_manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_alternatives_downloaded": total_downloaded,
            "papers": alt_papers,
        }, f, indent=2, ensure_ascii=False)

    # Summary
    total_pdfs = len(list(OUTPUT_DIR.glob("*.pdf")))
    print("\n" + "=" * 70)
    print("  ALTERNATIVE PAPER DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"  New alternatives downloaded: {total_downloaded}")
    print(f"  Total PDFs in directory:     {total_pdfs}")
    print(f"\n  Downloads by disease:")
    for disease, count in sorted(downloaded_per_disease.items()):
        print(f"    {disease}: +{count} alternatives")
    print("=" * 70)

    if alt_papers:
        print("\n  New papers added:")
        for p in alt_papers:
            print(f"    [{p['disease_class']}] {p['title'][:60]}...")

    print("\nDone!")


if __name__ == "__main__":
    main()
