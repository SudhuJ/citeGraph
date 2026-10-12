---
title: Papers & venues
---

# Papers & venues

```js
const papers = FileAttachment("data/papers.csv").csv({typed: true});
const INST = ["IISER Pune", "IISER Kolkata"];
const instColor = {domain: INST, range: ["var(--pune)", "var(--kolkata)"], legend: true};
```

```js
const pick = view(Inputs.radio(["Both", ...INST], {value: "Both", label: "Institute"}));
const noHyper = view(Inputs.toggle({label: "Exclude ≥100-author collaboration papers", value: true}));
```

```js
const P = papers.filter((d) => (pick === "Both" || d.institution === pick) && !(noHyper && d.hyperauthored));
```

## Most-cited papers (top 10)

<p class="muted">Citation counts from OpenAlex at collection date. Collaboration papers are hidden by default because they would fill the whole list.</p>

```js
const top = d3.groups(P, (d) => d.work_id).map(([, v]) => ({...v[0], institution: v.map((d) => d.institution).join(" & ")}))
  .sort((a, b) => b.citations - a.citations).slice(0, 10);
display(Inputs.table(top, {
  columns: ["title", "journal_name", "year", "citations", "institution", "doi"],
  header: {title: "Title", journal_name: "Journal", year: "Year", citations: "Citations", institution: "Institute", doi: "DOI"},
  format: {doi: (x) => (x ? html`<a href=${x} target="_blank">${x.replace("https://doi.org/", "")}</a>` : "—"), year: (x) => x},
  width: {title: 380, journal_name: 200}, layout: "auto", rows: 10, sort: "citations", reverse: true
}));
```

<div class="grid grid-cols-2">
<div class="card">

## Journal vs conference

```js
const types = d3.flatRollup(P, (v) => v.length, (d) => d.institution, (d) => d.type).map(([institution, type, n]) => ({institution, type, n}));
display(resize((width) => Plot.plot({
  width, height: 160, marginLeft: 100, x: {grid: true, label: "papers"}, y: {label: null}, fy: {label: null},
  color: instColor,
  marks: [Plot.barX(types, {x: "n", y: "type", fy: "institution", fill: "institution", tip: true}), Plot.ruleX([0])]
})));
```
<p class="muted">IISERs publish overwhelmingly in journals. Conference papers are mostly physics/chemistry proceedings.</p>
</div>
<div class="card">

## Conference rank (CORE)

```js
const confs = P.filter((d) => d.type === "conference");
const ranks = d3.rollups(confs, (v) => v.length, (d) => (["A*", "A", "B", "C"].includes(d.quartile) ? d.quartile : "not in CORE"))
  .map(([rank, n]) => ({rank, n}));
display(resize((width) => Plot.plot({
  width, height: 200, marginLeft: 90, x: {grid: true, label: "conference papers"}, y: {domain: ["A*", "A", "B", "C", "not in CORE"], label: null},
  marks: [Plot.barX(ranks, {x: "n", y: "rank", fill: "var(--q2)", tip: true}), Plot.ruleX([0])]
})));
```
<p class="muted">The CORE portal ranks computer-science venues only. Add <code>ref/core.csv</code> (CORE export) to fill the A*/A/B/C bars. For IISER papers most venues are outside CORE's scope.</p>
</div>
</div>

## All papers

```js
const q = view(Inputs.search(P, {placeholder: "Search titles, journals…", columns: ["title", "journal_name", "field"]}));
```

```js
display(Inputs.table(q, {columns: ["title", "year", "journal_name", "type", "quartile", "citations", "field", "institution"],
  format: {year: (x) => x}, width: {title: 360}, layout: "auto", rows: 15}));
```
