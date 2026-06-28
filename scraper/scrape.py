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
    "width_options", "has_medial_post", "msrp_usd", "image_url",
    "source_url", "data_confidence", "notes",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# JSON schema the model must fill. Nullable via anyOf so missing specs come back
# as null instead of guesses. additionalProperties:false is required.
def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}

EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "brand": _nullable({"type": "string"}),
        "model": _nullable({"type": "string"}),
        "version": _nullable({"type": "integer"}),
        "release_year": _nullable({"type": "integer"}),
        "archetype": _nullable({"type": "string", "enum": [
            "carbon_racer", "tempo", "daily_trainer", "stability",
            "max_cushion", "trail", "budget", "unknown",
        ]}),
        "gender": _nullable({"type": "string", "enum": ["m", "w", "unisex"]}),
        "weight_g": _nullable({"type": "number"}),
        "stack_heel_mm": _nullable({"type": "number"}),
        "stack_forefoot_mm": _nullable({"type": "number"}),
        "drop_mm": _nullable({"type": "number"}),
        "has_plate": _nullable({"type": "boolean"}),
        "plate_material": _nullable({"type": "string", "enum": ["carbon", "nylon", "none"]}),
        "foam_name": _nullable({"type": "string"}),
        "lug_depth_mm": _nullable({"type": "number"}),
        "width_options": _nullable({"type": "array", "items": {"type": "string"}}),
        "has_medial_post": _nullable({"type": "boolean"}),
        "msrp_usd": _nullable({"type": "number"}),
        "image_url": _nullable({"type": "string"}),
        "notes": _nullable({"type": "string"}),
    },
    "required": [
        "brand", "model", "version", "release_year", "archetype", "gender",
        "weight_g", "stack_heel_mm", "stack_forefoot_mm", "drop_mm",
        "has_plate", "plate_material", "foam_name", "lug_depth_mm",
        "width_options", "has_medial_post", "msrp_usd", "image_url", "notes",
    ],
}

SYSTEM = (
    "You extract running-shoe specifications from web page text into a strict "
    "schema. Only use facts present in the text — never guess. If a field isn't "
    "stated, return null for it. Infer `archetype` from the specs you do find "
    "(carbon_racer: plate + stack>=35mm + weight<240g; max_cushion: stack>=38mm "
    "& heavy; trail: lugged outsole; stability: medial post/guide rails; "
    "daily_trainer otherwise; unknown if too little data). Use grams for weight, "
    "millimetres for stack/drop/lug, USD for price. Put anything noteworthy or "
    "uncertain in `notes`."
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
    """Ask Claude to fill the schema from page text. Returns a dict."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": page_text}],
        output_config={"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


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


def append_rows(rows):
    SEED_CSV.parent.mkdir(parents=True, exist_ok=True)
    new_file = not SEED_CSV.exists()
    with SEED_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
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


def main():
    urls = load_urls(sys.argv[1:])
    if not urls:
        print(f"No URLs. Add some to {URLS_FILE} or pass them as arguments.")
        return
    if len(urls) > 5:
        print(f"Note: {len(urls)} URLs queued — consider batches of ~5 to review as you go.")

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
        append_rows(rows)
        print(f"\nWrote {len(rows)} row(s) to {SEED_CSV}. Review before trusting them.")
    else:
        print("\nNothing written.")


if __name__ == "__main__":
    main()
