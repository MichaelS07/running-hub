// RunHub — loads data/scores.csv and renders ranked scorecards per category.

const ARCHETYPES = {
  carbon_racer:  "Carbon Racers",
  tempo:         "Tempo / Uptempo",
  daily_trainer: "Daily Trainers",
  stability:     "Stability",
  max_cushion:   "Max Cushion",
  trail:         "Trail",
};

const CRITERIA = [
  ["score_ride", "Ride"],
  ["score_cushioning", "Cushion"],
  ["score_weight", "Weight"],
  ["score_comfort_fit", "Comfort/fit"],
  ["score_durability", "Durability"],
  ["score_expert", "Expert"],
];

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = splitRow(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = splitRow(line);
    const row = {};
    headers.forEach((h, i) => (row[h] = cells[i] ?? ""));
    return row;
  });
}

// Quote-aware single-row splitter.
function splitRow(line) {
  const out = [];
  let cur = "", inQ = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') {
      if (inQ && line[i + 1] === '"') { cur += '"'; i++; }
      else inQ = !inQ;
    } else if (c === "," && !inQ) {
      out.push(cur); cur = "";
    } else cur += c;
  }
  out.push(cur);
  return out;
}

function scoreColor(s) {
  if (s >= 70) return "var(--good)";
  if (s >= 50) return "var(--mid)";
  return "var(--low)";
}

function valueClass(v) {
  if (v === "Great value") return "value-great";
  if (v === "Premium") return "value-premium";
  return "value-fair";
}

function shoeName(row) {
  // Some scraped model names already include the version (e.g. "Adios Pro 3").
  const model = (row.model || "").trim();
  const v = (row.version || "").trim();
  const tail = v && !new RegExp(`(^|\\s)${v}$`).test(model) ? ` ${v}` : "";
  return `${row.brand} ${model}${tail}`.trim();
}

function card(row) {
  const score = Math.round(Number(row.runhub_score));
  const name = shoeName(row);
  const arch = ARCHETYPES[row.archetype] || row.archetype;
  const color = scoreColor(score);

  const bars = CRITERIA.map(([key, label]) => {
    const v = Number(row[key]);
    const pct = Math.max(0, Math.min(100, v * 10));
    return `<div class="bar-row">
      <span class="bar-label">${label}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${pct}%"></span></span>
      <span class="bar-val">${v.toFixed(1)}</span>
    </div>`;
  }).join("");

  const photo = row.image_url
    ? `<div class="card-photo"><img src="${row.image_url}" alt="${name}" loading="lazy" /></div>`
    : "";

  return `<article class="card ${row.category_rank === "1" ? "rank-1" : ""}">
    ${photo}
    <div class="card-body">
      <div class="card-top">
        <div>
          <div class="card-rank">#${row.category_rank} ${arch}</div>
          <div class="card-name">${name}</div>
        </div>
        <div class="score-badge">
          <div class="score-circle" style="border-color:${color};color:${color}">${score}</div>
          <div class="score-label">score</div>
        </div>
      </div>
      <div class="bars">${bars}</div>
      <div class="card-foot">
        <span class="value-badge ${valueClass(row.value_rating)}">${row.value_rating}</span>
        <span class="price">$<b>${row.msrp_usd}</b></span>
        <a class="cta" href="#" data-shoe="${name}">Check price</a>
      </div>
    </div>
  </article>`;
}

function render(rows) {
  const groups = {};
  rows.forEach((r) => (groups[r.archetype] ||= []).push(r));
  Object.values(groups).forEach((g) =>
    g.sort((a, b) => Number(a.category_rank) - Number(b.category_rank))
  );

  const order = Object.keys(ARCHETYPES).filter((a) => groups[a]);
  const nav = document.getElementById("cat-nav");
  const main = document.getElementById("catalog");
  main.innerHTML = "";

  order.forEach((arch) => {
    const title = ARCHETYPES[arch];
    nav.insertAdjacentHTML("beforeend", `<a href="#${arch}">${title}</a>`);
    const cards = groups[arch].map(card).join("");
    main.insertAdjacentHTML("beforeend",
      `<section class="category" id="${arch}">
        <h2>${title} <span class="count">${groups[arch].length} shoes</span></h2>
        <div class="grid">${cards}</div>
      </section>`);
  });
}

fetch("data/scores.csv")
  .then((r) => { if (!r.ok) throw new Error(r.status); return r.text(); })
  .then((t) => render(parseCSV(t)))
  .catch((e) => {
    document.getElementById("catalog").innerHTML =
      `<p class="loading">Couldn't load scores.csv (${e.message}). ` +
      `If you opened this file directly, run a local server: ` +
      `<code>python3 -m http.server</code> from the repo root, then visit localhost:8000.</p>`;
  });
