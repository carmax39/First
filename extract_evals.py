"""
Columbia University Course Evaluation PDF Extractor
====================================================
Extracts structured data from Columbia course evaluation PDFs,
appends to eval_database.csv, backs up the CSV, then deletes
the processed PDF.

Usage:
    python extract_evals.py path/to/eval1.pdf path/to/eval2.pdf ...
    python extract_evals.py path/to/folder_of_pdfs/

Requirements:
    pip install pdfplumber
"""

import pdfplumber
import csv
import re
import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime


CSV_PATH = "eval_database.csv"
BACKUP_DIR = "csv_backups"


def backup_csv():
    """Create a timestamped backup of the CSV before processing."""
    if not os.path.isfile(CSV_PATH):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"eval_database_{ts}.csv")
    shutil.copy2(CSV_PATH, backup)
    # Keep only the 10 most recent backups
    backups = sorted(Path(BACKUP_DIR).glob("eval_database_*.csv"), reverse=True)
    for old in backups[10:]:
        old.unlink()
    print(f"  Backup saved: {backup}")


def extract_text_from_pdf(pdf_path: str) -> str:
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n\n"
    return full_text


def parse_instructor(text: str) -> str:
    match = re.search(r"Instructor:\s*(.+)", text)
    if match:
        return match.group(1).strip()
    return ""


def parse_course(text: str) -> tuple[str, str]:
    match = re.search(
        r"Course:\s*.+?:\s*(\S+)\s*-\s*(.+?)(?=\nInstructor:)",
        text,
        re.DOTALL,
    )
    if match:
        code = match.group(1).strip()
        title = " ".join(match.group(2).split())
        return code, title
    return "", ""


def parse_overall_rating(text: str) -> dict:
    result = {
        "mean": None, "std": None, "median": None,
        "response_rate": None, "distribution": {},
    }
    block_match = re.search(
        r"(?:What is your overall assessment|overall assessment of (?:the |this )course)"
        r".*?"
        r"Response Rate\s+Mean\s+STD\s+Median\s*\n\s*"
        r"([\d/]+\s*\([\d.]+%\))\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
        text, re.DOTALL | re.IGNORECASE,
    )
    if block_match:
        result["response_rate"] = block_match.group(1).strip()
        result["mean"] = float(block_match.group(2))
        result["std"] = float(block_match.group(3))
        result["median"] = float(block_match.group(4))

    dist_pattern = re.compile(
        r"(Excellent|Very [Gg]ood|Good|Fair|Poor)\s+\((\d)\)\s+(\d+)\s+([\d.]+%)"
    )
    for m in dist_pattern.finditer(text):
        result["distribution"][m.group(1)] = {
            "weight": int(m.group(2)),
            "count": int(m.group(3)),
            "percent": m.group(4),
        }
    return result


def parse_workload(text: str) -> dict:
    result = {"mean": None, "response_rate": None, "distribution": {}}
    block_match = re.search(
        r"(?:How does the workload|workload in this course compare)"
        r"(.*?)(?=\n\d+ -|\Z)",
        text, re.DOTALL | re.IGNORECASE,
    )
    if not block_match:
        return result

    block = block_match.group(0)
    rr_match = re.search(r"([\d/]+\s*\([\d.]+%\))", block)
    if rr_match:
        result["response_rate"] = rr_match.group(1).strip()

    options = [
        "Much heavier workload", "Heavier workload",
        "Similar workload", "Lighter workload",
        "Much lighter workload", "No basis for comparison",
    ]
    total_weighted = 0
    total_count = 0
    for opt in options:
        pattern = re.compile(re.escape(opt) + r"\s+\((\d)\)\s+(\d+)\s+([\d.]+%)")
        m = pattern.search(block)
        if m:
            weight = int(m.group(1))
            count = int(m.group(2))
            percent = m.group(3)
            result["distribution"][opt] = {
                "weight": weight, "count": count, "percent": percent,
            }
            if opt != "No basis for comparison":
                total_weighted += weight * count
                total_count += count

    if total_count > 0:
        result["mean"] = round(total_weighted / total_count, 2)
    return result


def parse_open_responses(text: str, question_keyword: str) -> list[str]:
    q_match = re.search(
        r"\d+\s*-\s*[^\n]*" + re.escape(question_keyword[:30]) + r".*?\n(.*?)(?=\n\d+ -|\Z)",
        text, re.DOTALL | re.IGNORECASE,
    )
    if not q_match:
        return []

    block = q_match.group(1)
    responses = []
    current = []
    for line in block.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                responses.append(" ".join(current))
            current = [stripped[2:].strip()]
        elif stripped and current:
            current.append(stripped)
        elif stripped.startswith("-") and len(stripped) > 1 and stripped[1:].strip():
            if current:
                responses.append(" ".join(current))
            current = [stripped[1:].strip()]
    if current:
        responses.append(" ".join(current))

    responses = [
        r for r in responses
        if r
        and not re.match(r"^Response Option", r)
        and not re.match(r"^(Excellent|Very [Gg]ood|Good|Fair|Poor)\s+\(\d\)", r)
        and not re.match(r"^(Much heavier|Heavier|Similar|Lighter|Much lighter|No basis)\s+(workload|for)", r)
        and not re.match(r"^(Definitely|Probably)\s+(not\s+)?recommend", r, re.IGNORECASE)
        and not re.match(r"^I'm not sure I'd recommend", r)
        and not re.match(r"^Response Rate$", r)
    ]
    return responses


def parse_hours_responses(text: str) -> list[str]:
    return parse_open_responses(text, "How many hours a week")


def parse_all_reviews(text: str) -> list[str]:
    reviews = parse_open_responses(text, "What did you learn")
    recs = parse_open_responses(text, "Please qualify your recommendations")
    return reviews + recs


def process_pdf(pdf_path: str) -> dict:
    text = extract_text_from_pdf(pdf_path)
    instructor = parse_instructor(text)
    course_code, course_title = parse_course(text)
    overall = parse_overall_rating(text)
    workload = parse_workload(text)
    reviews = parse_all_reviews(text)
    hours = parse_hours_responses(text)

    return {
        "source_file": os.path.basename(pdf_path),
        "instructor": instructor,
        "course_code": course_code,
        "course_title": course_title,
        "overall_mean": overall["mean"],
        "overall_std": overall["std"],
        "overall_median": overall["median"],
        "overall_response_rate": overall["response_rate"],
        "overall_distribution": json.dumps(overall["distribution"]),
        "workload_mean": workload["mean"],
        "workload_response_rate": workload["response_rate"],
        "workload_distribution": json.dumps(workload["distribution"]),
        "reviews": json.dumps(reviews),
        "hours_per_week_responses": json.dumps(hours),
    }


def is_already_in_csv(source_file: str) -> bool:
    """Check if a PDF has already been extracted to avoid duplicates."""
    if not os.path.isfile(CSV_PATH):
        return False
    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("source_file") == source_file:
                    return True
    except Exception:
        pass
    return False


def append_to_csv(row: dict):
    fieldnames = [
        "source_file", "instructor", "course_code", "course_title",
        "overall_mean", "overall_std", "overall_median",
        "overall_response_rate", "overall_distribution",
        "workload_mean", "workload_response_rate", "workload_distribution",
        "reviews", "hours_per_week_responses",
    ]
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def print_summary(data: dict):
    print("=" * 65)
    print(f"  {data['course_code']} -- {data['course_title']}")
    print(f"  Instructor: {data['instructor']}")
    print("-" * 65)

    if data["overall_mean"] is not None:
        print(f"  Overall Rating:  {data['overall_mean']}/5.00  "
              f"(STD: {data['overall_std']}, Median: {data['overall_median']})")
        print(f"  Response Rate:   {data['overall_response_rate']}")
        dist = json.loads(data["overall_distribution"])
        if dist:
            print("  Distribution:")
            for label, info in dist.items():
                pct = float(info["percent"].rstrip("%"))
                bar = "#" * int(pct / 5)
                print(f"    {label:<12}  {info['count']:>3}  ({info['percent']:>7})  {bar}")
    else:
        print("  Overall Rating:  Not found in PDF")

    print()
    if data["workload_mean"] is not None:
        print(f"  Workload Score:  {data['workload_mean']}/5.00")
        dist = json.loads(data["workload_distribution"])
        if dist:
            print("  Distribution:")
            for label, info in dist.items():
                if label != "No basis for comparison":
                    pct = float(info["percent"].rstrip("%"))
                    bar = "#" * int(pct / 5)
                    print(f"    {label:<25}  {info['count']:>3}  ({info['percent']:>7})  {bar}")

    reviews = json.loads(data["reviews"])
    if reviews:
        print(f"\n  Reviews ({len(reviews)}):")
        for i, r in enumerate(reviews[:3], 1):
            snippet = r[:120] + ("..." if len(r) > 120 else "")
            print(f"    {i}. {snippet}")
        if len(reviews) > 3:
            print(f"    ... +{len(reviews) - 3} more")

    hours = json.loads(data["hours_per_week_responses"])
    if hours:
        print(f"\n  Hours/Week ({len(hours)}):")
        for h in hours[:3]:
            print(f"    {h[:80]}")

    print("=" * 65)
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_evals.py <pdf_file_or_folder> [...]")
        sys.exit(1)

    pdf_paths = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            pdf_paths.extend(sorted(p.glob("*.pdf")))
        elif p.is_file() and p.suffix.lower() == ".pdf":
            pdf_paths.append(p)
        else:
            print(f"  Skipping '{arg}'")

    if not pdf_paths:
        print("No PDF files found.")
        sys.exit(1)

    # Backup CSV before processing
    backup_csv()

    processed = 0
    skipped = 0
    deleted = 0

    for pdf_path in pdf_paths:
        basename = pdf_path.name

        # Skip if already in CSV
        if is_already_in_csv(basename):
            print(f"  [skip] {basename} (already in CSV)")
            skipped += 1
            continue

        print(f"  Processing: {basename}")
        try:
            data = process_pdf(str(pdf_path))
            append_to_csv(data)
            print_summary(data)
            processed += 1

            # Delete PDF after successful extraction
            try:
                pdf_path.unlink()
                deleted += 1
                print(f"  [deleted] {basename}")
            except Exception as e:
                print(f"  [warn] Could not delete {basename}: {e}")

        except Exception as e:
            print(f"  [ERROR] {basename}: {e}")
            print(f"  (PDF kept for retry)")
            print()

   # Final cleanup: delete any PDFs that are already in the CSV
    cleanup_count = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            remaining = list(p.glob("*.pdf"))
        elif p.is_file() and p.suffix.lower() == ".pdf" and p.exists():
            remaining = [p]
        else:
            remaining = []

        for pdf in remaining:
            if is_already_in_csv(pdf.name):
                try:
                    pdf.unlink()
                    cleanup_count += 1
                    print(f"  [cleanup] {pdf.name}")
                except Exception:
                    pass

    print(f"\nDone. {processed} processed, {skipped} skipped, {deleted} deleted, {cleanup_count} cleaned up.")
    print(f"CSV: {os.path.abspath(CSV_PATH)}")
    if os.path.exists(BACKUP_DIR):
        backups = list(Path(BACKUP_DIR).glob("*.csv"))
        print(f"Backups: {len(backups)} in {BACKUP_DIR}/")


if __name__ == "__main__":
    main()