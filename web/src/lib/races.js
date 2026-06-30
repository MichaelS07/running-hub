// Build-time loader for data/races.csv (parkrun events).
import fs from "node:fs";
import path from "node:path";

const RACES = path.resolve(process.cwd(), "..", "data", "races.csv");

export const COUNTRY_NAMES = { "new-zealand": "New Zealand", australia: "Australia" };

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

let _cache = null;
export function getRaces() {
  if (_cache) return _cache;
  _cache = fs.existsSync(RACES) ? parseCSV(fs.readFileSync(RACES, "utf8")) : [];
  return _cache;
}

export function slugify(s) {
  return (s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function racesByRegionSlug(slug) {
  return getRaces().filter((r) => slugify(r.region) === slug);
}

// Regions grouped by country, for the /races landing.
export function regionsByCountry() {
  const regions = {};
  for (const r of getRaces()) {
    const slug = slugify(r.region);
    (regions[slug] ||= { slug, name: r.region, country: r.country, country_slug: r.country_slug, count: 0 }).count++;
  }
  const byCountry = {};
  for (const reg of Object.values(regions)) {
    (byCountry[reg.country] ||= { country: reg.country, country_slug: reg.country_slug, regions: [] }).regions.push(reg);
  }
  for (const c of Object.values(byCountry)) c.regions.sort((a, b) => b.count - a.count);
  return Object.values(byCountry).sort((a, b) => a.country.localeCompare(b.country));
}

export function allRegions() {
  const seen = {};
  for (const r of getRaces()) {
    const slug = slugify(r.region);
    seen[slug] ||= { slug, name: r.region, country: r.country };
  }
  return Object.values(seen);
}
