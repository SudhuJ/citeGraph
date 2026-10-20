---
title: Big collaborations
---

# Big collaborations (100+ authors)

<p class="muted">Particle-physics and gravitational-wave experiments publish papers with hundreds or thousands of authors. OpenAlex cuts author lists at 100, so we cannot check who on these papers was at an IISER, and one person's paper count can run into the hundreds. We keep these papers in the deliverable CSVs, flagged <code>hyperauthored</code>, and leave them out of every other page. This page shows what they are and what they would change.</p>

```js
import {INST, instColor, shortInst, pct, num, answer} from "./components/defs.js";
const papers = FileAttachment("data/papers.csv").csv({typed: true});
const faculty = FileAttachment("data/faculty.csv").csv({typed: true});
const conn = FileAttachment("data/connections.csv").csv({typed: true});
const M = FileAttachment("data/network_metrics.json").json();
```

```js
const H = papers.filter((d) => d.hyperauthored);
const hyperIds = new Set(H.map((d) => d.work_id));
const hf = faculty.filter((d) => d.hyper_papers > 0).toSorted((a, b) => b.hyper_papers - a.hyper_papers);
const instShare = (inst) => H.filter((d) => d.institution === inst).length / papers.filter((d) => d.institution === inst).length;
```

## How many are there, and whose are they?

${answer(html`There are ${num(hyperIds.size)} such papers. They would make up ${INST.map((i) => `${pct(instShare(i))} of ${shortInst(i)}'s output`).join(" and ")}. Almost all come from ${hf.slice(0, 2).map((d) => `${d.name} (${num(d.hyper_papers)})`).join(" and ")}, both in the CMS experiment at CERN. Counted in, they would make these two the most "productive" faculty at either institute by a wide margin.`)}

```js
display(Inputs.table(hf, {
  columns: ["name", "institution", "department", "hyper_papers", "hyper_citations", "papers", "h_index"],
  header: {name: "Faculty", institution: "Institute", department: "Department", hyper_papers: "100+ author papers", hyper_citations: "Their citations",
           papers: "Other papers", h_index: "h-index without them"},
  format: {institution: shortInst}, layout: "auto", select: false
}));
```

<div class="grid grid-cols-2">
<div class="card">

### Per year

```js
const perYear = d3.flatRollup(H, (v) => v.length, (d) => d.institution, (d) => d.year).map(([institution, year, n]) => ({institution, year, n}));
display(resize((width) => Plot.plot({width, height: 260, x: {tickFormat: "d", label: null}, y: {grid: true, label: "papers"}, color: instColor,
  marks: [Plot.rectY(perYear, {x: "year", y: "n", fill: "institution", interval: 1, inset: 1, tip: true}), Plot.ruleY([0])]})));
```
</div>
<div class="card">

### Partners they would add

```js
const gain = conn.map((d) => ({...d, added: d.shared_papers_incl_hyper - d.shared_papers})).filter((d) => d.added > 0)
  .toSorted((a, b) => b.added - a.added).slice(0, 10);
display(Inputs.table(gain, {columns: ["your_inst", "partner_inst", "shared_papers", "added"],
  header: {your_inst: "Institute", partner_inst: "Partner", shared_papers: "Joint papers (main analysis)", added: "Added by 100+ author papers"},
  format: {your_inst: shortInst}, layout: "auto", select: false}));
```
</div>
</div>

<p class="caveat">Including these papers would push institutes like Aligarh Muslim University and the Variable Energy Cyclotron Centre near the top of Pune's partner list, through a shared detector collaboration rather than direct work together.</p>

## What would they do to the co-authorship analysis?

```js
const S = M.hyperauthorship;
```

${answer(html`Little to the structure and a lot to the rankings. They connect only ${S.hyper_faculty_pairs} pairs of our faculty (${num(S.hyper_papers_multi_faculty)} papers have two or more of our faculty on them), so the network's shape barely moves: mean degree ${S.without.mean_degree} → ${S.with.mean_degree}. But each of those pairs shares hundreds of papers, so any ranking by number of joint papers would put the CMS members at the top.`)}

```js
display(Inputs.table(S.top_strength_with, {header: {name: "Faculty", papers: "Joint papers with other faculty, 100+ author papers counted"}, select: false}));
```

## Most cited

```js
const top = d3.groups(H, (d) => d.work_id).map(([, v]) => ({...v[0], institution: v.map((d) => shortInst(d.institution)).join(" & ")}))
  .sort((a, b) => b.citations - a.citations).slice(0, 10);
display(Inputs.table(top, {columns: ["title", "journal_name", "year", "citations", "institution"],
  header: {title: "Title", journal_name: "Journal", year: "Year", citations: "Citations", institution: "Institute"},
  format: {year: (x) => x}, width: {title: 420}, layout: "auto", select: false}));
```

## Papers with 11–99 authors

```js
const mid = papers.filter((d) => d.large_team && !d.hyperauthored);
```

${answer(html`These stay in the main analysis. There are ${num(new Set(mid.map((d) => d.work_id)).size)} of them, about ${pct(mid.length / papers.filter((d) => !d.hyperauthored).length)} of the rest. They are spread across fields, led by medicine, physics, molecular biology and materials science. They are flagged <code>large_team</code> in the CSVs, and each department's share is in the "&gt;10 authors" column on <a href="./faculty">Faculty & departments</a>.`)}
