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

export function racesByCountrySlug(slug) {
  return getRaces().filter((r) => r.country_slug === slug);
}

export function countryList() {
  const counts = {};
  for (const r of getRaces()) counts[r.country_slug] = (counts[r.country_slug] || 0) + 1;
  return Object.keys(counts)
    .map((slug) => ({ slug, name: COUNTRY_NAMES[slug] || slug, count: counts[slug] }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
