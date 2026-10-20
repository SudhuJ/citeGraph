---
title: India & the world
---

# India & the world

<p class="muted">Who cites our papers, whose work our papers cite, and which Indian institutions our faculty write with. Papers with 100 or more authors are left out.</p>

```js
import {INST, instColor, instVar, shortInst, pct, num, answer, ORIGIN, originLabel, originColor, instName} from "./components/defs.js";
const origin = FileAttachment("data/origin.csv").csv({typed: true});
const conn = FileAttachment("data/connections.csv").csv({typed: true});
const M = FileAttachment("data/network_metrics.json").json();
```

```js
const agg = (dir) => d3.flatRollup(origin.filter((d) => d.direction === dir), (v) => ({n: d3.sum(v, (d) => d.n), india_frac: d3.sum(v, (d) => d.india_frac)}),
  (d) => d.institution, (d) => d.category).map(([institution, category, m]) => ({institution, category, ...m}));
const share = (rows, inst, cats) => d3.sum(rows.filter((d) => d.institution === inst && cats.includes(d.category)), (d) => d.n)
  / d3.sum(rows.filter((d) => d.institution === inst), (d) => d.n);
const fracIndia = (rows, inst, cats) => d3.sum(rows.filter((d) => d.institution === inst && cats.includes(d.category)), (d) => d.india_frac)
  / d3.sum(rows.filter((d) => d.institution === inst), (d) => d.n);
const IN = agg("in"), OUT = agg("out");
const OTHER = ["other Indian only", "India + abroad"];
const originChart = (rows) => resize((width) => Plot.plot({width,
  height: 140, marginLeft: 100, x: {percent: true, label: "share of citation links (%)"}, y: {label: null, domain: INST},
  color: {...originColor, legend: true, tickFormat: (c) => originLabel[c]},
  marks: [Plot.barX(rows, Plot.stackX({offset: "normalize", order: ORIGIN, x: "n", y: "institution", fill: "category", inset: 1,
    tip: {format: {x: false}}, title: (d) => `${d.institution}\n${originLabel[d.category]}: ${num(d.n)} links`}))]
}));
```

## Who cites our work?

${answer(html`Mostly researchers abroad. ${INST.map((i) => `${pct(share(IN, i, ["abroad or unknown"]))} of ${shortInst(i)}'s citations come from papers with no Indian author or no affiliation data`).join(", and ")}. Other Indian institutes give ${INST.map((i) => `${pct(share(IN, i, OTHER))} (${shortInst(i)})`).join(" and ")}, about as much as the authors' own self-citations (${INST.map((i) => `${pct(share(IN, i, ["self"]))}`).join(" and ")}). Colleagues at the same IISER who are not co-authors give only ${INST.map((i) => pct(share(IN, i, ["own institute"]), 1)).join(" and ")}.`)}

```js
display(originChart(IN));
```

## Whose work do we cite?

${answer(html`Overwhelmingly foreign work. ${INST.map((i) => `${pct(share(OUT, i, ["abroad or unknown"]))} of ${shortInst(i)}'s references point to papers with no Indian author or no affiliation data`).join(", and ")}. References to other Indian institutes make up ${INST.map((i) => `${pct(share(OUT, i, OTHER))} (${shortInst(i)})`).join(" and ")}.`)}

```js
display(originChart(OUT));
```

<p class="caveat">"No Indian author, or unknown" is a remainder: total citations (or references) minus the Indian ones we fetched. It includes papers whose affiliations OpenAlex has not parsed. The incoming and outgoing shares are comparable, but raw counts are not: references can point to work of any year, while citations can only reach our 2016–26 papers.</p>
<details class="how"><summary>How it's computed</summary>
<p>Every citation link goes into the first category that fits:</p>
<ol>
<li><b>Self-citation:</b> the two papers share an author.</li>
<li><b>Same IISER:</b> the other paper has an author at the same institute, but no shared author.</li>
<li><b>Indian and foreign authors:</b> the other paper has both. Papers with 100+ authors also go here, since their author lists are truncated.</li>
<li><b>Other Indian institutes only:</b> all of the other paper's authors are in India.</li>
<li><b>No Indian author, or unknown:</b> everything else. OpenAlex gives the total, and we subtract the Indian links.</li>
</ol>
<p>Fractional counting is a check on the categories. If each citing paper is split by the share of its authors who are in India, India accounts for ${INST.map((i) => `${pct(fracIndia(IN, i, ORIGIN))} of ${shortInst(i)}'s citations`).join(" and ")}, self-citations included.</p>
</details>

## Is the Indian share changing?

```js
const byYear = d3.flatRollup(origin.filter((d) => d.direction === "in" && d.year <= 2025), (v) => ({
  other: d3.sum(v.filter((d) => OTHER.includes(d.category)), (d) => d.n), all: d3.sum(v, (d) => d.n)}),
  (d) => d.institution, (d) => d.year).map(([institution, year, m]) => ({institution, year, share: m.other / m.all, ...m}));
const first = (i) => byYear.find((d) => d.institution === i && d.year === 2016)?.share;
const last = (i) => byYear.find((d) => d.institution === i && d.year === 2025)?.share;
```

${answer(html`${INST.every((i) => Math.abs(last(i) - first(i)) < 0.05) ? "Not much." : "Somewhat."} For papers published in 2016, other Indian institutes gave ${INST.map((i) => `${pct(first(i))} of the citations (${shortInst(i)})`).join(" and ")}. For papers published in 2025 the figure is ${INST.map((i) => `${pct(last(i))} (${shortInst(i)})`).join(" and ")}. Recent papers have few citations so far, so the last points are noisy.`)}

```js
display(resize((width) => Plot.plot({width,
  height: 260, marginLeft: 44, x: {label: "publication year of our paper", tickFormat: "d"}, y: {grid: true, percent: true, label: "citations from other Indian institutes (%)", zero: true},
  color: instColor,
  marks: [
    Plot.line(byYear, {x: "year", y: "share", stroke: "institution", strokeWidth: 2}),
    Plot.dot(byYear, {x: "year", y: "share", fill: "institution", r: 4, stroke: "var(--theme-background)", strokeWidth: 2, tip: true,
      title: (d) => `${d.institution} · papers from ${d.year}\n${num(d.other)} of ${num(d.all)} citations from other Indian institutes`})
  ]
})));
```

## Who do we write with in India?

```js
const pick = view(Inputs.radio(INST, {value: "IISER Pune", label: "Institute"}));
```

```js
const C = conn.filter((d) => d.your_inst === pick);
const partners = C.filter((d) => d.shared_papers > 0);
const top = partners.toSorted((a, b) => b.shared_papers - a.shared_papers).slice(0, 20);
const byCluster = d3.rollups(partners, (v) => d3.sum(v, (d) => d.shared_papers), (d) => d.partner_cluster)
  .map(([cluster, papers]) => ({cluster, papers})).sort((a, b) => b.papers - a.papers);
const crossShare = d3.sum(partners.filter((d) => d.cross_cluster), (d) => d.shared_papers) / d3.sum(partners, (d) => d.shared_papers);
```

${answer(html`${shortInst(pick)} faculty co-authored with ${partners.length} Indian institutions. The strongest partners are ${top.slice(0, 3).map((d) => `${instName(d.partner_inst)} (${d.shared_papers} papers)`).join(", ")}, so nearby institutions rank high. ${pct(crossShare)} of joint papers are with institutions outside the IISc · TIFR · IISER cluster.`)}

<div class="grid grid-cols-2">
<div class="card">

### Top 20 co-author institutions

```js
display(resize((width) => Plot.plot({
  width, height: 560, marginLeft: 240, x: {grid: true, label: "joint papers"},
  y: {label: null, domain: top.map((d) => d.partner_inst)},
  marks: [
    Plot.barX(top, {x: "shared_papers", y: "partner_inst", fill: instVar(pick), tip: true,
      title: (d) => `${d.partner_inst} (${d.partner_cluster})\n${d.shared_papers} joint papers · cited us ${d.cites_in}× · we cited ${d.cites_out}×`}),
    Plot.text(top, {x: "shared_papers", y: "partner_inst", text: (d) => d.partner_cluster, dx: 6, textAnchor: "start", fill: "var(--theme-foreground-muted)", fontSize: 10}),
    Plot.ruleX([0])
  ]
})));
```
</div>
<div class="card">

### Joint papers by partner cluster

```js
display(resize((width) => Plot.plot({
  width, height: 340, marginLeft: 170, x: {grid: true, label: "joint papers (one per partner institution)"}, y: {label: null, domain: byCluster.map((d) => d.cluster)},
  marks: [Plot.barX(byCluster, {x: "papers", y: "cluster", fill: instVar(pick), tip: true}), Plot.ruleX([0])]
})));
```
</div>
</div>

<p class="caveat">Some partners are umbrella bodies rather than labs: Homi Bhabha National Institute (DAE institutes), the Academy of Scientific and Innovative Research and the CSIR headquarters record overlap with the labs they cover. A paper with three partner institutions counts once for each.</p>

## Which Indian institutes cite our work most?

```js
const tc = M.citation.top_citing_institutes.filter((d) => d.institution === pick);
```

${answer(html`${instName(tc[0]?.partner)} cites ${shortInst(pick)}'s work most often (${num(tc[0]?.citations)} citation links, self-citations excluded), followed by ${tc.slice(1, 3).map((d) => instName(d.partner)).join(" and ")}.`)}

```js
display(resize((width) => Plot.plot({
  width, height: 340, marginLeft: 240, x: {grid: true, label: "citation links to our papers (no shared author)"}, y: {label: null, domain: tc.map((d) => d.partner)},
  marks: [Plot.barX(tc, {x: "citations", y: "partner", fill: instVar(pick), tip: true, title: (d) => `${d.partner} (${d.cluster}): ${d.citations}`}), Plot.ruleX([0])]
})));
```

```js
display(Inputs.table(M.citation.top_citing_papers.filter((d) => d.institution === pick), {
  columns: ["title", "year", "corpus_papers_cited", "insts"],
  header: {title: "Indian paper citing us", year: "Year", corpus_papers_cited: "Our papers it cites", insts: "Its institutes"},
  format: {year: (x) => x}, width: {title: 380, insts: 260}, layout: "auto", select: false
}));
```

## Do shared research topics go with collaboration?

```js
const sim = C.filter((d) => d.jaccard_topics != null && d.shared_papers >= 3);
const rank = (xs) => { const s = xs.map((x, i) => [x, i]).sort((a, b) => a[0] - b[0]); const r = []; s.forEach(([, i], k) => (r[i] = k)); return r; };
const rho = (() => {
  if (sim.length < 5) return null;
  const a = rank(sim.map((d) => d.jaccard_topics)), b = rank(sim.map((d) => d.shared_papers));
  const ma = d3.mean(a), mb = d3.mean(b);
  return d3.sum(a, (x, i) => (x - ma) * (b[i] - mb)) / Math.sqrt(d3.sum(a, (x) => (x - ma) ** 2) * d3.sum(b, (y) => (y - mb) ** 2));
})();
```

${rho == null
  ? answer(html`Topic profiles are not loaded yet (run <code>make topics</code>), so this question is open.`)
  : answer(html`${rho < 0.2 ? "Hardly" : rho < 0.5 ? "Moderately" : "Strongly"}. Among partners with at least 3 joint papers, topic similarity and number of joint papers have a Spearman correlation of ${rho.toFixed(2)}. Topic overlap explains only part of who writes with whom.`)}

```js
display(sim.length === 0 ? html`` : resize((width) => Plot.plot({
  width, height: 340, x: {label: "topic similarity (Jaccard of research subfields)", grid: true, domain: [0, 1]},
  y: {type: "log", label: "joint papers (log)", grid: true},
  marks: [Plot.dot(sim, {x: "jaccard_topics", y: "shared_papers", r: 4, fill: instVar(pick), stroke: "var(--theme-background)", tip: true,
    title: (d) => `${d.partner_inst} (${d.partner_cluster})\nJaccard ${d3.format(".2f")(d.jaccard_topics)} · ${d.shared_papers} joint papers`}),
    Plot.text(sim.toSorted((a, b) => b.shared_papers - a.shared_papers).slice(0, 6), {x: "jaccard_topics", y: "shared_papers", text: "partner_inst", dy: -9, fontSize: 10, fill: "var(--theme-foreground-muted)"})]
})));
```

<details class="how"><summary>How it's computed</summary>
<p>For each institution we take the OpenAlex subfields that make up at least 0.5% of its 2016–26 papers. The Jaccard similarity of two institutions is the number of subfields they share divided by the number either has.</p>
</details>

## All partner institutions

```js
const qs = view(Inputs.search(C, {placeholder: "Search institutions…", columns: ["partner_inst", "partner_full_name", "partner_cluster"]}));
```

```js
display(Inputs.table(qs, {columns: ["partner_inst", "partner_cluster", "cross_cluster", "shared_papers", "cites_in", "cites_out", "jaccard_topics"],
  header: {partner_inst: "Partner", partner_cluster: "Cluster", cross_cluster: "Cross-cluster", shared_papers: "Joint papers",
           cites_in: "Cites us", cites_out: "We cite", jaccard_topics: "Topic Jaccard"},
  format: {cross_cluster: (x) => (x ? "yes" : ""), jaccard_topics: (x) => (x == null ? "—" : d3.format(".2f")(x))},
  sort: "shared_papers", reverse: true, rows: 15, layout: "auto"}));
```
