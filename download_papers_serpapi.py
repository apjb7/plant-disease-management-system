"""
SerpAPI Google Scholar Paper Downloader
=======================================
Uses SerpAPI to search Google Scholar for the exact missing papers
and download their PDFs from the links Google Scholar provides.
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
MANIFEST_PATH = OUTPUT_DIR / "download_manifest.json"

SERPAPI_KEY = "d9db4c6cd62cb586f6a558b55bb4f33e2906069e78324fdcc1d0df2bb7e58028"
SERPAPI_URL = "https://serpapi.com/search.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# The 22 papers still missing — exact titles from Paper_related_diseases.docx
MISSING_PAPERS = [
    {
        "title": "Management of Anthracnose Disease of Mango Caused by Colletotrichum gloeosporioides: A Review",
        "authors": "Md. Nasir Uddin et al.",
        "doi": "10.22271/chemi.2020.v8.i6g.10810",
    },
    {
        "title": "Alleviating biotic stress of powdery mildew in mango cv. Keitt by sulfur nanoparticles and assessing their effect on productivity and disease severity",
        "authors": "Abou El-Nasr et al.",
        "doi": "10.21203/rs.3.rs-4824860/v1",
    },
    {
        "title": "Powdery mildew of mango in South Africa: A review",
        "authors": "Joubert, Manicom and Wingfield",
        "doi": None,
    },
    {
        "title": "A centenary for bacterial spot of tomato and pepper",
        "authors": "Osdaghi et al.",
        "doi": "10.1111/mpp.13125",
    },
    {
        "title": "Bacterial spot of tomato and pepper: diverse Xanthomonas species posing a worldwide challenge",
        "authors": "Potnis et al.",
        "doi": None,
    },
    {
        "title": "Pepper Bacterial Spot Control by Bacillus velezensis",
        "authors": "Pajcin et al.",
        "doi": "10.3390/microorganisms8101463",
    },
    {
        "title": "Exploring the Antifungal Activity of Moroccan Bacterial and Fungal Isolates and a Strobilurin Fungicide in the Control of Cladosporium fulvum, the Causal Agent of Tomato Leaf Mold Disease",
        "authors": "Belabess et al.",
        "doi": "10.3390/plants13162213",
    },
    {
        "title": "Beyond the genomes of Fulvia fulva (syn. Cladosporium fulvum) and Dothistroma septosporum: New insights into how these fungal pathogens interact with their host plants",
        "authors": "Mesarich et al.",
        "doi": "10.1111/mpp.13309",
    },
    {
        "title": "Biology, ecology, and epidemiology of Alternaria species associated with the tomato pathosystem: a review",
        "authors": "Salotti et al.",
        "doi": None,
    },
    {
        "title": "Antifungal potential of volatiles produced by Bacillus subtilis for controlling Alternaria solani causing early blight disease in tomato",
        "authors": "Awan et al.",
        "doi": None,
    },
    {
        "title": "Potato and Tomato Late Blight Caused by Phytophthora infestans: An Overview of Pathology and Resistance Breeding",
        "authors": "Nowicki et al.",
        "doi": "10.1094/pdis-05-11-0458",
    },
    {
        "title": "Integrated Disease Management of Tomato Late Blight",
        "authors": "Shrestha and Ashley",
        "doi": "10.3126/narj.v8i0.11583",
    },
    {
        "title": "Integrated Management of Tomato Yellow Leaf Curl Virus and Bemisia tabaci in Tomato Using Resistant Tomato Cultivars, Insecticides, and Mulches",
        "authors": "Riley et al.",
        "doi": None,
    },
    {
        "title": "Tomato Yellow Leaf Curl Virus-Resistant and -Susceptible Tomato Cultivars and Their Effects on Silverleaf Whitefly Population Dynamics",
        "authors": "Marchant et al.",
        "doi": None,
    },
    {
        "title": "The viral etiology of tomato yellow leaf curl disease - a review",
        "authors": "Glick et al.",
        "doi": "10.17221/26/2009-pps",
    },
    {
        "title": "A review of early blight of potato",
        "authors": "van der Waals et al.",
        "doi": None,
    },
    {
        "title": "Enhanced control efficacy of Bacillus subtilis NM4 via integration of chlorothalonil on potato early blight caused by Alternaria solani",
        "authors": "Noh et al.",
        "doi": "10.1016/j.micpath.2024.106604",
    },
    {
        "title": "Evaluation of models to control potato early blight based on field experiments in Finland, 1983-2014",
        "authors": "Abuley et al.",
        "doi": None,
    },
    {
        "title": "Five Reasons why Phytophthora infestans is the Plant Destroyer",
        "authors": "Fry et al.",
        "doi": None,
    },
    {
        "title": "Biological control of Phytophthora infestans by Bacillus strains: Antagonistic potential and mechanism of action",
        "authors": "Stefanczyk et al.",
        "doi": None,
    },
    {
        "title": "Reduced fungicide inputs for Phytophthora infestans control in potato using a decision support system",
        "authors": "Kessel et al.",
        "doi": None,
    },
    {
        "title": "Late Blight Resistance Evaluation and Genome-Wide Association Analysis in Tetraploid Potato",
        "authors": "Duan et al.",
        "doi": "10.3724/sp.j.1006.2021.04099",
    },
]


def sanitize_filename(title: str) -> str:
    clean = re.sub(r'[^\w\s-]', '', title)
    clean = re.sub(r'\s+', '_', clean.strip())
    return clean[:100]


def title_similarity(a: str, b: str) -> float:
    """Word-overlap similarity between two titles."""
    words_a = set(re.findall(r'\w+', a.lower()))
    words_b = set(re.findall(r'\w+', b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def download_pdf(url: str, save_path: Path) -> bool:
    """Download PDF and verify it's valid."""
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
        print(f"      [Download error] {e}")
        if save_path.exists():
            save_path.unlink()
        return False


def search_google_scholar(query: str, num: int = 5) -> list[dict]:
    """Search Google Scholar via SerpAPI."""
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num,
    }
    try:
        resp = requests.get(SERPAPI_URL, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"      SerpAPI HTTP {resp.status_code}")
            return []
        data = resp.json()
        return data.get("organic_results", [])
    except Exception as e:
        print(f"      [SerpAPI error] {e}")
        return []


def find_pdf_link(result: dict) -> str | None:
    """Extract PDF link from a Google Scholar result."""
    # Check for direct PDF resource links
    resources = result.get("resources", [])
    for resource in resources:
        link = resource.get("link", "")
        file_format = resource.get("file_format", "").lower()
        if "pdf" in file_format or link.endswith(".pdf"):
            return link

    # Check inline_links for related versions that might be PDFs
    inline_links = result.get("inline_links", {})
    
    # Some results have a direct link field with PDF
    link = result.get("link", "")
    if link and link.endswith(".pdf"):
        return link

    return None


def try_additional_sources(paper: dict, save_path: Path) -> tuple[bool, str]:
    """Try additional download sources for a paper."""
    doi = paper.get("doi")
    
    if not doi:
        return False, ""
    
    # Try Frontiers
    if "10.3389/" in doi:
        url = f"https://www.frontiersin.org/articles/{doi}/pdf"
        if download_pdf(url, save_path):
            return True, "frontiers_direct"
    
    # Try MDPI
    if "10.3390/" in doi:
        try:
            resp = requests.get(f"https://doi.org/{doi}", headers=HEADERS,
                              timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                pdf_url = resp.url.rstrip("/") + "/pdf"
                if download_pdf(pdf_url, save_path):
                    return True, "mdpi_direct"
        except Exception:
            pass
    
    # Try PubMed Central via DOI
    try:
        url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={doi}&format=json"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            records = resp.json().get("records", [])
            for rec in records:
                pmcid = rec.get("pmcid")
                if pmcid:
                    pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
                    if download_pdf(pmc_url, save_path):
                        return True, f"pmc_{pmcid}"
    except Exception:
        pass
    
    # Try Research Square (preprints)
    if "10.21203/" in doi:
        try:
            resp = requests.get(f"https://doi.org/{doi}", headers=HEADERS,
                              timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                # Research Square pages often have a direct PDF link
                final_url = resp.url
                if "researchsquare.com" in final_url:
                    # Try appending /v1 or direct pdf path
                    pdf_url = final_url.rstrip("/") + ".pdf"
                    if download_pdf(pdf_url, save_path):
                        return True, "research_square"
        except Exception:
            pass

    return False, ""


def main():
    print("=" * 70)
    print("  SerpAPI Google Scholar Paper Downloader")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  Total missing papers: {len(MISSING_PAPERS)}")
    print(f"  SerpAPI Key: {SERPAPI_KEY[:12]}...{SERPAPI_KEY[-6:]}")

    downloaded = 0
    failed = 0
    results_log = []

    for i, paper in enumerate(MISSING_PAPERS):
        title = paper["title"]
        authors = paper["authors"]
        doi = paper.get("doi")

        print(f"\n{'─'*70}")
        print(f"  [{i+1}/{len(MISSING_PAPERS)}] {title[:68]}...")
        print(f"  Authors: {authors}")
        if doi:
            print(f"  DOI: {doi}")

        filename = sanitize_filename(title) + ".pdf"
        save_path = OUTPUT_DIR / filename

        # Skip if already exists
        if save_path.exists() and save_path.stat().st_size > 10000:
            print(f"  >> Already exists, skipping")
            downloaded += 1
            results_log.append({**paper, "status": "already_exists", "filename": filename})
            continue

        # Strategy 1: Search Google Scholar for the exact title
        print(f"\n  [1] Searching Google Scholar for exact title...")
        # Use quotes around title for exact match
        search_query = f'"{title}"'
        results = search_google_scholar(search_query, num=3)
        time.sleep(2)  # Rate limit

        pdf_downloaded = False

        if results:
            for result in results:
                result_title = result.get("title", "")
                similarity = title_similarity(title, result_title)
                
                print(f"      Found: {result_title[:60]}... (sim={similarity:.2f})")

                if similarity < 0.4:
                    print(f"      -> Title mismatch, skipping")
                    continue

                # Try to get PDF link from the result
                pdf_link = find_pdf_link(result)
                if pdf_link:
                    print(f"      -> PDF link found: {pdf_link[:60]}...")
                    if download_pdf(pdf_link, save_path):
                        print(f"      >> SUCCESS via Google Scholar PDF ({save_path.stat().st_size / 1024:.0f} KB)")
                        pdf_downloaded = True
                        results_log.append({**paper, "status": "downloaded", "filename": filename, "source": "serpapi_scholar_pdf"})
                        break
                    else:
                        print(f"      -> PDF download failed")

                # Try the main result link (might be an OA publisher page)
                main_link = result.get("link", "")
                if main_link and not pdf_downloaded:
                    print(f"      -> Trying main link: {main_link[:60]}...")
                    if download_pdf(main_link, save_path):
                        print(f"      >> SUCCESS via main link ({save_path.stat().st_size / 1024:.0f} KB)")
                        pdf_downloaded = True
                        results_log.append({**paper, "status": "downloaded", "filename": filename, "source": "serpapi_main_link"})
                        break
        else:
            print(f"      No results found")

        # Strategy 2: Search with authors + key terms
        if not pdf_downloaded:
            print(f"\n  [2] Searching with authors + key terms...")
            author_short = authors.split(" et al")[0].split(",")[0].strip()
            search_query2 = f'{author_short} "{title[:50]}"'
            results2 = search_google_scholar(search_query2, num=3)
            time.sleep(2)

            if results2:
                for result in results2:
                    result_title = result.get("title", "")
                    similarity = title_similarity(title, result_title)
                    
                    if similarity < 0.4:
                        continue

                    pdf_link = find_pdf_link(result)
                    if pdf_link:
                        print(f"      -> PDF found: {pdf_link[:60]}...")
                        if download_pdf(pdf_link, save_path):
                            print(f"      >> SUCCESS ({save_path.stat().st_size / 1024:.0f} KB)")
                            pdf_downloaded = True
                            results_log.append({**paper, "status": "downloaded", "filename": filename, "source": "serpapi_author_search"})
                            break

                    main_link = result.get("link", "")
                    if main_link:
                        if download_pdf(main_link, save_path):
                            print(f"      >> SUCCESS via link ({save_path.stat().st_size / 1024:.0f} KB)")
                            pdf_downloaded = True
                            results_log.append({**paper, "status": "downloaded", "filename": filename, "source": "serpapi_author_link"})
                            break

        # Strategy 3: Try direct publisher/PMC sources using DOI
        if not pdf_downloaded and doi:
            print(f"\n  [3] Trying direct publisher sources...")
            success, source = try_additional_sources(paper, save_path)
            if success:
                print(f"      >> SUCCESS via {source} ({save_path.stat().st_size / 1024:.0f} KB)")
                pdf_downloaded = True
                results_log.append({**paper, "status": "downloaded", "filename": filename, "source": source})

        if pdf_downloaded:
            downloaded += 1
        else:
            failed += 1
            print(f"\n  >> FAILED - Could not find downloadable PDF")
            results_log.append({**paper, "status": "failed", "filename": None})

    # Save results
    results_manifest = {
        "total_searched": len(MISSING_PAPERS),
        "downloaded": downloaded,
        "failed": failed,
        "papers": results_log,
    }

    serpapi_manifest = OUTPUT_DIR / "serpapi_download_results.json"
    with open(serpapi_manifest, "w", encoding="utf-8") as f:
        json.dump(results_manifest, f, indent=2, ensure_ascii=False)

    # Final count
    total_pdfs = len(list(OUTPUT_DIR.glob("*.pdf")))

    print("\n" + "=" * 70)
    print("  SERPAPI DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"  Papers searched:    {len(MISSING_PAPERS)}")
    print(f"  Downloaded:         {downloaded}")
    print(f"  Failed:             {failed}")
    print(f"  Total PDFs now:     {total_pdfs}")
    print(f"  Results saved to:   {serpapi_manifest}")
    print("=" * 70)

    if failed > 0:
        print("\n  Still missing:")
        for entry in results_log:
            if entry["status"] == "failed":
                print(f"    - {entry['title'][:70]}...")

    print("\nDone!")


if __name__ == "__main__":
    main()
