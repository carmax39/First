"""
Columbia Course Eval Downloader — Fast Edition (Fixed)
=======================================================
Connection pooling, dept-letter caching, no negative dept cache.
"""

import requests
import os
import sys
import time
import json
import re
from datetime import datetime


def _load_file(name):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    if os.path.exists(p):
        return open(p).read().strip()
    return ""


TOKEN = _load_file(".columbia_token")
COOKIE = _load_file(".columbia_cookie")
BATCH = int(os.environ.get("BATCH_SIZE", "2000"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./columbia_evals")
LETTERS = "WVGKBEANSDLRPOCMFTHIJQUXYZ"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "authorization": "Bearer " + TOKEN,
    "origin": "https://vergil.columbia.edu",
    "referer": "https://vergil.columbia.edu/",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
}
if COOKIE:
    HEADERS["cookie"] = COOKIE

SEARCH_URL = "https://prod2-sas-studentrecords.api.columbia.edu/v1/course_and_class_search"
EVALKIT_URL = "https://prod2-sas-studentrecords.api.columbia.edu/legacy/evalkit"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "_progress.json")
NAMES_FILE = os.path.join(OUTPUT_DIR, "_names.json")

S = requests.Session()
S.headers.update(HEADERS)


def generate_terms():
    now = datetime.now()
    cy, cm = now.year, now.month
    terms = []
    for y in range(2019, cy + 1):
        if y < cy or (y == cy and cm >= 7):
            terms.append(str(y) + "1")
        if y < cy - 1 or (y == cy - 1 and cm >= 2):
            terms.append(str(y) + "3")
    terms.reverse()
    return terms


def tname(c):
    if len(c) != 5:
        return c
    return {"1": "Spring", "2": "Summer", "3": "Fall"}.get(c[4], "?") + " " + c[:4]


def load_prog():
    if os.path.exists(PROGRESS_FILE):
        try:
            d = json.load(open(PROGRESS_FILE))
            for k in ["queried", "dl_urls", "files", "empty_terms"]:
                d.setdefault(k, [])
            d.setdefault("cache", {})
            return d
        except Exception:
            pass
    return {"queried": [], "dl_urls": [], "files": [], "empty_terms": [], "cache": {}}


def save_prog(p):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    json.dump(p, open(PROGRESS_FILE, "w"), indent=2)


def show_status():
    p = load_prog()
    c = p.get("cache", {})
    depts = {k: v for k, v in c.items() if k.startswith("d_") and v}
    print("=" * 55)
    print("  Queried:     ", len(p["queried"]))
    print("  Downloaded:  ", len(p["dl_urls"]))
    print("  Dept letters:", len(depts), "known")
    print("  Course IDs:  ", len([k for k in c if not k.startswith("d_")]))
    if depts:
        for k, v in list(depts.items())[:12]:
            print("    ", k[2:], "->", v)
    print("=" * 55)


def get_courses(term):
    all_c = []
    page = 1
    while True:
        url = (SEARCH_URL + "?term=" + term
               + "&page[number]=" + str(page)
               + "&page[size]=500&page[classes.size]=500&schedule=true")
        try:
            r = S.get(url, timeout=30)
            if r.status_code != 200:
                break
        except Exception:
            break
        data = r.json().get("data", {})
        courses = data.get("courses", [])
        total = data.get("total_count", 0)
        all_c.extend(courses)
        print(f"      page {page}: +{len(courses)} (total so far: {len(all_c)}/{total})")
        if len(all_c) >= total or not courses:
            break
        page += 1
        time.sleep(0.2)
    return all_c


def _check_evalkit(cand):
    """Returns True if evalkit has data for this candidate ID."""
    try:
        r = S.get(EVALKIT_URL, params={"course_id": cand}, timeout=10)
        body = r.json()
        items = body if isinstance(body, list) else body.get("data", [])
        return isinstance(items, list) and len(items) > 0
    except Exception:
        return False


def find_ek(dept, num, cache):
    """Find evalkit ID by trying cached dept letter, then brute-force A-Z."""
    key = dept + num
    if key in cache:
        return cache[key]

    dk = "d_" + dept

    # Try cached dept letter first (fast path)
    if dk in cache and cache[dk]:
        cand = dept + cache[dk] + num
        if _check_evalkit(cand):
            cache[key] = cand
            return cand
        # Cached letter didn't work — fall through to full brute force
        # (different courses in same dept can use different letters,
        #  e.g. ECONW1105 undergrad vs ECONG6493 graduate)

    # Brute force all 26 letters
    for letter in LETTERS:
        # Skip the letter we already tried from cache
        if dk in cache and cache[dk] == letter:
            continue
        cand = dept + letter + num
        if _check_evalkit(cand):
            cache[key] = cand
            # Update dept cache to this letter (most recent hit wins)
            cache[dk] = letter
            return cand
        time.sleep(0.05)

    # No letter worked for this specific course
    cache[key] = ""
    return ""


def get_reports(ek_id):
    try:
        r = S.get(EVALKIT_URL, params={"course_id": ek_id}, timeout=10)
        body = r.json()
        items = body if isinstance(body, list) else body.get("data", [])
        if isinstance(items, dict) or not isinstance(items, list):
            return []
        return [x for x in items if isinstance(x, dict) and x.get("reportLink")]
    except Exception:
        return []


def dl_pdf(url, fp):
    try:
        r = S.get(url, timeout=30, allow_redirects=True)
        if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
            open(fp, "wb").write(r.content)
            return True
    except Exception:
        pass
    return False


def safefn(s):
    return re.sub(r'[<>:"/\\|?*]', '_', s)[:150]


def main():
    if "--reset" in sys.argv:
        for f in [PROGRESS_FILE, NAMES_FILE]:
            if os.path.exists(f):
                os.remove(f)
        print("Reset done.")
        return
    if "--status" in sys.argv:
        show_status()
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prog = load_prog()
    queried = set(prog["queried"])
    dl_urls = set(prog["dl_urls"])
    empty = set(prog["empty_terms"])
    cache = prog.get("cache", {})

    all_terms = generate_terms()
    depts_known = len([k for k in cache if k.startswith("d_") and cache[k]])

    print("=" * 55)
    print("  Columbia Eval Downloader")
    print("=" * 55)
    print("  Batch:     ", BATCH)
    print("  Queried:   ", len(queried))
    print("  Downloaded:", len(dl_urls))
    print("  Depts:     ", depts_known, "known")
    print("=" * 55)

    # Load or build course list
    if os.path.exists(NAMES_FILE):
        names = json.load(open(NAMES_FILE))
        print("\n  Loaded", len(names), "cached names")
    else:
        to_scan = [t for t in all_terms if t not in empty]
        print("\n  Scanning", len(to_scan), "terms...")
        names = {}
        for term in to_scan:
            courses = get_courses(term)
            if not courses:
                empty.add(term)
                prog["empty_terms"] = list(empty)
                save_prog(prog)
                print("   ", tname(term) + ": 0 (skip)")
                continue
            n = 0
            for c in courses:
                nm = c.get("course_name", "")
                tt = c.get("course_official_title", "")
                if nm and nm not in names:
                    names[nm] = tt
                    if nm not in queried:
                        n += 1
            print("   ", tname(term) + ":", len(courses), "(" + str(n) + " new)")
            json.dump(names, open(NAMES_FILE, "w"))
        json.dump(names, open(NAMES_FILE, "w"))

    new = [(n, t) for n, t in names.items() if n not in queried]
    print("  Total:", len(names), " Done:", len(queried), " Left:", len(new))

    if not new:
        print("\n  All done.")
        save_prog(prog)
        return

    batch = new[:BATCH]
    print("  Batch:", len(batch), "\n")

    hits = 0
    misses = 0
    skips = 0
    dok = 0
    t0 = time.time()

    for i, (name, title) in enumerate(batch):
        m = re.match(r'^([A-Z]+?)(\d+)$', name)
        if not m:
            queried.add(name)
            skips += 1
            continue

        dept, num = m.groups()
        ek = find_ek(dept, num, cache)
        prog["cache"] = cache

        if ek:
            rpts = get_reports(ek)
            hits += 1
            print(f"  [{i+1}/{len(batch)}] HIT {name} -> {ek} ({len(rpts)} PDFs) {title[:30]}")

            for rpt in rpts:
                url = rpt["reportLink"]
                if url in dl_urls:
                    continue
                fn = safefn(
                    rpt.get("term", "") + "_"
                    + rpt.get("courseCode", "") + "_"
                    + rpt.get("instructorLastname", "")
                ) + ".pdf"
                fp = os.path.join(OUTPUT_DIR, fn)
                if os.path.exists(fp):
                    dl_urls.add(url)
                    continue
                if dl_pdf(url, fp):
                    sz = os.path.getsize(fp) // 1024
                    print(f"    [ok] {fn} ({sz} KB)")
                    dl_urls.add(url)
                    prog["files"].append(fn)
                    dok += 1
                else:
                    print(f"    [FAIL] {fn}")
                time.sleep(0.2)
        else:
            misses += 1
            if (i + 1) % 10 == 0 or misses <= 5:
                print(f"  [{i+1}/{len(batch)}] miss {name}")

        queried.add(name)
        prog["queried"] = list(queried)
        prog["dl_urls"] = list(dl_urls)

        if (i + 1) % 10 == 0:
            save_prog(prog)
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  --- {i+1}/{len(batch)} | {hits} hits | {dok} PDFs | {rate:.1f} courses/s ---")

    save_prog(prog)

    elapsed = time.time() - t0
    rem = len(new) - len(batch)
    print()
    print("=" * 55)
    print(f"  Done in {elapsed:.0f}s")
    print(f"  Hits: {hits}  Misses: {misses}  Skipped: {skips}")
    print(f"  Downloaded: {dok}")
    print(f"  Remaining: {rem}")
    if rem > 0:
        print(f"  Run again for next {min(BATCH, rem)}")
    print(f"  Output: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 55)


if __name__ == "__main__":
    main()