# Data schema

Designed so the [scoring engine](methodology.md) has every input it needs. Relational: one core
`shoes` table plus supporting tables for things that change over time (prices, review signals).

Each field is tagged by **source** and whether it's **auto** or **manual**.

## Table 1 — `shoes` (identity + objective specs)

The spine. Most of the scoring engine reads from here.

| Field | Type | Source | Auto? | Notes |
|---|---|---|---|---|
| `id` | uuid | internal | — | primary key |
| `brand` | string | feed/scrape | auto | |
| `model` | string | feed/scrape | auto | |
| `version` | int | feed/scrape | auto | e.g. Mach **6** — treat versions as separate shoes |
| `slug` | string | generated | auto | URL: `/shoes/hoka-mach-6` |
| `release_year` | int | scrape | auto | drives freshness / "current model" filters |
| `archetype` | enum | computed | auto | from Step 1 rules; manual override allowed |
| `gender` | enum | feed | auto | m / w / unisex (link variants) |
| `weight_g` | float | feed/scrape | auto | core to weight score |
| `stack_heel_mm` | float | scrape | auto | |
| `stack_forefoot_mm` | float | scrape | auto | |
| `drop_mm` | float | computed/scrape | auto | heel − forefoot |
| `has_plate` | bool | scrape/manual | mixed | carbon/nylon → archetype + ride |
| `plate_material` | enum | scrape/manual | mixed | carbon / nylon / none |
| `foam_name` | string | scrape | auto | e.g. "PEBA", "EVA" |
| `foam_class` | enum | manual map | manual | super / responsive / standard (maintained lookup) |
| `outsole_rubber_pct` | int | manual/scrape | manual | coverage estimate → durability |
| `lug_depth_mm` | float | scrape | auto | trail detection |
| `width_options` | array | feed | auto | narrow/wide → fit score |
| `has_medial_post` | bool | scrape/manual | mixed | stability detection |
| `msrp_usd` | float | feed | auto | reference price (not live price) |
| `image_url` | string | feed | auto | |
| `data_confidence` | enum | computed | auto | high/med/low from field completeness |

## Table 2 — `offers` (live prices + affiliate links)

Separate because price changes constantly and a shoe has many sellers. Powers the "Check price"
button and the Value rating. Keep a `price_history` row on each check → enables "lowest in 90 days".

| Field | Type | Source | Auto? | Notes |
|---|---|---|---|---|
| `shoe_id` | fk | — | — | |
| `retailer` | string | affiliate feed | auto | Running Warehouse, REI… |
| `price_usd` | float | feed/scrape | auto | live price |
| `in_stock` | bool | feed | auto | hide dead links |
| `affiliate_url` | string | network | auto | Awin/CJ/RW deep link |
| `network` | enum | — | auto | awin / cj / amazon / direct |
| `last_checked` | timestamp | cron | auto | freshness |

## Table 3 — `review_signals` (aggregated sentiment, one row per source)

Store raw per-source signals; compute the Bayesian average downstream (don't pre-blend, so we can
re-tune).

| Field | Type | Source | Auto? | Notes |
|---|---|---|---|---|
| `shoe_id` | fk | — | — | |
| `source` | enum | — | auto | runrepeat / retailer / reddit / youtube |
| `rating_avg` | float | scrape | auto | normalize all to 0–10 |
| `rating_count` | int | scrape | auto | feeds Bayesian confidence constant |
| `sentiment_comfort` | float | NLP (later) | auto | per-dimension tags from review text |
| `sentiment_durability` | float | NLP (later) | auto | catches "fell apart at 200mi" |
| `sentiment_fit` | float | NLP (later) | auto | sizing/lockdown |
| `fit_verdict` | enum | scrape/NLP | auto | runs small / true / large |

## Table 4 — `scores` (computed output — a view, not hand-entered)

Materialized from Tables 1–3 by the scoring job. Nothing here is typed by a human.

| Field | Source |
|---|---|
| `score_ride`, `score_cushion`, `score_weight`, `score_durability`, `score_fit`, `score_versatility` | computed (Steps 2–3) |
| `runhub_score` | weighted composite (Step 5), 0–100 |
| `value_rating` | quality-per-dollar percentile (Step 5 refinement) |
| `category_rank` | rank within archetype |
| `computed_at` | job timestamp |

## Table 5 — `editorial` (the trust layer — manual)

| Field | Source | Notes |
|---|---|---|
| `tested_by_us` | manual | the badge |
| `miles_logged` | manual | real mileage |
| `strava_embed_url` | manual | proof |
| `verdict_text` | manual | human take |
| `pros` / `cons` | manual | bullet lists |

## Where the automated fields actually come from

- **Affiliate product feeds** (Awin / CJ / Running Warehouse) → brand, model, weight, MSRP, images,
  live price, affiliate URLs. *Best structured source — start here.*
- **Targeted scrapers** (brand spec pages, RunRepeat) → stack, drop, foam, plate, lab specs.
- **Manual lookups** → `foam_class` map, `outsole_rubber_pct`, plate confirmation. Low volume, high
  leverage — a few hours seeds hundreds of shoes.
- **NLP layer (Phase 2)** → the `sentiment_*` fields. Skip at launch; use `rating_avg`/`rating_count`.

## Phase 1 minimum — don't build all of this yet

To launch you only truly need: `shoes` (specs + archetype), `offers` (one affiliate link + price),
`review_signals` (rating_avg + count from 1–2 sources), and computed `scores`. The NLP fields and
Table 5 come later. **~12 fields gets you a live, ranking shoe.**
