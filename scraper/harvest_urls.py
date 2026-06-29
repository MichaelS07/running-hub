"""Harvest real shoe URLs from RunRepeat's catalog into urls.txt.

Pulls brand-prefixed review links across catalog pages, drops any shoe already
in shoes-seed.csv, and writes urls.txt up to a target total. Far more reliable
than hand-guessing slugs.

    python3 harvest_urls.py            # fill toward 100 total
    python3 harvest_urls.py 60         # target 60 total
"""

import csv
import re
import sys
import time
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data" / "shoes-seed.csv"
URLS = Path(__file__).resolve().parent / "urls.txt"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
BRANDS = ["hoka", "asics", "nike", "adidas", "saucony", "brooks", "new-balance",
          "puma", "mizuno", "salomon", "on", "altra", "topo", "la-sportiva", "merrell"]


def existing_slugs():
    if not DATA.exists():
        return [], set()
    with DATA.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    slugs = [r["source_url"].rstrip("/").split("/")[-1] for r in rows if r.get("source_url")]
    return slugs, set(slugs)


def harvest(pages=10):
    found, seen = [], set()
    for p in range(1, pages + 1):
        url = f"https://runrepeat.com/catalog/running-shoes?page={p}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            for s in re.findall(r'href="(?:https://runrepeat.com)?/([a-z0-9-]+)"', r.text):
                if any(s.startswith(b + "-") for b in BRANDS) and s not in seen:
                    seen.add(s)
                    found.append(s)
        except Exception as e:
            print(f"page {p} failed: {e}")
        time.sleep(1)
    return found


def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    ex_list, ex_set = existing_slugs()
    harvested = harvest()
    new = [s for s in harvested if s not in ex_set]
    chosen = new[: max(0, target - len(ex_set))]
    all_slugs = ex_list + chosen

    with URLS.open("w", encoding="utf-8") as f:
        f.write("# RunHub scrape list. scrape.py skips any URL already in shoes-seed.csv.\n")
        f.write(f"# {len(ex_set)} already scraped + {len(chosen)} new = {len(all_slugs)} total.\n")
        for s in all_slugs:
            f.write(f"https://runrepeat.com/{s}\n")

    print(f"existing: {len(ex_set)} | harvested: {len(harvested)} | new available: {len(new)} | added: {len(chosen)}")
    print(f"urls.txt now lists {len(all_slugs)} shoes (scraper will fetch the {len(chosen)} new ones).")
    if chosen:
        print("sample of new:", ", ".join(chosen[:6]))


if __name__ == "__main__":
    main()
