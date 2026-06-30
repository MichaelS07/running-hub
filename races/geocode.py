"""Add city + region (admin1) to data/races.csv from each race's coordinates.

Offline reverse-geocoding (reverse_geocoder) — no API, no rate limits. Run after
fetch_parkrun.py. Only fills rows missing a region, so it's cheap to re-run.

    pip install reverse_geocoder
    python3 geocode.py
"""

import csv
from pathlib import Path

import reverse_geocoder as rg

CSV = Path(__file__).resolve().parent.parent / "data" / "races.csv"


def main():
    with CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    todo = [r for r in rows if not r.get("region")]
    if not todo:
        print("Nothing to geocode — all rows already have a region.")
        return

    coords = [(float(r["lat"]), float(r["lng"])) for r in todo]
    results = rg.search(coords, mode=1)
    for r, res in zip(todo, results):
        r["city"] = res["name"]
        r["region"] = res["admin1"]

    with CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    regions = Counter(r["region"] for r in rows)
    print(f"Geocoded {len(todo)} races across {len(regions)} regions.")
    for region, n in regions.most_common(10):
        print(f"  {region}: {n}")


if __name__ == "__main__":
    main()
