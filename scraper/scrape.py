"""Scrape running-shoe specs into the seed CSV using LLM extraction.

Point it at any brand page or RunRepeat URL. It fetches each page, hands the
text to Claude, and appends a schema-shaped row to data/shoes-seed.csv.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    pip install -r requirements.txt
    # put up to ~5 shoe URLs (one per line) in urls.txt, then:
    python scrape.py
    # or pass URLs directly:
    python scrape.py https://www.example.com/shoe-a https://www.example.com/shoe-b

Be a good citizen: keep batches small, leave the delay in place, and don't
point this at sites whose terms forbid it. Specs only — commerce data (price,
stock, buy links) should come from affiliate feeds, which you're allowed to
republish.
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import anthropic

# Default to the most capable model. For bulk runs where cost matters more than
# edge-case accuracy, switch to "claude-haiku-4-5" (~5x cheaper).
MODEL = "claude-opus-4-8"

DELAY_SECONDS = 4          # politeness gap between page fetches
MAX_PAGE_CHARS = 16000     # trim very long pages before sending to the model

SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "shoes-seed.csv"
URLS_FILE = Path(__file__).resolve().parent / "urls.txt"

# Order matters — this is the CSV header.
FIELDS = [
    "brand", "model", "version", "release_year", "archetype", "gender",
    "weight_g", "stack_heel_mm", "stack_forefoot_mm", "drop_mm",
    "has_plate", "plate_material", "foam_name", "lug_depth_mm",
    "width_options", "has_medial_post", "msrp_usd",
    "energy_return_pct", "breathability_1to5", "durability_1to5", "wet_traction",
    "torsional_rigidity_1to5", "heel_counter_1to5", "runrepeat_score",
    "image_url", "source_url", "data_confidence", "notes",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Keys the model returns (source_url + data_confidence are computed locally).
EXTRACT_KEYS = [
    "brand", "model", "version", "release_year", "archetype", "gender",
    "weight_g", "stack_heel_mm", "stack_forefoot_mm", "drop_mm",
    "has_plate", "plate_material", "foam_name", "lug_depth_mm",
    "width_options", "has_medial_post", "msrp_usd",
    "energy_return_pct", "breathability_1to5", "durability_1to5", "wet_traction",
    "torsional_rigidity_1to5", "heel_counter_1to5", "runrepeat_score",
    "image_url", "notes",
]

SYSTEM = (
    "You extract running-shoe specifications from web page text. "
    "Respond with ONLY a single JSON object — no markdown, no code fences, no prose. "
    "Use exactly these keys: " + ", ".join(EXTRACT_KEYS) + ". "
    "Only use facts present in the text — never guess. Use null for any field not stated. "
    "Numbers are plain numbers (grams for weight; millimetres for stack/drop/lug; USD for price). "
    "`width_options` is an array of strings. `has_plate`/`has_medial_post` are booleans. "
    "`plate_material` is one of carbon/nylon/none. `gender` is one of m/w/unisex. "
    "Infer `archetype` (one of carbon_racer, tempo, daily_trainer, stability, max_cushion, "
    "trail, budget, unknown) from the specs: carbon_racer = plate + stack>=35mm + weight<240g; "
    "max_cushion = stack>=38mm and heavy; trail = lugged outsole; stability = medial post/guide "
    "rails; daily_trainer otherwise; unknown if too little data. "
    "Several fields come from RunRepeat's lab tests — capture each as a plain number if "
    "present, else null: `energy_return_pct` (energy return %), `breathability_1to5` "
    "(breathability rating out of 5), `durability_1to5` (outsole/overall durability rating "
    "out of 5), `wet_traction` (traction coefficient, roughly 0-1), `torsional_rigidity_1to5` "
    "(stiffness rating out of 5), `heel_counter_1to5` (heel-counter stiffness out of 5), "
    "`runrepeat_score` (RunRepeat's overall score out of 100). "
    "Put anything noteworthy or uncertain in `notes`."
)


def fetch_page_text(url):
    """Return cleaned page text, or raise with a helpful message."""
    resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
    body = resp.text or ""
    blocked_markers = ("Just a moment", "cf-browser-verification", "Attention Required")
    if resp.status_code == 403 or any(m in body for m in blocked_markers):
        raise RuntimeError(
            "blocked by bot protection (likely Cloudflare). This site needs a "
            "real browser — render it with Playwright and pass the HTML to "
            "extract_specs(), or seed this shoe manually."
        )
    resp.raise_for_status()
    soup = BeautifulSoup(body, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:MAX_PAGE_CHARS]


def extract_specs(client, page_text):
    """Ask Claude to extract specs as JSON from page text. Returns a dict."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": page_text}],
    )
    text = next(b.text for b in resp.content if b.type == "text")
    # Be tolerant of stray prose / code fences: parse the outermost JSON object.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in response: {text[:200]}")
    return json.loads(text[start:end + 1])


def to_row(data, url):
    """Flatten the extracted dict into a CSV row, computing confidence."""
    populated = sum(
        1 for k in ("weight_g", "stack_heel_mm", "drop_mm", "foam_name", "msrp_usd")
        if data.get(k) is not None
    )
    confidence = "high" if populated >= 4 else "medium" if populated >= 2 else "low"

    row = {f: "" for f in FIELDS}
    for k, v in data.items():
        if k == "width_options" and isinstance(v, list):
            row[k] = ";".join(v)
        elif v is not None:
            row[k] = v
    row["source_url"] = url
    row["data_confidence"] = confidence
    return row


def load_existing_rows():
    """Existing CSV rows keyed by source_url (for safe refresh merges)."""
    if not SEED_CSV.exists():
        return {}
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        return {r["source_url"]: r for r in csv.DictReader(f) if r.get("source_url")}


def write_rows(rows, overwrite=False):
    SEED_CSV.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "a"
    write_header = overwrite or not SEED_CSV.exists()
    with SEED_CSV.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, restval="")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def load_urls(argv):
    if argv:
        return argv
    if URLS_FILE.exists():
        return [
            line.strip() for line in URLS_FILE.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    return []


def load_done_urls():
    """source_urls already in the CSV, so we never scrape the same shoe twice."""
    if not SEED_CSV.exists():
        return set()
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        return {r["source_url"] for r in csv.DictReader(f) if r.get("source_url")}


def main():
    raw_args = sys.argv[1:]
    refresh = "--refresh" in raw_args
    urls = load_urls([a for a in raw_args if a != "--refresh"])
    if not urls:
        print(f"No URLs. Add some to {URLS_FILE} or pass them as arguments.")
        return

    if refresh:
        print(f"Refresh mode: re-scraping all {len(urls)} URL(s), overwriting the CSV.")
    else:
        done = load_done_urls()
        already = [u for u in urls if u in done]
        urls = [u for u in urls if u not in done]
        if already:
            print(f"Skipping {len(already)} URL(s) already in the CSV.")
        if not urls:
            print("All queued URLs are already scraped — nothing to do.")
            return
    if len(urls) > 10:
        print(f"Note: {len(urls)} URLs queued — this will take a few minutes.")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    rows = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        try:
            text = fetch_page_text(url)
            data = extract_specs(client, text)
            row = to_row(data, url)
            rows.append(row)
            label = f"{row['brand']} {row['model']}".strip() or "(no name found)"
            print(f"    -> {label}  [{row['data_confidence']} confidence]")
        except Exception as e:
            print(f"    !! skipped: {e}")
        if i < len(urls):
            time.sleep(DELAY_SECONDS)

    if rows:
        if refresh:
            # Merge over existing rows so any URL that failed this run keeps its old data.
            merged = load_existing_rows()
            for r in rows:
                merged[r["source_url"]] = r
            write_rows(list(merged.values()), overwrite=True)
        else:
            write_rows(rows, overwrite=False)
        print(f"\nWrote {len(rows)} row(s) to {SEED_CSV}. Review before trusting them.")
    else:
        print("\nNothing written.")


if __name__ == "__main__":
    main()
