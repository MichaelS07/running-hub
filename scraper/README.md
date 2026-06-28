# Scraper

LLM-assisted spec scraper. Point it at brand pages or RunRepeat URLs; it fetches
each page, has Claude extract the [schema](../docs/schema.md) fields, and appends
rows to `../data/shoes-seed.csv`. One extractor works across any site layout —
no per-site parsing code.

**Specs only.** Get commerce data (price, stock, buy links) from affiliate feeds
— you're allowed to republish those. See [docs/affiliate-and-data](../docs/affiliate-and-data.md) (when added).

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run (5 at a time)

Put up to ~5 shoe URLs in `urls.txt` (one per line), then:

```bash
python scrape.py
```

Or pass URLs directly:

```bash
python scrape.py https://brand.com/shoe-a https://runrepeat.com/shoe-b
```

Review each batch in `../data/shoes-seed.csv` before adding the next five.

## Notes & limits

- **Model:** defaults to `claude-opus-4-8`. For bulk runs, set `MODEL` in
  `scrape.py` to `claude-haiku-4-5` to cut cost ~5x.
- **Bot protection:** sites behind Cloudflare (often RunRepeat, big retailers)
  return a challenge page — the script flags these and skips them. To scrape
  those, render with Playwright and feed the HTML to `extract_specs()`, or seed
  the shoe manually.
- **JS-rendered specs:** if a page loads specs via JavaScript, the raw fetch is
  empty — same Playwright fix.
- **Be polite & legal:** there's a delay between fetches; keep batches small,
  respect each site's `robots.txt`/terms, and don't hammer anyone.
- **Always review:** the `data_confidence` column flags thin extractions. Treat
  output as a draft, not gospel.
