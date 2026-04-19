import os, json, time, re, sys

OUTPUT_DIR = "culpa_reviews"
COMBINED_FILE = os.path.join(OUTPUT_DIR, "ALL_CULPA_REVIEWS.txt")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "_progress.json")
BASE_URL = "https://www.culpa.info"
MAX_PROFESSOR_ID = 5000
PAGE_DELAY = 1.5
DEBUG_FIRST_N = 5

JUNK_LINES = set([
    "culpa", "home", "search", "faq", "faqs", "submit a review",
    "log in", "sign up", "about", "departments", "professors",
    "courses", "write a review", "most agreed review",
    "most disagreed review", "back", "reviews", "all reviews",
    "sort reviews", "filter by course", "join the team",
    "admin login", "announcements", "loading",
    "admin@culpa.info", "@culpa.info", "write a review",
    "load more",
    "you need to enable javascript to run this app.",
    "you need to enable javascript to run this app"
])


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"last_id": 0, "found": 0}


def save_progress(prog):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(prog, f)


def is_junk(text):
    t = text.strip().lower()
    if t in JUNK_LINES:
        return True
    if len(t) < 2:
        return True
    if t.startswith("©"):
        return True
    return False


def find_name(lines):
    for line in lines:
        s = line.strip()
        if is_junk(s):
            continue
        if len(s) > 80:
            continue
        if s.endswith((".", "?", "!", ":")):
            continue
        words = s.split()
        if 2 <= len(words) <= 6:
            return s
    return None


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Run these first:")
        print("  python -m pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prog = load_progress()
    start = prog["last_id"] + 1

    if start > 1:
        print("Resuming from ID " + str(start) + " (" + str(prog["found"]) + " found)")

    print("Scanning IDs " + str(start) + " to " + str(MAX_PROFESSOR_ID))
    print("Debug output for first " + str(DEBUG_FIRST_N) + " pages\n")

    pages_seen = 0
    misses = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            for pid in range(start, MAX_PROFESSOR_ID + 1):
                url = BASE_URL + "/professor/" + str(pid)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=10000)
                    try:
                        page.wait_for_function(
                            "() => !document.body.innerText.includes('Loading')",
                            timeout=10000
                        )
                    except Exception:
                        pass
                    page.wait_for_timeout(2000)
                except Exception as e:
                    print("  [" + str(pid) + "] load error: " + str(e))
                    prog["last_id"] = pid
                    time.sleep(PAGE_DELAY)
                    continue

                try:
                    body = page.inner_text("body").strip()
                except Exception:
                    body = ""

                pages_seen += 1

                if pages_seen <= DEBUG_FIRST_N:
                    preview = body[:300].replace("\n", " | ")
                    print("  [" + str(pid) + "] DEBUG: " + preview)
                    print()

                if not body or len(body) < 50:
                    if pid % 50 == 0:
                        print("  [" + str(pid) + "] scanning... (" + str(prog["found"]) + " found)")
                    prog["last_id"] = pid
                    if pid % 25 == 0:
                        save_progress(prog)
                    time.sleep(PAGE_DELAY)
                    misses += 1
                    if misses > 500 and pid > 500:
                        print("  500 misses in a row, stopping.")
                        break
                    continue

                lower = body.lower()
                if "enable javascript" in lower and len(body) < 100:
                    prog["last_id"] = pid
                    time.sleep(PAGE_DELAY)
                    misses += 1
                    continue

                lines = [l.strip() for l in body.split("\n") if l.strip()]
                clean = [l for l in lines if not is_junk(l)]

                if not clean:
                    prog["last_id"] = pid
                    if pid % 25 == 0:
                        save_progress(prog)
                    time.sleep(PAGE_DELAY)
                    misses += 1
                    continue

                name = find_name(clean)

                if not name:
                    try:
                        title = page.title().strip()
                        if title.lower() not in JUNK_LINES and len(title) > 2:
                            name = title
                    except Exception:
                        pass

                if not name:
                    if pages_seen <= DEBUG_FIRST_N + 5:
                        print("  [" + str(pid) + "] no name found. Lines: " + str(clean[:5]))
                    prog["last_id"] = pid
                    time.sleep(PAGE_DELAY)
                    misses += 1
                    continue

                misses = 0
                content = "\n".join(clean)

                output = "=" * 60 + "\n"
                output += "PROFESSOR: " + name + "\n"
                output += "Source: " + url + "\n"
                output += "=" * 60 + "\n\n"
                output += content + "\n"

                safe = re.sub(r"[^a-zA-Z0-9]", "_", name)[:50].strip("_")
                fpath = os.path.join(OUTPUT_DIR, str(pid) + "_" + safe + ".txt")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(output)

                prog["found"] += 1
                print("  [" + str(pid) + "] + " + name)

                prog["last_id"] = pid
                if pid % 25 == 0:
                    save_progress(prog)

                time.sleep(PAGE_DELAY)

        except KeyboardInterrupt:
            print("\n\nStopped. Run again to resume.")

        finally:
            save_progress(prog)
            try:
                browser.close()
            except Exception:
                pass

    pfiles = sorted([
        f for f in os.listdir(OUTPUT_DIR)
        if f.endswith(".txt") and not f.startswith("_")
        and f != "ALL_CULPA_REVIEWS.txt"
    ])

    if pfiles:
        with open(COMBINED_FILE, "w", encoding="utf-8") as out:
            out.write("CULPA REVIEWS - " + str(len(pfiles)) + " professors\n")
            out.write("=" * 60 + "\n\n")
            for fn in pfiles:
                with open(os.path.join(OUTPUT_DIR, fn), "r", encoding="utf-8") as rf:
                    out.write(rf.read() + "\n\n")

        sz = os.path.getsize(COMBINED_FILE)
        s = str(round(sz / 1048576, 1)) + " MB" if sz > 1048576 else str(sz // 1024) + " KB"
        print("\nDone! " + str(len(pfiles)) + " professors saved to " + COMBINED_FILE + " (" + s + ")")
    else:
        print("\nNo professors found.")


if __name__ == "__main__":
    main()