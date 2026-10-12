---
title: Faculty
---

# Faculty

```js
const faculty = FileAttachment("data/faculty.csv").csv({typed: true});
const INST = ["IISER Pune", "IISER Kolkata"];
const instColor = {domain: INST, range: ["var(--pune)", "var(--kolkata)"], legend: true};
```

```js
const pick = view(Inputs.radio(["Both", ...INST], {value: "Both", label: "Institute"}));
```

```js
const depts = [...new Set(faculty.filter((d) => pick === "Both" || d.institution === pick).map((d) => d.department))].sort();
const dept = view(Inputs.select(["All departments", ...depts], {label: "Department"}));
```

```js
const F = faculty.filter((d) => (pick === "Both" || d.institution === pick) && (dept === "All departments" || d.department === dept));
const q = view(Inputs.search(F, {placeholder: "Search faculty…"}));
```

## Faculty performance

<p class="muted">Click a column header to sort. <b>h-index (2016–26)</b> is computed from the papers in this dataset; <b>lifetime</b> is OpenAlex's career h-index. Two IISER Pune physicists (CMS collaboration) have ~750 papers with hundreds of authors each, so check the "≥100-author papers" column before comparing counts.</p>

```js
display(Inputs.table(q, {
  columns: ["name", "institution", "department", "designation", "papers", "citations", "h_index", "h_index_lifetime", "q1_share", "top_journal", "hyper_papers"],
  header: {name: "Name", institution: "Institute", department: "Department", designation: "Designation", papers: "Papers",
           citations: "Citations", h_index: "h-index (2016–26)", h_index_lifetime: "h-index (lifetime)", q1_share: "Q1 share",
           top_journal: "Top journal", hyper_papers: "≥100-author papers"},
  format: {q1_share: (x) => (x == null ? "—" : d3.format(".0%")(x)), name: (x, i, data) => html`<a href=${data[i].profile_url} target="_blank">${x}</a>`},
  width: {name: 190, department: 170, designation: 180, top_journal: 220},
  sort: "papers", reverse: true, rows: 18, layout: "auto"
}));
```

<div class="grid grid-cols-2">
<div class="card">

## h-index distribution

```js
display(resize((width) => Plot.plot({
  width, height: 300, x: {label: "h-index (2016–2026 window)"}, y: {grid: true, label: "faculty"},
  color: instColor, fy: {label: null},
  marks: [
    Plot.rectY(F, Plot.binX({y: "count"}, {x: "h_index", fill: "institution", fy: "institution", interval: 2, inset: 1, tip: true})),
    Plot.ruleY([0])
  ]
})));
```
</div>
<div class="card">

## Papers vs citations per faculty

```js
display(resize((width) => Plot.plot({
  width, height: 300, x: {type: "log", label: "papers (log)", grid: true}, y: {type: "log", label: "citations (log)", grid: true},
  color: instColor,
  marks: [
    Plot.dot(F.filter((d) => d.papers > 0 && d.citations > 0), {x: "papers", y: "citations", fill: "institution", r: 4,
      stroke: "var(--theme-background)", tip: true, title: (d) => `${d.name}\n${d.department}\n${d.papers} papers · ${d.citations} citations · h=${d.h_index}`})
  ]
})));
```
</div>
</div>

## Department summary

```js
const deptRows = d3.flatRollup(F, (v) => ({
  faculty: v.length, papers: d3.sum(v, (d) => d.papers), citations: d3.sum(v, (d) => d.citations),
  median_h: d3.median(v, (d) => d.h_index), papers_per_faculty: d3.sum(v, (d) => d.papers) / v.length
}), (d) => d.institution, (d) => d.department).map(([institution, department, m]) => ({institution, department, ...m}));
display(Inputs.table(deptRows, {sort: "papers", reverse: true, format: {papers_per_faculty: d3.format(".1f")},
  header: {papers_per_faculty: "papers / faculty", median_h: "median h"}}));
```
