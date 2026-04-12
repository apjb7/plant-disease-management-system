"""
Final retry round — aggressive search for remaining papers.
Uses broader title search, Google Scholar links, and CrossRef fuzzy matching.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "research_papers"
MANIFEST_PATH = OUTPUT_DIR / "download_manifest.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


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
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        return False


def crossref_broad_search(title: str) -> dict | None:
    """Broader CrossRef search with just key words from the title."""
    # Try with a simplified title (remove common words)
    url = "https://api.crossref.org/works"
    params = {
        "query.bibliographic": title,
        "rows": 5,
        "select": "DOI,title,link"
    }
    try:
        resp = requests.get(url, params=params, headers={
            "User-Agent": "PlantDiseaseRAG/1.0 (mailto:research@example.com)"
        }, timeout=30)
        if resp.status_code != 200:
            return None
        data = resp.json()
        items = data.get("message", {}).get("items", [])
        title_lower = title.lower().strip()
        for item in items:
            for t in item.get("title", []):
                t_lower = t.lower().strip()
                words_a = set(re.findall(r'\w+', title_lower))
                words_b = set(re.findall(r'\w+', t_lower))
                if words_a and words_b:
                    overlap = len(words_a & words_b) / len(words_a | words_b)
                    if overlap > 0.5:
                        return {"doi": item.get("DOI"), "links": item.get("link", [])}
        return None
    except Exception:
        return None


def try_frontiers_pdf(doi: str, save_path: Path) -> bool:
    if "10.3389/" not in doi:
        return False
    url = f"https://www.frontiersin.org/articles/{doi}/pdf"
    return download_pdf(url, save_path)


def try_mdpi_pdf(doi: str, save_path: Path) -> bool:
    if "10.3390/" not in doi:
        return False
    try:
        resp = requests.get(f"https://doi.org/{doi}", headers=HEADERS, timeout=30, allow_redirects=True)
        if resp.status_code == 200:
            pdf_url = resp.url.rstrip("/") + "/pdf"
            return download_pdf(pdf_url, save_path)
    except:
        pass
    # Try direct MDPI PDF endpoint
    # Pattern for MDPI: 10.3390/{journal_short}/{volume}/{issue}/{article_number}
    # PDF: https://www.mdpi.com/{journal}/{volume}/{issue}/{article_number}/pdf
    parts = doi.replace("10.3390/", "").split("/")
    if len(parts) == 1:
        # Modern DOI: 10.3390/microorganisms8101463
        article_id = parts[0]
        # Try common MDPI journals
        for journal_base in ["microorganisms", "plants", "pathogens", "molecules", "agronomy"]:
            if article_id.lower().startswith(journal_base):
                # MDPI uses volume-issue-page encoding in the article ID
                remaining = article_id[len(journal_base):]
                if remaining:
                    vol = remaining[:1] if len(remaining) >= 1 else ""
                    issue = remaining[1:3] if len(remaining) >= 3 else ""
                    page = remaining[3:] if len(remaining) > 3 else ""
                    if vol and issue and page:
                        pdf_url = f"https://www.mdpi.com/{vol}/{issue}/{page}/pdf"
                        if download_pdf(pdf_url, save_path):
                            return True
    return False


def try_pmc_by_title(title: str, save_path: Path) -> bool:
    """Search PubMed Central via NCBI E-utilities by title."""
    try:
        # Search PubMed first
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pmc",
            "term": f'"{title}"[Title]',
            "retmax": 3,
            "retmode": "json"
        }
        resp = requests.get(search_url, params=params, timeout=20)
        if resp.status_code != 200:
            return False
        
        data = resp.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        
        for pmcid in ids:
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/pdf/"
            if download_pdf(pdf_url, save_path):
                return True
    except Exception:
        pass
    return False


def try_semantic_scholar_broad(title: str, save_path: Path) -> bool:
    """Broader Semantic Scholar search."""
    try:
        # Try with shorter title (first 100 chars)
        short_title = title[:100]
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": short_title,
            "limit": 10,
            "fields": "title,openAccessPdf,isOpenAccess"
        }
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            return False
        
        data = resp.json()
        title_lower = title.lower()
        title_words = set(re.findall(r'\w+', title_lower))
        
        for paper in data.get("data", []):
            paper_title = (paper.get("title") or "").lower()
            paper_words = set(re.findall(r'\w+', paper_title))
            if title_words and paper_words:
                overlap = len(title_words & paper_words) / len(title_words)
                if overlap > 0.6:
                    oa = paper.get("openAccessPdf")
                    if oa and oa.get("url"):
                        if download_pdf(oa["url"], save_path):
                            return True
    except Exception:
        pass
    return False


def main():
    print("=" * 70)
    print("  Paper Downloader - Final Aggressive Retry")
    print("=" * 70)

    if not MANIFEST_PATH.exists():
        print("[ERROR] No manifest found.")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    papers = manifest["papers"]
    to_retry = [p for p in papers if p["status"] != "downloaded"]
    already_done = [p for p in papers if p["status"] == "downloaded"]

    print(f"\n  Already downloaded: {len(already_done)}")
    print(f"  Papers to retry:   {len(to_retry)}\n")

    new_downloads = 0

    for i, paper in enumerate(to_retry):
        title = paper["title"]
        doi = paper["doi"]
        print(f"\n  [{i+1}/{len(to_retry)}] {title[:70]}...")

        filename = sanitize_filename(title) + ".pdf"
        save_path = OUTPUT_DIR / filename
        success = False

        # Step 1: If no DOI, try CrossRef broad search
        if not doi:
            print(f"    CrossRef broad search...", end=" ")
            result = crossref_broad_search(title)
            if result and result.get("doi"):
                doi = result["doi"]
                paper["doi"] = doi
                print(f"FOUND DOI: {doi}")
            else:
                print("no DOI found")
            time.sleep(1)

        # Step 2: Try Frontiers/MDPI direct (if applicable)
        if doi and "10.3389/" in doi:
            print(f"    Frontiers direct...", end=" ")
            success = try_frontiers_pdf(doi, save_path)
            print("SUCCESS" if success else "failed")

        if not success and doi and "10.3390/" in doi:
            print(f"    MDPI direct...", end=" ")
            success = try_mdpi_pdf(doi, save_path)
            print("SUCCESS" if success else "failed")

        # Step 3: Try PubMed Central by title
        if not success:
            print(f"    PMC by title...", end=" ")
            success = try_pmc_by_title(title, save_path)
            print("SUCCESS" if success else "not found")
            time.sleep(1)

        # Step 4: Try Semantic Scholar broad
        if not success:
            print(f"    Semantic Scholar broad...", end=" ")
            success = try_semantic_scholar_broad(title, save_path)
            print("SUCCESS" if success else "not found")
            time.sleep(1)

        # Step 5: Try DOI redirect with PDF accept
        if not success and doi:
            print(f"    DOI PDF redirect...", end=" ")
            try:
                resp = requests.get(f"https://doi.org/{doi}", headers={
                    **HEADERS, "Accept": "application/pdf"
                }, timeout=30, allow_redirects=True)
                if resp.status_code == 200 and "pdf" in resp.headers.get("Content-Type", "").lower():
                    with open(save_path, "wb") as f:
                        f.write(resp.content)
                    if save_path.stat().st_size > 10000 and open(save_path, "rb").read(5) == b"%PDF-":
                        success = True
                    else:
                        save_path.unlink() if save_path.exists() else None
            except:
                pass
            print("SUCCESS" if success else "failed")

        if success:
            paper["status"] = "downloaded"
            paper["filename"] = filename
            paper["source"] = "final_retry"
            new_downloads += 1
            size = save_path.stat().st_size
            print(f"    >> Downloaded ({size / 1024:.0f} KB)")
        else:
            doi_str = f"https://doi.org/{doi}" if doi else "No DOI"
            print(f"    Still unavailable. {doi_str}")

    # Update manifest
    manifest["downloaded"] = len([p for p in papers if p["status"] == "downloaded"])
    manifest["failed"] = len([p for p in papers if p["status"] == "download_failed"])
    manifest["no_open_access"] = len([p for p in papers if p["status"] == "no_open_access_found"])

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("  FINAL RETRY SUMMARY")
    print("=" * 70)
    print(f"  New downloads this round:  {new_downloads}")
    print(f"  Total downloaded overall:  {manifest['downloaded']}")
    print(f"  Still missing:             {32 - manifest['downloaded']}")
    print("=" * 70)

    still_missing = [p for p in papers if p["status"] != "downloaded"]
    if still_missing:
        print("\n  Still requiring manual download:")
        for p in still_missing:
            doi_str = f"https://doi.org/{p['doi']}" if p["doi"] else "No DOI"
            print(f"    - {p['title'][:70]}...")
            print(f"      {doi_str}")

    print("\nDone!")


if __name__ == "__main__":
    main()
