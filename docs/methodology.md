# Scoring methodology

This is the defensible IP. Designed to be **credible** (compares like-with-like), **transparent**
(every number traces to a source), and **automatable** (maps to data we can pull).

## Principle 0: score within a category, never across

The biggest credibility killer is comparing a 450g max-cushion recovery shoe against a 180g carbon
racer on one scale. So every shoe is first **classified into an archetype**, then scored *relative to
its peers in that archetype*. A 9.0 means "top-tier daily trainer," not "better than a Vaporfly."

## Step 1 — Archetype classification (auto-assigned from specs)

| Archetype | Auto-rule (rough) |
|---|---|
| Carbon racer | has plate + stack ≥ 35mm + weight < 240g |
| Tempo / uptempo | lightweight, responsive foam, often plated, < 250g |
| Daily trainer (neutral) | stack 28–40mm, no medial post, 220–290g |
| Stability / support | has medial post / guide rails |
| Max-cushion | stack ≥ 38mm, weight > 280g |
| Trail | lugged outsole ≥ 3mm |
| Budget | price below category median − 25% |

Allow a manual override on archetype for edge cases.

## Step 2 — The six scoring criteria

Each scored 0–10 from a mix of **objective** (spec, automated) and **sentiment** (aggregated reviews):

| Criterion | What it measures | Primary data source | Type |
|---|---|---|---|
| Ride & responsiveness | energy return, "pop" | foam type, plate, stack + review sentiment on "ride" | hybrid |
| Cushioning & comfort | underfoot protection, plushness | stack height, foam class + comfort rating | hybrid |
| Weight | grams (lower = better, within category) | spec weight, percentile-ranked | objective |
| Durability | outsole + midsole longevity | outsole rubber coverage, claimed mileage + durability complaints | hybrid |
| Fit & stability | sizing accuracy, lockdown, support | width options, heel counter, post + fit sentiment | hybrid |
| Versatility | range of paces/uses it covers | archetype breadth + "do-it-all" sentiment | hybrid |

## Step 3 — Normalize within category (the credibility engine)

For each objective metric, convert the raw number to a **0–10 percentile score against peers in the
same archetype**. e.g. a 238g daily trainer in the ~90th percentile of daily-trainer weights → 9.0.
Auto-recalibrates as shoes are added; no hand-tuning.

For sentiment, use a **Bayesian average** so a shoe with 4 glowing reviews doesn't outrank one with
400 solid ones:

```
adjusted = (C * m + sum(ratings)) / (C + n)
```

where `m` = category mean, `n` = review count, `C` = confidence constant (~15 reviews). This is the
single most important anti-gaming detail.

## Step 4 — Weight the criteria per archetype

Different shoes have different jobs, so weights shift. Defaults:

| Criterion | Daily trainer | Carbon racer | Max-cushion | Trail |
|---|---|---|---|---|
| Ride & responsiveness | 20% | 35% | 15% | 20% |
| Cushioning & comfort | 20% | 10% | 30% | 15% |
| Weight | 15% | 25% | 10% | 10% |
| Durability | 20% | 5% | 15% | 25% |
| Fit & stability | 15% | 15% | 15% | 20% |
| Versatility | 10% | 10% | 15% | 10% |

(Add weight columns for tempo, stability, budget as those archetypes fill in.)

## Step 5 — The composite "RunHub Score"

```
Score = sum(criterion_score * category_weight) * 10   ->   0-100
```

### Value is separate, not baked in

Price changes weekly and a great shoe shouldn't lose *quality* points for costing more. So:

- **RunHub Score** = pure quality (no price).
- **Value rating** = a separate badge = quality-score-per-dollar, percentile-ranked within category
  ("Best value" / "Premium"). A second axis, not mixed into the headline.

## Step 6 — Confidence / data-completeness flag

Attach a **confidence level** (high / medium / low) from how many inputs are populated + review
volume. Low-confidence shoes get a visible "limited data" tag instead of a falsely precise score.
Admitting uncertainty protects trust and is a differentiator.

## The trust layer (Phase 1.5 — the real moat)

The algorithm gets us launched and ranking. What earns *trust* over RunRepeat is that we actually run.
Reserve manual override fields: a "tested by us" badge + real Strava data / wear photos on shoes we've
logged miles in. Algorithm scales; human testing earns the links and loyalty.
