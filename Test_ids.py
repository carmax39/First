import requests, time, re

cookie = open(".columbia_cookie").read().strip()
token = open(".columbia_token").read().strip()

h = {
    "accept": "application/json, text/plain, */*",
    "authorization": "Bearer " + token,
    "origin": "https://vergil.columbia.edu",
    "referer": "https://vergil.columbia.edu/",
    "cookie": cookie,
    "user-agent": "Mozilla/5.0",
}

evalkit_url = "https://prod2-sas-studentrecords.api.columbia.edu/legacy/evalkit"
search_url = "https://prod2-sas-studentrecords.api.columbia.edu/v1/course_and_class_search"

# Most common letters first based on what we know
LETTER_ORDER = "WVGKBEANSDLRPOCMFTHIJQUXYZ"

def find_evalkit_id(dept, num):
    for letter in LETTER_ORDER:
        cand = dept + letter + num
        r = requests.get(evalkit_url, params={"course_id": cand}, headers=h, timeout=15)
        body = r.json()
        items = body if isinstance(body, list) else body.get("data", [])
        if isinstance(items, dict):
            continue
        count = len([x for x in items if isinstance(x, dict) and x.get("reportLink")])
        if count > 0 or (isinstance(items, list) and len(items) > 0):
            return cand, len(items), count
        time.sleep(0.15)
    return None, 0, 0

# Get 50 courses from Fall 2024
r = requests.get(search_url + "?term=20243&page[number]=3&page[size]=50&schedule=true", headers=h, timeout=30)
courses = r.json().get("data", {}).get("courses", [])
print(f"Got {len(courses)} courses from Fall 2024\n")

hits = 0
tested = 0

for c in courses[:20]:
    name = c.get("course_name", "")
    title = c.get("course_official_title", "")[:35]

    m = re.match(r'^([A-Z]+?)(\d+)$', name)
    if not m:
        continue

    dept, num = m.groups()
    tested += 1

    ek_id, total, pdfs = find_evalkit_id(dept, num)
    if ek_id:
        hits += 1
        print(f"  HIT  {name:15s} -> {ek_id:15s} ({pdfs} PDFs)  {title}")
    else:
        print(f"  miss {name:15s}                              {title}")

print(f"\n  Result: {hits}/{tested} hits")