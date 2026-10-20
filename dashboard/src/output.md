---
title: Output & venues
---

# Output & venues

```js
import {INST, instColor, shortInst, pct, num, answer, isTopJournal, TOP_JOURNAL_RULE, hasQuartiles, measure} from "./components/defs.js";
const papers = FileAttachment("data/papers.csv").csv({typed: true});
const faculty = FileAttachment("data/faculty.csv").csv({typed: true});
```

```js
const pick = view(Inputs.radio(["Both", ...INST], {value: "Both", label: "Institute"}));
```

```js
const all = papers.filter((d) => !d.hyperauthored);
const P = all.filter((d) => pick === "Both" || d.institution === pick);
const shown = pick === "Both" ? INST : [pick];
const quartilesLoaded = hasQuartiles(all);
```

## Is output growing?

```js
const trend = d3.flatRollup(P, (v) => v.length, (d) => d.institution, (d) => d.year)
  .map(([institution, year, papers]) => ({institution, year, papers}));
// faculty counted as active from the year of their first paper here (current faculty only)
const active = (inst, y) => faculty.filter((f) => f.institution === inst && f.first_year != null && f.first_year <= y).length;
const perFac = trend.map((d) => ({...d, active: active(d.institution, d.year), per_faculty: d.papers / active(d.institution, d.year)}));
const rise = (inst, key) => {
  const r = (y) => perFac.find((d) => d.institution === inst && d.year === y)?.[key];
  return r(2025) / r(2016) - 1;
};
```

${measure(html`Papers per year at each institute, and the same divided by the number of current faculty who had published here by that year.`)}

${answer(html`Yes. From 2016 to 2025 yearly output grew ${shown.map((i) => `${pct(rise(i, "papers"))} at ${shortInst(i)}`).join(" and ")}. Per active faculty member the change is ${shown.map((i) => `${pct(rise(i, "per_faculty"))} at ${shortInst(i)}`).join(" and ")}, so most of the growth comes from more people publishing rather than each person publishing more.`)}

<div class="grid grid-cols-2">
<div class="card">

### Papers per year

```js
display(resize((width) => Plot.plot({width,
  height: 280, marginLeft: 44, x: {label: null, tickFormat: "d", ticks: 11}, y: {grid: true, label: "papers"},
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
</div>
<div class="card">

### Papers per active faculty member

```js
display(resize((width) => Plot.plot({width,
  height: 280, marginLeft: 44, x: {label: null, tickFormat: "d", ticks: 11}, y: {grid: true, label: "papers per faculty", zero: true},
  color: instColor,
  marks: [
    Plot.line(perFac, {x: "year", y: "per_faculty", stroke: "institution", strokeWidth: 2}),
    Plot.dot(perFac, {x: "year", y: "per_faculty", fill: "institution", r: 4, stroke: "var(--theme-background)", strokeWidth: 2}),
    Plot.ruleX(perFac, Plot.pointerX({x: "year", stroke: "var(--theme-foreground-faint)"})),
    Plot.tip(perFac, Plot.pointer({x: "year", y: "per_faculty",
      title: (d) => `${d.institution} · ${d.year}\n${d.papers} papers by ${d.active} active faculty = ${d.per_faculty.toFixed(2)}`}))
  ]
})));
```
</div>
</div>

<p class="caveat">We only track faculty on today's rosters, so the early years miss people who have since left. 2026 is a partial year (data collected October 2026).</p>
<details class="how"><summary>How it's computed</summary>
<p>Papers are counted once per institute per year. A faculty member counts as active from the year of their first paper in this dataset, which approximates their joining year.</p>
</details>

## How good are the venues?

```js
const qOrder = ["Q1", "Q2", "Q3", "Q4", "unranked"];
const journals = P.filter((d) => d.type === "journal");
const qRows = d3.flatRollup(journals, (v) => v.length, (d) => d.institution,
  (d) => (/^Q[1-4]$/.test(d.quartile ?? "") ? d.quartile : "unranked"))
  .map(([institution, quartile, n]) => ({institution, quartile, n}));
const share = (inst, f) => {
  const r = journals.filter((d) => d.institution === inst && /^Q[1-4]$/.test(d.quartile ?? ""));
  return r.length ? r.filter(f).length / r.length : null;
};
```

${measure(html`For journal papers, the SCImago quartile of the venue: Q1 means the journal is in the top quarter of its subject category by SJR, a citation-based prestige score. The stricter bar also needs an impact-factor proxy above 5.`)}

${quartilesLoaded
  ? answer(html`${shown.map((i) => `${pct(share(i, (d) => d.quartile === "Q1"))} of ${shortInst(i)}'s ranked journal papers are in Q1 venues`).join(", and ")}. Using the stricter bar of Q1 with an impact-factor proxy above 5, the share is ${shown.map((i) => `${pct(share(i, isTopJournal))} (${shortInst(i)})`).join(" and ")}.`)
  : answer(html`SCImago files are not loaded yet, so quartiles are empty. Add them to <code>ref/scimago/</code> and rebuild.`)}

```js
display(!quartilesLoaded ? html`` : resize((width) => Plot.plot({width,
  height: 50 + 50 * shown.length, marginLeft: 100, x: {percent: true, label: "share of journal papers (%)"}, y: {label: null},
  color: {domain: qOrder, range: ["var(--q1)", "var(--q2)", "var(--q3)", "var(--q4)", "var(--qna)"], legend: true},
  marks: [
    Plot.barX(qRows, Plot.stackX({offset: "normalize", order: qOrder, x: "n", y: "institution", fill: "quartile",
      inset: 1, tip: {format: {x: false}}, title: (d) => `${d.institution} · ${d.quartile}: ${d.n} papers`}))
  ]
})));
```

<p class="caveat">SCImago's "best quartile" is the best rank a journal holds in any of its subject categories. A journal that is Q1 in one category and Q3 in another counts as Q1, so these shares are an upper bound. The impact factor itself is not open data, so we use SCImago's citations per document over two years, which is computed the same way but from Scopus. Citation rates differ by field, so the IF&gt;5 bar is far easier to clear in chemistry and materials than in mathematics, where even the leading journals sit below 5.</p>
<details class="how"><summary>How it's computed</summary>
<p>Each paper takes its journal's quartile for the SCImago year closest to, and not after, its publication year, matched by ISSN. "Unranked" means the venue is not in SCImago. Conference papers use the CORE rank instead; ${all.filter((d) => d.type === "conference").length} papers are conference papers, ${all.filter((d) => ["A*", "A", "B", "C"].includes(d.quartile)).length} of them in CORE-ranked venues.</p>
</details>

<div class="grid grid-cols-2">
<div class="card">

## Where do they publish most?

```js
const topJ = shown.flatMap((inst) =>
  d3.rollups(P.filter((d) => d.institution === inst && d.journal_name), (v) => v.length, (d) => d.journal_name)
    .sort((a, b) => b[1] - a[1]).slice(0, 5).map(([journal, n]) => ({institution: inst, journal, n, key: `${shortInst(inst)} · ${journal}`})));
display(resize((width) => Plot.plot({width,
  height: 50 + 30 * topJ.length, marginLeft: 280, x: {grid: true, label: "papers"},
  y: {domain: topJ.map((d) => d.key), label: null}, color: instColor,
  marks: [
    Plot.barX(topJ, {y: "key", x: "n", fill: "institution", tip: true}),
    Plot.text(topJ, {y: "key", x: "n", text: "n", dx: 4, textAnchor: "start", fill: "var(--theme-foreground-muted)"}),
    Plot.ruleX([0])
  ]
})));
```
<p class="muted">Top 5 journals by number of papers, per institute.</p>
</div>
<div class="card">

## What do they work on?

```js
const fieldRows = d3.flatRollup(P, (v) => v.length, (d) => d.institution, (d) => d.field ?? "Unclassified")
  .map(([institution, field, n]) => ({institution, field, n, share: n / P.filter((p) => p.institution === institution).length}));
const topFields = d3.groupSort(fieldRows, (v) => -d3.sum(v, (d) => d.n), (d) => d.field).slice(0, 10);
display(resize((width) => Plot.plot({width,
  height: 380, marginLeft: 210, x: {percent: true, grid: true, label: "share of the institute's papers (%)"},
  fy: {domain: topFields, label: null}, y: {domain: shown, axis: null}, color: instColor,
  marks: [
    Plot.barX(fieldRows.filter((d) => topFields.includes(d.field)), {x: "share", y: "institution", fy: "field",
      fill: "institution", tip: true, title: (d) => `${d.institution}\n${d.field}: ${d.n} papers (${d3.format(".1%")(d.share)})`}),
    Plot.ruleX([0])
  ]
})));
```
<p class="muted">OpenAlex field of each paper's main topic; top 10 fields.</p>
</div>
</div>

## Which papers stand out?

```js
const top30 = (rows) => d3.groups(rows, (d) => d.work_id)
  .map(([, v]) => ({...v[0], institution: v.map((d) => shortInst(d.institution)).join(" & ")}))
  .sort((a, b) => b.citations - a.citations).slice(0, 30);
const tableOpts = {
  columns: ["title", "journal_name", "year", "citations", "institution", "doi"],
  header: {title: "Title", journal_name: "Journal", year: "Year", citations: "Citations", institution: "Institute", doi: "DOI"},
  format: {doi: (x) => (x ? html`<a href=${x} target="_blank">${x.replace("https://doi.org/", "")}</a>` : "—"), year: (x) => x},
  width: {title: 420, journal_name: 200}, layout: "auto", rows: 12, sort: "citations", reverse: true, select: false
};
const byCites = top30(P);
const byVenue = top30(P.filter(isTopJournal));
```

${measure(html`Each paper's total citation count in OpenAlex at the time of collection (October 2026).`)}

${answer(html`The 30 most-cited papers are ${pct(byCites.filter((d) => d.year <= 2019).length / byCites.length)} from 2016–2019. Citation counts favour older papers, which have had longer to be cited.`)}

### Top 30 by citations

```js
display(Inputs.table(byCites, tableOpts));
```

### Top 30 in top journals

<p class="muted">Papers in journals that meet the rule "${TOP_JOURNAL_RULE}", ranked by citations. The rule favours high-citation fields, so ${byVenue.filter((d) => ["Chemistry", "Materials Science", "Engineering"].includes(d.field)).length} of these ${byVenue.length} are chemistry, materials science or engineering papers.</p>

```js
display(quartilesLoaded ? Inputs.table(byVenue, tableOpts) : html`<p class="muted">Needs the SCImago files.</p>`);
```

<details class="how"><summary>How it's computed</summary>
<p>Citation counts are OpenAlex's totals at collection time. A paper written by faculty at both institutes appears once, with both institutes named.</p>
</details>

## All papers

```js
const q = view(Inputs.search(P, {placeholder: "Search titles, journals…", columns: ["title", "journal_name", "field"]}));
```

```js
display(Inputs.table(q, {columns: ["title", "year", "journal_name", "type", "quartile", "if_proxy", "citations", "n_authors", "institution"],
  header: {if_proxy: "IF proxy", n_authors: "authors"},
  format: {year: (x) => x, if_proxy: (x) => (x == null ? "—" : x.toFixed(1))}, width: {title: 360}, layout: "auto", rows: 15}));
```
