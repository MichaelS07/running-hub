// Build-time loader for data/products.csv — the shop catalog.
// Products with a shopify_buy_url are purchasable; without one they show
// as "coming soon". Swap in real Shopify cart-permalink URLs when live.

import fs from "node:fs";
import path from "node:path";

const CSV = path.resolve(process.cwd(), "..", "data", "products.csv");

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
export function getProducts() {
  if (_cache) return _cache;
  _cache = (fs.existsSync(CSV) ? parseCSV(fs.readFileSync(CSV, "utf8")) : []).map((p) => ({
    ...p,
    featureList: (p.features || "").split(";").map((f) => f.trim()).filter(Boolean),
    live: p.status === "live" && p.shopify_buy_url,
  }));
  return _cache;
}

// Append UTM params so we can see which pages sell product.
export function buyUrl(product, campaign) {
  if (!product.shopify_buy_url) return "";
  const sep = product.shopify_buy_url.includes("?") ? "&" : "?";
  return `${product.shopify_buy_url}${sep}utm_source=runhub&utm_medium=shop&utm_campaign=${campaign}`;
}
