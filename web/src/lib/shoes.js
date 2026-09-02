// Build-time data loader: reads the CSVs in ../data and merges specs + scores
// into one shoe object per row, keyed by a URL-friendly slug.

import fs from "node:fs";
import path from "node:path";

const DATA_DIR = path.resolve(process.cwd(), "..", "data");

export const ARCHETYPES = {
  carbon_racer: "Carbon Racers",
  tempo: "Tempo / Uptempo",
  daily_trainer: "Daily Trainers",
  stability: "Stability",
  max_cushion: "Max Cushion",
  trail: "Trail",
};
export const ARCH_ORDER = Object.keys(ARCHETYPES);

export const CATEGORY_SLUGS = {
  carbon_racer: "carbon-racers",
  tempo: "tempo",
  daily_trainer: "daily-trainers",
  stability: "stability",
  max_cushion: "max-cushion",
  trail: "trail",
};
export const SLUG_TO_ARCH = Object.fromEntries(
  Object.entries(CATEGORY_SLUGS).map(([k, v]) => [v, k])
);

export function brandsOf(shoes) {
  return [...new Set(shoes.map((s) => s.brand))].sort();
}
export function maxPriceOf(shoes) {
  return Math.ceil(Math.max(...shoes.map((s) => Number(s.msrp_usd) || 0)) / 10) * 10;
}

export const CRITERIA = [
  ["score_ride", "Ride"],
  ["score_cushioning", "Cushion"],
  ["score_weight", "Weight"],
  ["score_comfort_fit", "Comfort/fit"],
  ["score_durability", "Durability"],
  ["score_expert", "Expert"],
];

function splitRow(line) {
  const out = [];
  let cur = "", inQ = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') {
      if (inQ && line[i + 1] === '"') { cur += '"'; i++; }
      else inQ = !inQ;
    } else if (c === "," && !inQ) { out.push(cur); cur = ""; }
    else cur += c;
  }
  out.push(cur);
  return out;
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = splitRow(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = splitRow(line);
    const row = {};
    headers.forEach((h, i) => (row[h] = (cells[i] ?? "").trim()));
    return row;
  });
}

const keyOf = (r) => `${r.brand}|${r.model}|${r.version}`.toLowerCase();

function displayName(r) {
  const model = (r.model || "").trim();
  const v = (r.version || "").trim();
  const tail = v && !new RegExp(`(^|\\s)${v}$`).test(model) ? ` ${v}` : "";
  return `${r.brand} ${model}${tail}`.trim();
}

function slugOf(sp) {
  const tail = (sp.source_url || "").split("/").filter(Boolean).pop() || "";
  const cleaned = tail.replace(/\.html$/i, "");
  if (cleaned && /^[a-z0-9-]+$/i.test(cleaned) && cleaned.length > 6 && !/^\d+$/.test(cleaned)) {
    return cleaned.toLowerCase();
  }
  return keyOf(sp).replace(/\|/g, "-").replace(/\s+/g, "-");
}

function howItRuns(sp, name) {
  const stored = (sp.how_it_runs || "").trim();
  if (stored) return stored;
  const job = (ARCHETYPES[sp.archetype] || "running shoe").toLowerCase();
  const bits = [];
  if (sp.weight_g) bits.push(`${sp.weight_g} g`);
  if (sp.stack_heel_mm) bits.push(`${sp.stack_heel_mm} mm heel stack`);
  if (sp.drop_mm) bits.push(`${sp.drop_mm} mm drop`);
  const head = `${name} is a ${job}${bits.length ? ` (${bits.join(", ")})` : ""}.`;
  const notes = (sp.notes || "").trim();
  const snippet = notes.length > 260 ? notes.slice(0, 257).replace(/\s+\S*$/, "") + "…" : notes;
  const lab = snippet ? ` From the lab notes on file: ${snippet}` : "";
  return `${head}${lab} This is a spec-and-lab synthesis, not a wear-test — RunHub has not logged miles in this pair.`;
}

function reviewSources(sp) {
  const stored = (sp.review_sources || "").trim();
  if (stored) return stored;
  const url = (sp.source_url || "").trim();
  return url ? `${url} · RunHub lab-notes field` : "RunHub lab-notes field in data/shoes-seed.csv";
}

let _cache = null;

export function getShoes() {
  if (_cache) return _cache;
  const specs = parseCSV(fs.readFileSync(path.join(DATA_DIR, "shoes-seed.csv"), "utf8"));
  const scores = parseCSV(fs.readFileSync(path.join(DATA_DIR, "scores.csv"), "utf8"));
  const scoreByKey = {};
  scores.forEach((s) => (scoreByKey[keyOf(s)] = s));

  _cache = specs.map((sp) => {
    const sc = scoreByKey[keyOf(sp)] || {};
    const name = displayName(sp);
    return { ...sp, ...sc, slug: slugOf(sp), name, how_it_runs: howItRuns(sp, name), review_sources: reviewSources(sp) };
  });
  return _cache;
}

export function shoesByArchetype() {
  const groups = {};
  for (const shoe of getShoes()) {
    (groups[shoe.archetype] ||= []).push(shoe);
  }
  for (const g of Object.values(groups)) {
    g.sort((a, b) => Number(a.category_rank) - Number(b.category_rank));
  }
  return ARCH_ORDER.filter((a) => groups[a]).map((a) => ({
    key: a,
    title: ARCHETYPES[a],
    shoes: groups[a],
  }));
}

export function scoreColor(s) {
  const n = Number(s);
  if (n >= 70) return "var(--good)";
  if (n >= 50) return "var(--mid)";
  return "var(--low)";
}

export function valueClass(v) {
  if (v === "Great value") return "value-great";
  if (v === "Premium") return "value-premium";
  return "value-fair";
}
