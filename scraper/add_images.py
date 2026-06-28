"""Fill the image_url column in data/shoes-seed.csv from each shoe's page.

Pulls the og:image (the page's share photo — a clean product shot). No API key
needed. Only fills rows whose image_url is empty, so it's safe to re-run.

    python3 add_images.py

Note: these are hotlinked source URLs — fine for prototyping. For production,
prefer images from licensed affiliate product feeds, or self-host them.
"""

import csv
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "shoes-seed.csv"
DELAY_SECONDS = 1.5
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}


def og_image(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for key, val in [("property", "og:image"), ("name", "twitter:image")]:
        tag = soup.find("meta", attrs={key: val})
        if tag and tag.get("content"):
            return tag["content"]
    return None


def main():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    todo = [r for r in rows if not r.get("image_url")]
    print(f"{len(rows)} shoes; {len(todo)} missing an image.")

    filled = 0
    for i, r in enumerate(todo, 1):
        name = f"{r['brand']} {r['model']}".strip()
        try:
            img = og_image(r["source_url"])
            if img:
                r["image_url"] = img
                filled += 1
                print(f"[{i}/{len(todo)}] {name} -> ok")
            else:
                print(f"[{i}/{len(todo)}] {name} -> no image found")
        except Exception as e:
            print(f"[{i}/{len(todo)}] {name} -> failed: {e}")
        if i < len(todo):
            time.sleep(DELAY_SECONDS)

    with SEED_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nFilled {filled} image URL(s). Updated {SEED_CSV.name}.")


if __name__ == "__main__":
    main()
