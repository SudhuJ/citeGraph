---
title: Indian connectivity
---

# Indian connectivity

<p class="muted">How IISER Pune and IISER Kolkata sit in the wider Indian research network: who our faculty co-author with, and who we cite and are cited by. Source: <code>indian_connections.csv</code>. Each partner is an OpenAlex institution with an Indian address; clusters follow the course grouping.</p>

```js
const conn = FileAttachment("data/connections.csv").csv({typed: true});
const INST = ["IISER Pune", "IISER Kolkata"];
const instColor = {domain: INST, range: ["var(--pune)", "var(--kolkata)"], legend: true};
```

```js
const pick = view(Inputs.radio(INST, {value: "IISER Pune", label: "Institute"}));
const metric = view(Inputs.radio(["shared_papers", "total_citations"], {value: "shared_papers", label: "Rank partners by",
  format: (m) => (m === "shared_papers" ? "co-authored papers" : "citations exchanged")}));
```

```js
const C = conn.filter((d) => d.your_inst === pick);
const coauthorPartners = C.filter((d) => d.shared_papers > 0);
```

<div class="grid grid-cols-4">
  <div class="card"><h2>Co-author partner institutions</h2><div class="big">${coauthorPartners.length.toLocaleString()}</div><div class="muted">Indian institutions with ≥1 joint paper</div></div>
  <div class="card"><h2>Joint papers (partner-links)</h2><div class="big">${d3.sum(C, (d) => d.shared_papers).toLocaleString()}</div><div class="muted">a paper with 3 partners counts 3×</div></div>
  <div class="card"><h2>Citations in · out</h2><div class="big">${d3.sum(C, (d) => d.cites_in).toLocaleString()} · ${d3.sum(C, (d) => d.cites_out).toLocaleString()}</div><div class="muted">paper-level citation links with Indian institutions</div></div>
  <div class="card"><h2>Cross-cluster partners</h2><div class="big">${d3.format(".0%")(coauthorPartners.filter((d) => d.cross_cluster).length / coauthorPartners.length)}</div><div class="muted">outside the IISc · TIFR · IISER cluster</div></div>
</div>

## Top partner institutions

```js
const top = C.toSorted((a, b) => b[metric] - a[metric]).slice(0, 20);
display(resize((width) => Plot.plot({
  width, height: 560, marginLeft: 260, x: {grid: true, label: metric === "shared_papers" ? "co-authored papers" : "citations exchanged (in + out)"},
  y: {label: null, domain: top.map((d) => d.partner_inst)},
  marks: [
    Plot.barX(top, {x: metric, y: "partner_inst", fill: (d) => (d.cross_cluster ? "var(--context)" : instColor.range[INST.indexOf(pick)]),
      tip: true, title: (d) => `${d.partner_inst} (${d.partner_cluster})\n${d.shared_papers} joint papers · ${d.cites_in} cites in · ${d.cites_out} cites out\ntopic Jaccard ${d.jaccard_topics == null ? "—" : d3.format(".2f")(d.jaccard_topics)}`}),
    Plot.text(top, {x: metric, y: "partner_inst", text: (d) => d.partner_cluster, dx: 6, textAnchor: "start", fill: "var(--theme-foreground-muted)", fontSize: 10}),
    Plot.ruleX([0])
  ]
})));
```
<p class="muted">Bar colour: institute colour = same cluster (IISc · TIFR · IISER); grey = cross-cluster link (IISER ↔ IIT, CSIR, DAE, …). The label gives the partner's cluster.</p>

<div class="grid grid-cols-2">
<div class="card">

## Co-authorship by partner cluster

```js
const byCluster = d3.rollups(C, (v) => ({papers: d3.sum(v, (d) => d.shared_papers), partners: v.filter((d) => d.shared_papers > 0).length}), (d) => d.partner_cluster)
  .map(([cluster, m]) => ({cluster, ...m})).filter((d) => d.papers > 0);
display(resize((width) => Plot.plot({
  width, height: 340, marginLeft: 170, x: {grid: true, label: "joint papers (partner-links)"}, y: {label: null},
  marks: [Plot.barX(byCluster, {x: "papers", y: "cluster", sort: {y: "-x"}, fill: instColor.range[INST.indexOf(pick)], tip: true,
    title: (d) => `${d.cluster}: ${d.papers} joint papers with ${d.partners} institutions`}), Plot.ruleX([0])]
})));
```
</div>
<div class="card">

## Topic similarity vs collaboration

```js
const sim = C.filter((d) => d.jaccard_topics != null && d.shared_papers >= 3);
display(resize((width) => Plot.plot({
  width, height: 340, x: {label: "Jaccard similarity of research subfields", grid: true, domain: [0, 1]},
  y: {type: "log", label: "co-authored papers (log)", grid: true},
  marks: [Plot.dot(sim, {x: "jaccard_topics", y: "shared_papers", r: 4, fill: (d) => (d.cross_cluster ? "var(--context)" : instColor.range[INST.indexOf(pick)]),
    stroke: "var(--theme-background)", tip: true, title: (d) => `${d.partner_inst} (${d.partner_cluster})\nJaccard ${d3.format(".2f")(d.jaccard_topics)} · weighted ${d3.format(".2f")(d.weighted_jaccard)}\n${d.shared_papers} joint papers`}),
    Plot.text(sim.toSorted((a, b) => b.shared_papers - a.shared_papers).slice(0, 6), {x: "jaccard_topics", y: "shared_papers", text: "partner_inst", dy: -9, fontSize: 10, fill: "var(--theme-foreground-muted)"})]
})));
```
<p class="muted">Jaccard over the sets of OpenAlex subfields that each make up ≥0.5% of an institution's 2016–26 output (institution-wide, from OpenAlex). Partners with ≥3 joint papers.</p>
</div>
</div>

## Cross-cluster links

```js
const cross = C.filter((d) => d.cross_cluster && d.shared_papers > 0).toSorted((a, b) => b.shared_papers - a.shared_papers);
display(Inputs.table(cross, {columns: ["partner_inst", "partner_cluster", "shared_papers", "cites_in", "cites_out", "total_citations", "jaccard_topics"],
  header: {partner_inst: "Partner", partner_cluster: "Cluster", shared_papers: "Joint papers", cites_in: "Cites in", cites_out: "Cites out",
           total_citations: "Citations total", jaccard_topics: "Topic Jaccard"},
  format: {jaccard_topics: (x) => (x == null ? "—" : d3.format(".2f")(x))}, rows: 15, layout: "auto"}));
```

## All partner institutions

```js
const q = view(Inputs.search(C, {placeholder: "Search institutions…", columns: ["partner_inst", "partner_full_name", "partner_cluster"]}));
```

```js
display(Inputs.table(q, {columns: ["partner_inst", "partner_cluster", "shared_papers", "cites_in", "cites_out", "total_citations", "jaccard_topics", "weighted_jaccard"],
  format: {jaccard_topics: (x) => (x == null ? "—" : d3.format(".2f")(x)), weighted_jaccard: (x) => (x == null ? "—" : d3.format(".2f")(x))},
  sort: "shared_papers", reverse: true, rows: 15, layout: "auto"}));
```
