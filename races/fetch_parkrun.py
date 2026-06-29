"""Fetch all NZ + Australia parkruns into data/races.csv.

parkruns are free, weekly, timed 5km community runs — the best clean source of
small/local running events. No API key needed (public events feed).

    python3 fetch_parkrun.py
"""

import csv
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "data" / "races.csv"
FEED = "https://images.parkrun.com/events.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# parkrun country codes -> (display name, slug, site domain)
COUNTRIES = {
    65: ("New Zealand", "new-zealand", "www.parkrun.co.nz"),
    3: ("Australia", "australia", "www.parkrun.com.au"),
}

FIELDS = ["slug", "name", "location", "region", "city", "lat", "lng",
          "country", "country_slug", "url", "day", "time", "distance", "type"]


def main():
    data = requests.get(FEED, headers=HEADERS, timeout=60).json()
    feats = data["events"]["features"]

    rows = []
    for f in feats:
        p = f["properties"]
        cc = p.get("countrycode")
        if cc not in COUNTRIES:
            continue
        country, country_slug, domain = COUNTRIES[cc]
        lng, lat = f["geometry"]["coordinates"]
        junior = "junior" in p["eventname"] or "junior" in p["EventLongName"].lower()
        rows.append({
            "slug": p["eventname"],
            "name": p["EventLongName"],
            "location": p.get("EventLocation", ""),
            "region": "",   # filled later by reverse-geocoding
            "city": "",     # filled later by reverse-geocoding
            "lat": lat,
            "lng": lng,
            "country": country,
            "country_slug": country_slug,
            "url": f"https://{domain}/{p['eventname']}/",
            "day": "Sunday" if junior else "Saturday",
            "time": "",     # varies by event; usually 7-9am local
            "distance": "2 km" if junior else "5 km",
            "type": "junior parkrun" if junior else "parkrun",
        })

    rows.sort(key=lambda r: (r["country"], r["name"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    by = Counter(r["country"] for r in rows)
    print(f"Wrote {len(rows)} races to {OUT.name}: " + ", ".join(f"{k} {v}" for k, v in by.items()))


if __name__ == "__main__":
    main()
