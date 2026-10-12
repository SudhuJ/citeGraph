---
title: Overview
toc: false
---

# IISER Pune & IISER Kolkata, 2016–2026

<p class="muted">DPCN 2026 · Group 19. Every paper by a current regular faculty member, written while they were affiliated with the institute (OpenAlex). Pick an institute to filter every panel on this page.</p>

```js
const papers = FileAttachment("data/papers.csv").csv({typed: true});
const faculty = FileAttachment("data/faculty.csv").csv({typed: true});
const INST = ["IISER Pune", "IISER Kolkata"];
const instColor = {domain: INST, range: ["var(--pune)", "var(--kolkata)"], legend: true};
```

```js
const pick = view(Inputs.radio(["Both", ...INST], {value: "Both", label: "Institute"}));
const noHyper = view(Inputs.toggle({label: "Exclude ≥100-author collaboration papers", value: false}));
```

```js
const P = papers.filter((d) => (pick === "Both" || d.institution === pick) && !(noHyper && d.hyperauthored));
const F = faculty.filter((d) => pick === "Both" || d.institution === pick);
const shown = pick === "Both" ? INST : [pick];
const ranked = P.filter((d) => /^Q[1-4]$/.test(d.quartile ?? ""));
```

<div class="grid grid-cols-4">
  ${shown.map((inst) => {
    const p = P.filter((d) => d.institution === inst), f = F.filter((d) => d.institution === inst);
    const q = p.filter((d) => /^Q[1-4]$/.test(d.quartile ?? ""));
    return html`<div class="card"><h2><span class="swatch" style="background:var(${inst === "IISER Pune" ? "--pune" : "--kolkata"})"></span>${inst}</h2>
      <div class="big">${p.length.toLocaleString()}</div><div class="muted">papers · ${d3.sum(p, (d) => d.citations).toLocaleString()} citations</div>
      <div class="muted">${f.filter((d) => d.papers > 0).length} of ${f.length} faculty with papers · median h-index ${d3.median(f, (d) => d.h_index)}</div>
      <div class="muted">Q1 share: ${q.length ? d3.format(".0%")(q.filter((d) => d.quartile === "Q1").length / q.length) : "— (add SCImago files)"}</div></div>`;
  })}
</div>

<div class="grid grid-cols-2">
<div class="card">

## Publication trend

```js
const trend = d3.flatRollup(P, (v) => v.length, (d) => d.institution, (d) => d.year)
  .map(([institution, year, papers]) => ({institution, year, papers}));
display(resize((width) => Plot.plot({width,
  height: 300, marginLeft: 44, x: {label: null, tickFormat: "d", ticks: 11}, y: {grid: true, label: "papers"},
  color: instColor,
  marks: [
    Plot.ruleY([0], {stroke: "var(--theme-foreground-faint)"}),
    Plot.line(trend, {x: "year", y: "papers", stroke: "institution", strokeWidth: 2}),
    Plot.dot(trend, {x: "year", y: "papers", fill: "institution", r: 4, stroke: "var(--theme-background)", strokeWidth: 2}),
    Plot.ruleX(trend, Plot.pointerX({x: "year", stroke: "var(--theme-foreground-faint)"})),
    Plot.tip(trend, Plot.pointer({x: "year", y: "papers", title: (d) => `${d.institution}\n${d.year}: ${d.papers} papers`}))
  ]
})));
```
<p class="muted">2026 is a partial year (data collected Oct 2026).</p>
</div>
<div class="card">

## Journal quartile distribution

```js
const qOrder = ["Q1", "Q2", "Q3", "Q4", "unranked"];
const qRows = d3.flatRollup(P.filter((d) => d.type === "journal"), (v) => v.length, (d) => d.institution,
  (d) => (/^Q[1-4]$/.test(d.quartile ?? "") ? d.quartile : "unranked"))
  .map(([institution, quartile, n]) => ({institution, quartile, n}));
display(ranked.length === 0
  ? html`<p class="muted">No SCImago files in <code>ref/scimago/</code> yet, so quartiles are empty. Re-run <code>make data</code> after adding them.</p>`
  : resize((width) => Plot.plot({width,
      height: 160, marginLeft: 100, x: {percent: true, label: "share of journal papers (%)"}, y: {label: null},
      color: {domain: qOrder, range: ["var(--q1)", "var(--q2)", "var(--q3)", "var(--q4)", "var(--qna)"], legend: true},
      marks: [
        Plot.barX(qRows, Plot.stackX({offset: "normalize", order: qOrder, x: "n", y: "institution", fill: "quartile",
          inset: 1, tip: {format: {x: false}}, title: (d) => `${d.institution} · ${d.quartile}: ${d.n} papers`}))
      ]
    })));
```
</div>
</div>

<div class="grid grid-cols-2">
<div class="card">

## Research area breakdown

```js
const fieldRows = d3.flatRollup(P, (v) => v.length, (d) => d.institution, (d) => d.field ?? "Unclassified")
  .map(([institution, field, n]) => ({institution, field, n,
    share: n / P.filter((p) => p.institution === institution).length}));
const topFields = d3.groupSort(fieldRows, (v) => -d3.sum(v, (d) => d.n), (d) => d.field).slice(0, 12);
display(resize((width) => Plot.plot({width,
  height: 420, marginLeft: 210, x: {percent: true, grid: true, label: "share of the institute's papers (%)"},
  fy: {domain: topFields, label: null}, y: {domain: shown, axis: null}, color: instColor,
  marks: [
    Plot.barX(fieldRows.filter((d) => topFields.includes(d.field)), {x: "share", y: "institution", fy: "field",
      fill: "institution", tip: true, title: (d) => `${d.institution}\n${d.field}: ${d.n} papers (${d3.format(".1%")(d.share)})`}),
    Plot.ruleX([0])
  ]
})));
```
<p class="muted">OpenAlex field of each paper's primary topic; top 12 fields.</p>
</div>
<div class="card">

## Top journals

```js
const topJ = shown.flatMap((inst) =>
  d3.rollups(P.filter((d) => d.institution === inst && d.journal_name), (v) => v.length, (d) => d.journal_name)
    .sort((a, b) => b[1] - a[1]).slice(0, 5).map(([journal, n], i) => ({institution: inst, rank: i + 1, journal, n})));
display(resize((width) => Plot.plot({width,
  height: 60 + 34 * topJ.length, marginLeft: 270, x: {grid: true, label: "papers"},
  y: {domain: topJ.map((d) => `${d.institution === "IISER Pune" ? "Pune" : "Kolkata"} · ${d.journal}`), label: null},
  color: instColor,
  marks: [
    Plot.barX(topJ, {y: (d) => `${d.institution === "IISER Pune" ? "Pune" : "Kolkata"} · ${d.journal}`, x: "n",
      fill: "institution", tip: true}),
    Plot.text(topJ, {y: (d) => `${d.institution === "IISER Pune" ? "Pune" : "Kolkata"} · ${d.journal}`, x: "n",
      text: "n", dx: 4, textAnchor: "start", fill: "var(--theme-foreground-muted)"}),
    Plot.ruleX([0])
  ]
})));
```
</div>
</div>
