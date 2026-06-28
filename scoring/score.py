"""Compute v1 RunHub scores from data/shoes-seed.csv.

This is the methodology made real — but a *spec-based* first pass. It scores
each shoe on three objective signals we can trust from specs alone, normalized
within the shoe's archetype (never across), then weights them per archetype:

  - weight        (lighter is better, within category)
  - cushioning    (heel stack, more is better)
  - responsiveness (plate + premium-foam proxy)

Ride/durability/fit in the full methodology need lab metrics (energy return,
durability, breathability) that currently live in the free-text `notes`. Once
those are structured columns, this engine extends to the full six criteria with
no change to the shape below.

No API key or network needed — pure local computation.

    python3 score.py
"""

import csv
from pathlib import Path

SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "shoes-seed.csv"
SCORES_CSV = Path(__file__).resolve().parent.parent / "data" / "scores.csv"

# Per-archetype criterion weights (must sum to 1.0). Different shoes, different jobs.
WEIGHTS = {
    "daily_trainer": {"weight": 0.35, "cushion": 0.35, "responsiveness": 0.30},
    "carbon_racer":  {"weight": 0.35, "cushion": 0.15, "responsiveness": 0.50},
    "tempo":         {"weight": 0.35, "cushion": 0.20, "responsiveness": 0.45},
    "max_cushion":   {"weight": 0.20, "cushion": 0.55, "responsiveness": 0.25},
    "stability":     {"weight": 0.30, "cushion": 0.40, "responsiveness": 0.30},
    "trail":         {"weight": 0.30, "cushion": 0.35, "responsiveness": 0.35},
}
DEFAULT_WEIGHTS = {"weight": 0.34, "cushion": 0.33, "responsiveness": 0.33}

PREMIUM_FOAM = [
    "peba", "pebax", "pwrrun pb", "pwrrun hg", "zoomx", "lightstrike pro",
    "nitro", "ff turbo", "ff blast", "supercritical", "dreamstrike", "enerzy",
]


def responsiveness_raw(row):
    """Proxy for ride/pop from plate + foam, pending real lab metrics."""
    score = 0.0
    if str(row.get("has_plate", "")).lower() == "true":
        score += 2.0
        if (row.get("plate_material") or "").lower() == "carbon":
            score += 1.0
    foam = (row.get("foam_name") or "").lower()
    if any(k in foam for k in PREMIUM_FOAM):
        score += 2.0
    return score


def pct_scores(values, higher_better=True):
    """Average-rank percentile -> 0-10, within a group. Ties share a rank."""
    n = len(values)
    out = []
    for x in values:
        if n == 1:
            out.append(5.0)
            continue
        if higher_better:
            less = sum(1 for v in values if v < x)
        else:
            less = sum(1 for v in values if v > x)
        equal = sum(1 for v in values if v == x)
        pct = (less + (equal - 1) / 2) / (n - 1)
        out.append(round(pct * 10, 1))
    return out


def value_labels(scores, prices):
    """quality-per-dollar percentile -> Great value / Fair / Premium."""
    ratios = [s / p if p else 0 for s, p in zip(scores, prices)]
    pcts = pct_scores(ratios, higher_better=True)
    labels = []
    for p in pcts:
        labels.append("Great value" if p >= 6.7 else "Premium" if p <= 3.3 else "Fair")
    return labels


def load():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def score():
    rows = load()
    by_arch = {}
    for r in rows:
        by_arch.setdefault(r["archetype"], []).append(r)

    results = []
    for arch, shoes in by_arch.items():
        w = WEIGHTS.get(arch, DEFAULT_WEIGHTS)
        weight_s = pct_scores([float(s["weight_g"]) for s in shoes], higher_better=False)
        cushion_s = pct_scores([float(s["stack_heel_mm"]) for s in shoes], higher_better=True)
        resp_s = pct_scores([responsiveness_raw(s) for s in shoes], higher_better=True)

        composites = []
        for s, ws, cs, rs in zip(shoes, weight_s, cushion_s, resp_s):
            runhub = round((ws * w["weight"] + cs * w["cushion"] + rs * w["responsiveness"]) * 10)
            composites.append(runhub)

        prices = [float(s["msrp_usd"]) if s["msrp_usd"] else 0 for s in shoes]
        values = value_labels(composites, prices)

        ranked = sorted(
            zip(shoes, composites, weight_s, cushion_s, resp_s, values),
            key=lambda t: t[1], reverse=True,
        )
        for rank, (s, runhub, ws, cs, rs, val) in enumerate(ranked, 1):
            results.append({
                "brand": s["brand"], "model": s["model"], "version": s["version"],
                "archetype": arch,
                "runhub_score": runhub, "category_rank": rank,
                "score_weight": ws, "score_cushion": cs, "score_responsiveness": rs,
                "value_rating": val, "msrp_usd": s["msrp_usd"],
            })
    return results


def report(results):
    by_arch = {}
    for r in results:
        by_arch.setdefault(r["archetype"], []).append(r)

    order = ["carbon_racer", "tempo", "daily_trainer", "stability", "max_cushion", "trail"]
    for arch in [a for a in order if a in by_arch] + [a for a in by_arch if a not in order]:
        shoes = sorted(by_arch[arch], key=lambda r: r["category_rank"])
        print(f"\n  {arch.replace('_', ' ').upper()}")
        print(f"  {'#':<3}{'shoe':<28}{'score':<7}{'wt':<5}{'cush':<6}{'resp':<6}{'value':<12}${'msrp'}")
        print("  " + "-" * 74)
        for r in shoes:
            name = f"{r['brand']} {r['model']} {r['version']}".strip()
            print(f"  {r['category_rank']:<3}{name:<28}{r['runhub_score']:<7}"
                  f"{r['score_weight']:<5}{r['score_cushion']:<6}{r['score_responsiveness']:<6}"
                  f"{r['value_rating']:<12}${r['msrp_usd']}")


def write_csv(results):
    cols = ["brand", "model", "version", "archetype", "runhub_score", "category_rank",
            "score_weight", "score_cushion", "score_responsiveness",
            "value_rating", "msrp_usd"]
    with SCORES_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(results)


def main():
    results = score()
    report(results)
    write_csv(results)
    print(f"\n  Wrote {len(results)} scored shoes to {SCORES_CSV.name}")
    print("  v1 = spec-based (weight, cushioning, plate/foam). Lab metrics next.")


if __name__ == "__main__":
    main()
