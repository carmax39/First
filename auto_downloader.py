#!/usr/bin/env python3
"""
Columbia Course Evaluation PDF Downloader (Bulletproof Sweep)
========================================================
Handles Vergil's Angular SPA architecture with a sticky wait loop.
"""

import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
VERGIL_URL = "https://vergil.columbia.edu"
LINK_PATTERN = re.compile(
    r"https://arsn-columbia\.evaluationkit\.com/Report/Public/Pdf\?id=[\w\-]+",
    re.IGNORECASE,
)
OUTPUT_DIR = Path("Downloaded_Evals")
DELAY_BETWEEN_DOWNLOADS = 1      
DOWNLOAD_TIMEOUT        = 30_000 
NAV_TIMEOUT             = 60_000 

# ─────────────────────────────────────────────
# PDF Extraction & Downloading
# ─────────────────────────────────────────────
def collect_pdf_links(page) -> list[str]:
    try: anchors = page.query_selector_all("a[href]")
    except Exception: return []
    seen = set()
    links = []
    for a in anchors:
        href = a.get_attribute("href") or ""
        if not href.startswith("http"):
            href = f"https://arsn-columbia.evaluationkit.com{href}"
        if LINK_PATTERN.match(href) and href not in seen:
            seen.add(href)
            links.append(href)
    return links

def filename_from_url(url: str, index: int) -> str:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        hash_id = params.get("id", [None])[0]
        if hash_id:
            safe = re.sub(r"[^\w\-]", "_", hash_id)[:80]
            return f"eval_{safe}.pdf"
    except Exception:
        pass
    return f"eval_sweep_{int(time.time())}_{index:04d}.pdf"

def download_pdf(page, context, url: str, dest: Path, index: int, total: int):
    fname = filename_from_url(url, index)
    out_path = dest / fname

    if out_path.exists():
        print(f"      [{index}/{total}] SKIP (exists): {fname}")
        return

    print(f"      [{index}/{total}] Downloading: {fname} ...")
    new_page = context.new_page()
    try:
        with new_page.expect_download(timeout=DOWNLOAD_TIMEOUT) as dl_info:
            new_page.goto(url, timeout=DOWNLOAD_TIMEOUT, wait_until="commit")
        download = dl_info.value
        download.save_as(str(out_path))
        print(f"           Saved -> {out_path.name}")
    except PwTimeout:
        print(f"           Download event not fired — trying direct fetch ...")
        resp = new_page.request.get(url)
        if resp.ok:
            out_path.write_bytes(resp.body())
            print(f"           Saved (direct) -> {out_path.name}")
        else:
            print(f"           FAILED ({resp.status}): {url}")
    except Exception as e:
        print(f"           ERROR: {e}")
    finally:
        new_page.close()

# ─────────────────────────────────────────────
# Main Sweep Loop
# ─────────────────────────────────────────────
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 62)
    print("  Columbia Course Evaluation Downloader (Bulletproof)")
    print("=" * 62)
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(accept_downloads=True, viewport={"width": 1400, "height": 900})
        page = context.new_page()

        print(f"Opening portal: {VERGIL_URL}")
        page.goto(VERGIL_URL, timeout=NAV_TIMEOUT)

        print("-" * 62)
        print("  ACTION REQUIRED")
        print("-" * 62)
        print("  1. Log in to Vergil (SSO + 2FA).")
        print("  2. Search for a department or keyword (e.g., 'ECON').")
        print("  3. SCROLL DOWN through the results so all rows load.")
        print("  4. Come back here and press Enter to begin the sweep.\n")
        input("  Press ENTER when the course list is ready >>> ")
        print()

        # Step 3: "Sticky" Search Loop
        course_rows = None
        count = 0
        
        while True:
            selectors = [
                "mat-expansion-panel", 
                "app-course-item", 
                "div.course-item", 
                ".mat-expansion-panel"
            ]
            
            for sel in selectors:
                elements = page.locator(sel)
                if elements.count() > 0:
                    course_rows = elements
                    count = elements.count()
                    break
            
            if count > 0:
                break
                
            print("❌ Still see 0 courses. Vergil might still be loading them in the background.")
            retry = input("  Scroll down a bit more, then press ENTER to try again (or type 'q' to quit) >>> ")
            if retry.lower() == 'q':
                browser.close()
                return

        print(f"✅ Found {count} drop-down courses! Starting sweep...")

        # Step 4: The Clicking Loop
        for i in range(count):
            try:
                print(f"\n[{i+1}/{count}] Processing course...")
                panel = course_rows.nth(i)
                panel.scroll_into_view_if_needed()
                
                # Click to expand
                header = panel.locator("mat-expansion-panel-header, .panel-header").first
                if header.is_visible():
                    header.click()
                else:
                    panel.click()
                
                print("   -> Opened drop-down. Waiting for server to load evaluations...")
                
                # Look for the exact text link inside the panel
                eval_link = panel.get_by_text("Faculty Evaluations", exact=False)
                
                try:
                    eval_link.wait_for(state="visible", timeout=8000)
                    print("   -> Link loaded! Clicking...")
                    
                    with context.expect_page() as new_page_info:
                        eval_link.click()
                    eval_page = new_page_info.value
                    eval_page.wait_for_load_state("networkidle")
                    
                    links = collect_pdf_links(eval_page)
                        
                    if links:
                        print(f"   -> Found {len(links)} PDF(s). Downloading...")
                        for j, url in enumerate(links, start=1):
                            download_pdf(eval_page, context, url, OUTPUT_DIR, j, len(links))
                            if j < len(links):
                                time.sleep(DELAY_BETWEEN_DOWNLOADS)
                    else:
                        print("   -> No PDFs found on the EvaluationKit page.")
                    
                    eval_page.close()

                except PwTimeout:
                    print("   -> ⚠️ No evaluations loaded for this course (Timeout).")

                # Collapse the drop-down
                if header.is_visible():
                    header.click()
                else:
                    panel.click()
                time.sleep(0.5)

            except Exception as e:
                print(f"   -> Error processing row {i+1}: {e}")
                continue

        print("\n" + "=" * 62)
        print("  Sweep Complete! Run your extractor script next.")
        print("=" * 62)
        browser.close()

if __name__ == "__main__":
    main()