"""
Columbia University Course Evaluation Bulk Downloader (PROD2 EDITION)
====================================================================
"""

import requests
import os
import sys
import time
import json
import re
from datetime import datetime

# ============================================================
# 1. CONFIGURATION & CREDENTIALS
# ============================================================

def _load_token() -> str:
    token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".columbia_token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            return f.read().strip()
    # Fallback to your proven token
    return "nd5hm6jWzxLXsGXTefrSOWSGiUde"

def _load_cookie() -> str:
    cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".columbia_cookie")
    if os.path.exists(cookie_file):
        with open(cookie_file) as f:
            return f.read().strip()
    return ""

BEARER_TOKEN = _load_token()
COOKIE = _load_cookie()
START_YEAR = int(os.environ.get("START_YEAR", "2024")) # Let's start with 2024 for quick wins
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "50"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./columbia_evals")
DELAY_BETWEEN_REQUESTS = 0.3

# ============================================================
# 2. PROVEN NETWORK SETTINGS (The "Engine")
# ============================================================

# These are the exact headers you just proved work perfectly!
VERGIL_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "authorization": f"Bearer {BEARER_TOKEN}",
    "cookie": COOKIE,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
}

PDF_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "cookie": COOKIE
}

# The proven "prod2" endpoints
COURSE_SEARCH_URL = "https://prod2-sas-studentrecords.api.columbia.edu/v1/course_and_class_search"
EVALKIT_URL = "https://prod2-sas-studentrecords.api.columbia.edu/legacy/evalkit"

# ============================================================
# 3. ID TRANSLATOR (The "Brain")
# ============================================================

def build_evalkit_candidates(course_name: str) -> list[str]:
    """Converts Vergil names (ECON UN1105) to EvalKit IDs (ECONK1105)"""
    if not course_name: return []
    # Strip spaces and non-alphanumeric chars
    clean_name = re.sub(r'[^A-Z0-9]', '', course_name.upper())
    
    m = re.match(r'^([A-Z]+)(\d+)$', clean_name)
    if not m: return [course_name]
    
    prefix, number = m.groups()
    candidates = [clean_name]
    
    # Generate K-swaps (e.g., ACTUUN -> ACTUUK -> ACTUK)
    for drop in range(1, len(prefix)):
        k_name = prefix[:len(prefix) - drop] + "K" + number
        if k_name not in candidates:
            candidates.append(k_name)
            
    return candidates

# ============================================================
# 4. CORE DOWNLOader (The "Auto" Part)
# ============================================================

def get_courses_for_term(term: str) -> list[dict]:
    all_courses = []
    page = 1
    while True:
        qs = f"term={term}&page[number]={page}&page[size]=500&page[classes.size]=500&schedule=true"
        url = f"{COURSE_SEARCH_URL}?{qs}"
        resp = requests.get(url, headers=VERGIL_HEADERS, timeout=30)
        
        if resp.status_code != 200: break
        
        data = resp.json().get("data", {})
        courses = data.get("courses", [])
        all_courses.extend(courses)
        
        if len(all_courses) >= data.get("total_count", 0) or not courses:
            break
        page += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)
    return all_courses

def get_evalkit_reports(evalkit_id: str) -> list[dict]:
    try:
        resp = requests.get(EVALKIT_URL, params={"course_id": evalkit_id}, headers=VERGIL_HEADERS, timeout=15)
        if resp.status_code == 200:
            body = resp.json()
            items = body if isinstance(body, list) else body.get("data", [])
            return [r for r in items if isinstance(r, dict) and r.get("reportLink")]
    except:
        pass
    return []

def download_pdf(url: str, filepath: str) -> bool:
    try:
        resp = requests.get(url, headers=PDF_HEADERS, timeout=30, allow_redirects=True)
        if resp.status_code == 200 and "pdf" in resp.headers.get("content-type", "").lower():
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return True
    except:
        pass
    return False

# ============================================================
# MAIN LOOP
# ============================================================

def main():
    if "--reset" in sys.argv:
        if os.path.exists("./columbia_evals/_progress.json"):
            os.remove("./columbia_evals/_progress.json")
        print("Progress reset!")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load or create progress tracking
    prog_file = os.path.join(OUTPUT_DIR, "_progress.json")
    prog = {"queried_names": [], "downloaded_urls": []}
    if os.path.exists(prog_file):
        with open(prog_file) as f:
            prog = json.load(f)

    queried_set = set(prog.get("queried_names", []))
    downloaded_set = set(prog.get("downloaded_urls", []))

    print("=" * 60)
    print(" Columbia Evaluation Downloader")
    print(f" Token:  {BEARER_TOKEN[:6]}...{BEARER_TOKEN[-4:]}")
    print("=" * 60)

    # Simple term generator (Recent first)
    terms = [f"2025{i}" for i in [1, 2, 3]] + [f"2024{i}" for i in [1, 2, 3]]
    
    all_courses_map = {}
    print("\nScanning recent terms to build course list...")
    for term in terms:
        courses = get_courses_for_term(term)
        for c in courses:
            name = c.get("course_name", "")
            title = c.get("course_official_title", "")
            if name: all_courses_map[name] = title

    new_names = [(name, title) for name, title in all_courses_map.items() if name not in queried_set]
    batch = new_names[:BATCH_SIZE]
    
    if not batch:
        print("\nAll courses queried. Run with --reset to start over.")
        return

    print(f"\nFound {len(new_names)} unchecked courses. Processing batch of {len(batch)}...\n")

    hits = 0
    all_reports = []

    for i, (cname, ctitle) in enumerate(batch):
        candidates = build_evalkit_candidates(cname)
        matched = False
        
        for candidate in candidates:
            reports = get_evalkit_reports(candidate)
            if reports:
                print(f"  [{i+1}/{len(batch)}] HIT: {cname} -> {candidate} ({len(reports)} evals)")
                for r in reports:
                    r["_cname"], r["_ctitle"] = cname, ctitle
                all_reports.extend(reports)
                matched = True
                hits += 1
                break
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        if not matched:
            print(f"  [{i+1}/{len(batch)}] MISS: {cname}")

        queried_set.add(cname)
        prog["queried_names"] = list(queried_set)
        
        # Save progress every 10 courses
        if (i+1) % 10 == 0:
            with open(prog_file, "w") as f: json.dump(prog, f)

    with open(prog_file, "w") as f: json.dump(prog, f)

    new_reports = [r for r in all_reports if r.get("reportLink") not in downloaded_set]
    
    if new_reports:
        print(f"\nDownloading {len(new_reports)} PDFs...")
        for r in new_reports:
            url = r.get("reportLink")
            course_code = r.get("courseCode", "unknown")
            prof = f"{r.get('instructorLastname', '')}_{r.get('instructorFirstname', '')}"
            filename = re.sub(r'[<>:"/\\|?*]', '_', f"{r.get('term','')}_{course_code}_{prof}.pdf")
            filepath = os.path.join(OUTPUT_DIR, filename)

            if download_pdf(url, filepath):
                print(f"  [OK] {filename}")
                downloaded_set.add(url)
                prog["downloaded_urls"] = list(downloaded_set)
                with open(prog_file, "w") as f: json.dump(prog, f)
            else:
                print(f"  [FAIL] {filename}")
            time.sleep(DELAY_BETWEEN_REQUESTS)

    print("\nBatch Complete! Run the script again to process the next batch.")

if __name__ == "__main__":
    main()