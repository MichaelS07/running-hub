"""Compute v2 RunHub scores from data/shoes-seed.csv.

Six criteria, each normalized within the shoe's archetype (never across), then
weighted per archetype. Built on real lab metrics now in the CSV, with graceful
handling of gaps (a missing metric scores neutral, not zero):

  ride        energy_return_pct           (higher better)
  cushioning  stack_heel_mm               (higher better)
  weight      weight_g                    (lower better)
  comfort_fit breathability + widths + heel counter
  durability  durability_1to5             (higher better; sparse -> neutral)
  expert      runrepeat_score             (RunRepeat's overall score, 0-100)

`expert` is a transparent sentiment input, kept to a moderate weight so the
ranking leads with our own spec-based methodology rather than echoing RunRepeat.

No API key or network needed.

    python3 score.py
"""

import csv
from pathlib import Path

SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "shoes-seed.csv"
SCORES_CSV = Path(__file__).resolve().parent.parent / "data" / "scores.csv"

CRITERIA = ["ride", "cushioning", "weight", "comfort_fit", "durability", "expert"]

# Per-archetype weights (each row sums to 1.0). Different shoes, different jobs.
WEIGHTS = {
    "daily_trainer": dict(ride=.18, cushioning=.18, weight=.15, comfort_fit=.14, durability=.15, expert=.20),
    "carbon_racer":  dict(ride=.28, cushioning=.08, weight=.22, comfort_fit=.07, durability=.05, expert=.30),
    "tempo":         dict(ride=.25, cushioning=.12, weight=.20, comfort_fit=.08, durability=.10, expert=.25),
    "max_cushion":   dict(ride=.12, cushioning=.30, weight=.08, comfort_fit=.15, durability=.15, expert=.20),
    "stability":     dict(ride=.12, cushioning=.18, weight=.12, comfort_fit=.23, durability=.15, expert=.20),
    "trail":         dict(ride=.12, cushioning=.13, weight=.12, comfort_fit=.13, durability=.25, expert=.25),
}
DEFAULT_WEIGHTS = {c: 1 / len(CRITERIA) for c in CRITERIA}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def comfort_fit_raw(row):
    """Blend breathability, fit-width availability, and heel-counter into 0-10."""
    parts = []
    b = num(row.get("breathability_1to5"))
    if b is not None:
        parts.append(b / 5 * 10)
    hc = num(row.get("heel_counter_1to5"))
    if hc is not None:
        parts.append(hc / 5 * 10)
    widths = [w for w in (row.get("width_options") or "").split(";") if w.strip()]
    parts.append(min(len(widths), 4) / 4 * 10)
    return sum(parts) / len(parts) if parts else None


def raw_value(row, criterion):
    if criterion == "ride":
        return num(row.get("energy_return_pct"))
    if criterion == "cushioning":
        return num(row.get("stack_heel_mm"))
    if criterion == "weight":
        return num(row.get("weight_g"))
    if criterion == "comfort_fit":
        return comfort_fit_raw(row)
    if criterion == "durability":
        return num(row.get("durability_1to5"))
    if criterion == "expert":
        return num(row.get("runrepeat_score"))
    return None


def pct_within(values, higher_better=True):
    """Average-rank percentile -> 0-10 within a group. None -> 5.0 (neutral)."""
    present = [v for v in values if v is not None]
    n = len(present)
    out = []
    for v in values:
        if v is None or n <= 1:
            out.append(5.0)
            continue
        if higher_better:
            less = sum(1 for x in present if x < v)
        else:
            less = sum(1 for x in present if x > v)
        equal = sum(1 for x in present if x == v)
        pct = (less + (equal - 1) / 2) / (n - 1)
        out.append(round(pct * 10, 1))
    return out


def value_labels(scores, prices):
    ratios = [s / p if p else 0 for s, p in zip(scores, prices)]
    pcts = pct_within(ratios, higher_better=True)
    return ["Great value" if p >= 6.7 else "Premium" if p <= 3.3 else "Fair" for p in pcts]


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
        # 0-10 sub-scores per criterion, normalized within this archetype.
        subs = {}
        for c in CRITERIA:
            raws = [raw_value(s, c) for s in shoes]
            subs[c] = pct_within(raws, higher_better=(c != "weight"))

        composites, completeness = [], []
        for i, s in enumerate(shoes):
            runhub = round(sum(subs[c][i] * w[c] for c in CRITERIA) * 10)
            composites.append(runhub)
            present = sum(1 for c in CRITERIA if raw_value(s, c) is not None)
            completeness.append("high" if present >= 5 else "medium" if present >= 3 else "low")

        prices = [num(s["msrp_usd"]) or 0 for s in shoes]
        values = value_labels(composites, prices)

        ranked = sorted(
            range(len(shoes)),
            key=lambda i: composites[i], reverse=True,
        )
        for rank, i in enumerate(ranked, 1):
            s = shoes[i]
            results.append({
                "brand": s["brand"], "model": s["model"], "version": s["version"],
                "archetype": arch, "runhub_score": composites[i], "category_rank": rank,
                **{f"score_{c}": subs[c][i] for c in CRITERIA},
                "value_rating": values[i], "score_confidence": completeness[i],
                "msrp_usd": s["msrp_usd"],
            })
    return results


def report(results):
    by_arch = {}
    for r in results:
        by_arch.setdefault(r["archetype"], []).append(r)

    order = ["carbon_racer", "tempo", "daily_trainer", "stability", "max_cushion", "trail"]
    hdr = (f"  {'#':<3}{'shoe':<26}{'SCORE':<7}{'ride':<6}{'cush':<6}{'wt':<5}"
           f"{'fit':<6}{'dur':<6}{'exp':<6}{'value':<12}")
    for arch in [a for a in order if a in by_arch] + [a for a in by_arch if a not in order]:
        shoes = sorted(by_arch[arch], key=lambda r: r["category_rank"])
        print(f"\n  {arch.replace('_', ' ').upper()}")
        print(hdr)
        print("  " + "-" * 82)
        for r in shoes:
            name = f"{r['brand']} {r['model']} {r['version']}".strip()[:25]
            print(f"  {r['category_rank']:<3}{name:<26}{r['runhub_score']:<7}"
                  f"{r['score_ride']:<6}{r['score_cushioning']:<6}{r['score_weight']:<5}"
                  f"{r['score_comfort_fit']:<6}{r['score_durability']:<6}{r['score_expert']:<6}"
                  f"{r['value_rating']:<12}")


def write_csv(results):
    cols = (["brand", "model", "version", "archetype", "runhub_score", "category_rank"]
            + [f"score_{c}" for c in CRITERIA]
            + ["value_rating", "score_confidence", "msrp_usd"])
    with SCORES_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(results)


def main():
    results = score()
    report(results)
    write_csv(results)
    print(f"\n  Wrote {len(results)} scored shoes to {SCORES_CSV.name}")
    print("  ride=energy return  cush=stack  wt=weight  fit=comfort/fit  dur=durability  exp=RunRepeat score")


if __name__ == "__main__":
    main()
