"""
Columbia College Bulletin Scraper
=================================
Scrapes all department pages from the Columbia College 2025-2026 Bulletin
and saves them as clean .txt files for use in a RAG pipeline.

Usage:
  1. pip install requests beautifulsoup4
  2. python columbia_scraper.py

Output:
  - Creates a folder called 'columbia_bulletin_data/'
  - One .txt file per department (e.g., political-science.txt)
  - One combined file: ALL_DEPARTMENTS_COMBINED.txt
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import re
import sys

BASE_URL = "https://bulletin.columbia.edu"
DEPARTMENTS_URL = f"{BASE_URL}/columbia-college/departments-instruction/"
OUTPUT_DIR = "columbia_bulletin_data"
COMBINED_FILE = os.path.join(OUTPUT_DIR, "ALL_DEPARTMENTS_COMBINED.txt")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Polite delay between requests (seconds)
REQUEST_DELAY = 1.5


def get_department_links():
    """Fetch the main departments page and extract all department URLs."""
    print("Fetching department list...")
    resp = requests.get(DEPARTMENTS_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # The department links are in the sidebar nav under /departments-instruction/
    nav = soup.find("ul", id="/columbia-college/departments-instruction/")
    if not nav:
        # Fallback: look for any nav with department links
        nav = soup.find("div", id="cl-menu")

    links = []
    if nav:
        for a_tag in nav.find_all("a", href=True):
            href = a_tag["href"]
            if "/departments-instruction/" in href and href != "/columbia-college/departments-instruction/search/":
                name = a_tag.get_text(strip=True)
                full_url = href if href.startswith("http") else BASE_URL + href
                links.append((name, full_url))

    # Deduplicate while preserving order
    seen = set()
    unique_links = []
    for name, url in links:
        if url not in seen:
            seen.add(url)
            unique_links.append((name, url))

    return unique_links


def clean_text(element):
    """Extract clean text from a BeautifulSoup element, preserving structure."""
    if element is None:
        return ""

    lines = []
    for child in element.descendants:
        if child.name in ("h1", "h2"):
            text = child.get_text(strip=True)
            if text:
                lines.append(f"\n{'=' * 60}")
                lines.append(text.upper())
                lines.append('=' * 60)
        elif child.name == "h3":
            text = child.get_text(strip=True)
            if text:
                lines.append(f"\n{'-' * 40}")
                lines.append(text)
                lines.append('-' * 40)
        elif child.name == "h4":
            text = child.get_text(strip=True)
            if text:
                lines.append(f"\n{text}")
                lines.append("~" * len(text))
        elif child.name == "p":
            text = child.get_text(strip=True)
            if text:
                lines.append(text)
                lines.append("")  # blank line after paragraphs
        elif child.name == "li" and child.parent.name in ("ul", "ol"):
            # Only process direct li children, not nested
            text = child.get_text(strip=True)
            if text and len(text) > 1:
                lines.append(f"  - {text}")
        elif child.name == "tr":
            cells = child.find_all(["td", "th"])
            if cells:
                row_text = " | ".join(c.get_text(strip=True) for c in cells if c.get_text(strip=True))
                if row_text.strip():
                    lines.append(row_text)

    # Deduplicate consecutive identical lines
    cleaned = []
    prev = None
    for line in lines:
        if line != prev:
            cleaned.append(line)
        prev = line

    return "\n".join(cleaned)


def extract_tab_content(soup, tab_id):
    """Extract content from a specific tab container."""
    container = soup.find("div", id=tab_id)
    if container:
        return clean_text(container)
    return ""


def scrape_department(name, url):
    """Scrape a single department page and return structured text."""
    print(f"  Scraping: {name}...")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    ERROR: Could not fetch {name}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Get the page title
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else name

    sections = []
    sections.append("=" * 80)
    sections.append(f"COLUMBIA COLLEGE — {title.upper()}")
    sections.append(f"2025-2026 Bulletin")
    sections.append(f"Source: {url}")
    sections.append("=" * 80)

    # The page has tabs: Overview, Faculty, Requirements, Courses
    # Their container IDs are: textcontainer, facultytextcontainer,
    # requirementstextcontainer, coursestextcontainer

    tab_ids = [
        ("OVERVIEW", "textcontainer"),
        ("FACULTY", "facultytextcontainer"),
        ("REQUIREMENTS", "requirementstextcontainer"),
        ("COURSES", "coursestextcontainer"),
    ]

    for section_name, tab_id in tab_ids:
        content = extract_tab_content(soup, tab_id)
        if content.strip():
            sections.append(f"\n{'#' * 60}")
            sections.append(f"# {section_name}")
            sections.append('#' * 60)
            sections.append(content)

    # If no tabs found, just grab the main content area
    if all(extract_tab_content(soup, tid).strip() == "" for _, tid in tab_ids):
        content_div = soup.find("div", id="content")
        if content_div:
            sections.append(clean_text(content_div))

    full_text = "\n".join(sections)

    # Clean up excessive blank lines
    full_text = re.sub(r"\n{4,}", "\n\n\n", full_text)

    return full_text


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Get all department links
    departments = get_department_links()

    if not departments:
        print("ERROR: Could not find any department links.")
        print("The website structure may have changed.")
        print("Try opening the departments page manually to check:")
        print(f"  {DEPARTMENTS_URL}")
        sys.exit(1)

    print(f"\nFound {len(departments)} departments.\n")

    # Step 2: Scrape each department
    all_content = []
    success_count = 0
    fail_count = 0

    for i, (name, url) in enumerate(departments, 1):
        print(f"[{i}/{len(departments)}]", end="")
        content = scrape_department(name, url)

        if content:
            # Save individual file
            slug = url.rstrip("/").split("/")[-1]
            filename = f"{slug}.txt"
            filepath = os.path.join(OUTPUT_DIR, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            all_content.append(content)
            success_count += 1
            print(f"    ✓ Saved: {filename}")
        else:
            fail_count += 1

        # Be polite to the server
        if i < len(departments):
            time.sleep(REQUEST_DELAY)

    # Step 3: Create combined file
    print(f"\nCreating combined file...")
    with open(COMBINED_FILE, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("COLUMBIA COLLEGE — ALL DEPARTMENTS COMBINED\n")
        f.write("2025-2026 Bulletin — Complete Academic Reference\n")
        f.write(f"Total departments: {success_count}\n")
        f.write("=" * 80 + "\n\n")

        for content in all_content:
            f.write(content)
            f.write("\n\n" + "=" * 80 + "\n\n")

    # Get file size
    combined_size = os.path.getsize(COMBINED_FILE)
    size_str = (
        f"{combined_size / (1024*1024):.1f} MB"
        if combined_size > 1024 * 1024
        else f"{combined_size / 1024:.0f} KB"
    )

    print(f"\n{'=' * 50}")
    print(f"DONE!")
    print(f"{'=' * 50}")
    print(f"  Departments scraped: {success_count}")
    print(f"  Failed:              {fail_count}")
    print(f"  Individual files:    {OUTPUT_DIR}/[department].txt")
    print(f"  Combined file:       {COMBINED_FILE} ({size_str})")
    print()
    print("NEXT STEPS:")
    print("  For RAG, you can either:")
    print("  1. Use the combined .txt file as one document")
    print("  2. Use individual .txt files (better for chunking by department)")
    print("  3. Upload to Google NotebookLM, AnythingLLM, or similar")


if __name__ == "__main__":
    main()