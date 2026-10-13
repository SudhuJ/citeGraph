---
title: Authorship network
---

# Authorship network

<p class="muted">Undirected co-authorship graphs. The instruction note defines nodes as "faculty members" (§6b) while the slides say "authors", so we build <b>both</b> and compare them. <b>G_fac</b>: our publishing faculty only, linked when two of them co-author. <b>G_ind</b>: faculty plus their Indian co-authors at other institutions. Edge weight = Newman's collaboration strength Σ 1/(n−1) over shared papers. Papers with ≥100 authors are left out of both graphs (see sensitivity below).</p>

```js
import {graphView, legend} from "./components/graph.js";
```

```js
const M = FileAttachment("data/network_metrics.json").json();
const GF = FileAttachment("data/fac_graph.json").json();
const GI = FileAttachment("data/ind_graph.json").json();
const INST = ["IISER Pune", "IISER Kolkata"];
const instColor = {domain: INST, range: ["var(--pune)", "var(--kolkata)"], legend: true};
```

```js
const which = view(Inputs.radio(["G_fac — faculty only", "G_ind — faculty + Indian co-authors"], {value: "G_fac — faculty only", label: "Graph"}));
```

```js
const key = which.startsWith("G_fac") ? "G_fac" : "G_ind";
const G = key === "G_fac" ? GF : GI;
const S = M.coauthorship[key].summary;
// communities ranked by size (faculty members) for the highlight selector
const commSizes = d3.rollups(G.nodes.filter((n) => n.faculty), (v) => v.length, (n) => n.community)
  .filter(([, n]) => n >= 3).sort((a, b) => b[1] - a[1]);
```

<div class="grid grid-cols-4">
  <div class="card"><h2>Nodes · edges</h2><div class="big">${S.nodes.toLocaleString()} · ${S.edges.toLocaleString()}</div><div class="muted">${S.isolates} isolated · mean degree ${S.mean_degree}</div></div>
  <div class="card"><h2>Giant component</h2><div class="big">${d3.format(".0%")(S.giant_share)}</div><div class="muted">${S.components} components · avg path ${S.avg_path_gcc} · diameter ${S.diameter_gcc}</div></div>
  <div class="card"><h2>Leiden communities</h2><div class="big">${S.communities_leiden}</div><div class="muted">modularity Q = ${S.modularity_leiden} (Louvain ${S.modularity_louvain}, NMI ${S.nmi_leiden_louvain})</div></div>
  <div class="card"><h2>Clustering</h2><div class="big">${S.transitivity}</div><div class="muted">transitivity · avg local ${S.avg_clustering} · assortativity ${S.assortativity_degree}</div></div>
</div>

```js
const mode = view(Inputs.radio(["Institute", "Highlight a community"], {value: "Institute", label: "Colour"}));
```

```js
const comm = mode === "Institute" ? null : view(Inputs.select(commSizes.map(([c]) => c), {
  label: "Community", format: (c) => {
    const mem = G.nodes.filter((n) => n.faculty && n.community === c);
    const top = d3.rollups(mem, (v) => v.length, (n) => n.dept).sort((a, b) => b[1] - a[1])[0];
    return `#${c} · ${mem.length} faculty · mostly ${top[0]}`;
  }
}));
```

```js
const facColor = (n) => (n.inst === "IISER Pune" ? "pune" : "kolkata");
const gv = graphView({
  nodes: G.nodes, edges: G.edges, height: 860,
  color: (n) => (n.faculty ? facColor(n) : "context"),
  size: key === "G_fac" ? (n) => 3 + 1.6 * Math.sqrt(n.degree) : (n) => (n.faculty ? 3.5 + 0.55 * Math.sqrt(n.degree) : 2.8 + 0.35 * Math.sqrt(n.degree)),
  label: (n) => (n.faculty ? n.label : ""),
  labelThreshold: key === "G_fac" ? 4 : 7,
  edgeSize: (e) => 0.5 + Math.log2(1 + e[3]) * 0.45,
  focus: comm == null ? null : (n) => n.community === comm,
  tooltip: (n, deg) => `<b>${n.label}</b>${n.faculty ? `${n.dept} · ${n.inst}` : `co-author · ${n.inst}`}<br>degree ${deg} · betweenness ${n.betweenness.toExponential(2)}<br>Leiden community #${n.community}`
});
invalidation.then(() => gv.kill());
display(legend([["IISER Pune faculty", "var(--pune)"], ["IISER Kolkata faculty", "var(--kolkata)"],
  ...(key === "G_ind" ? [["Indian co-author (other institute)", "var(--context)"]] : [])]));
display(gv);
```

## Faculty centrality

<p class="muted">Degree centrality = most collaborative; betweenness (shortest paths with distance 1/strength) = brokers between groups. Both shown for the two graphs: a faculty member can be peripheral among IISER colleagues yet central in the wider Indian network.</p>

```js
const fc = M.faculty_comparison;
const qf = view(Inputs.search(fc, {placeholder: "Search faculty…", columns: ["name", "dept", "inst"]}));
```

```js
display(Inputs.table(qf, {
  columns: ["name", "inst", "dept", "deg_fac", "btw_fac", "comm_fac", "deg_ind", "btw_ind", "partner_insts_ind"],
  header: {name: "Faculty", inst: "Institute", dept: "Department", deg_fac: "Degree G_fac", btw_fac: "Betweenness G_fac",
           comm_fac: "Community G_fac", deg_ind: "Degree G_ind", btw_ind: "Betweenness G_ind", partner_insts_ind: "Partner institutes"},
  format: {btw_fac: d3.format(".4f"), btw_ind: d3.format(".4f")}, sort: "btw_ind", reverse: true, rows: 14, layout: "auto"
}));
```

## G_fac vs G_ind

```js
const keys = [["nodes", "Nodes"], ["edges", "Edges"], ["density", "Density"], ["components", "Components"], ["giant_share", "Giant component share"],
  ["isolates", "Isolated nodes"], ["mean_degree", "Mean degree"], ["transitivity", "Transitivity"], ["avg_clustering", "Avg local clustering"],
  ["assortativity_degree", "Degree assortativity"], ["avg_path_gcc", "Avg path length (giant)"], ["diameter_gcc", "Diameter (giant)"],
  ["modularity_leiden", "Modularity (Leiden)"], ["communities_leiden", "Communities (Leiden)"],
  ["nmi_community_department", "NMI communities ↔ departments"], ["nmi_community_institute", "NMI communities ↔ institute"]];
const cmp = keys.map(([k, label]) => ({metric: label, G_fac: M.coauthorship.G_fac.summary[k], G_ind: M.coauthorship.G_ind.summary[k]}));
```

<div class="grid grid-cols-2">
<div class="card">

```js
display(Inputs.table(cmp, {rows: 16, sort: null, layout: "auto", select: false}));
```
</div>
<div class="card">

### Do the two graphs rank faculty the same way?

Spearman ρ between faculty rankings in G_fac and G_ind: **degree ${M.spearman_fac_vs_ind.degree}**, **betweenness ${M.spearman_fac_vs_ind.betweenness}**.

```js
display(resize((width) => Plot.plot({
  width, height: 280, x: {type: "symlog", label: "degree in G_fac", grid: true}, y: {type: "symlog", label: "degree in G_ind", grid: true},
  color: instColor,
  marks: [Plot.dot(fc, {x: "deg_fac", y: "deg_ind", fill: "inst", r: 4, stroke: "var(--theme-background)", tip: true,
    title: (d) => `${d.name} (${d.dept})\nG_fac degree ${d.deg_fac} · G_ind degree ${d.deg_ind}`})]
})));
```
</div>
</div>

<div class="grid grid-cols-2">
<div class="card">

## Degree distribution

```js
const cc = ["G_fac", "G_ind"].flatMap((g) => M.coauthorship[g].degree_ccdf.map((d) => ({...d, graph: g})));
display(resize((width) => Plot.plot({
  width, height: 280, x: {type: "log", label: "degree k", grid: true}, y: {type: "log", label: "P(K ≥ k)", grid: true},
  color: {domain: ["G_fac", "G_ind"], range: ["var(--pune)", "var(--context)"], legend: true},
  marks: [Plot.line(cc, {x: "k", y: "p", stroke: "graph", strokeWidth: 2}), Plot.dot(cc, {x: "k", y: "p", fill: "graph", r: 2.5, tip: true})]
})));
```
<p class="muted">Power-law tail (discrete MLE): G_fac α = ${M.coauthorship.G_fac.summary.powerlaw_degree?.alpha} (k<sub>min</sub> ${M.coauthorship.G_fac.summary.powerlaw_degree?.xmin}, n<sub>tail</sub> ${M.coauthorship.G_fac.summary.powerlaw_degree?.n_tail}); G_ind α = ${M.coauthorship.G_ind.summary.powerlaw_degree?.alpha} (k<sub>min</sub> ${M.coauthorship.G_ind.summary.powerlaw_degree?.xmin}, n<sub>tail</sub> ${M.coauthorship.G_ind.summary.powerlaw_degree?.n_tail}). G_fac's tail has too few points for a credible fit.</p>
</div>
<div class="card">

## Growth 2016 → 2026

```js
display(resize((width) => Plot.plot({
  width, height: 280, x: {tickFormat: "d", label: null}, y: {grid: true, label: "giant-component share", percent: true, domain: [0, 100]},
  color: {domain: ["G_fac", "G_ind"], range: ["var(--pune)", "var(--context)"], legend: true},
  marks: [Plot.line(M.snapshots, {x: "year", y: "giant_share", stroke: "graph", strokeWidth: 2}),
          Plot.dot(M.snapshots, {x: "year", y: "giant_share", fill: "graph", r: 3, tip: true,
            title: (d) => `${d.graph} ≤ ${d.year}\n${d.nodes} nodes · ${d.edges} edges\ngiant ${d3.format(".0%")(d.giant_share)} · mean degree ${d.mean_degree}`})]
})));
```
<p class="muted">Cumulative snapshots: all co-authorships up to each year. Nodes without edges are not counted.</p>
</div>
</div>

## Hyperauthorship sensitivity

```js
const H = M.hyperauthorship;
```

<div class="card">

${H.hyper_papers} papers have ≥100 authors (OpenAlex truncates such author lists at 100). Between them they connect only **${H.hyper_faculty_pairs} pairs** of our faculty, but with hundreds of shared papers each. Counting edges by plain paper counts (no 1/(n−1) weighting), they would dominate collaboration strength:

```js
display(Inputs.table(H.top_strength_with, {header: {name: "Faculty", papers: "co-authored papers with other faculty, hyper papers included"}, select: false}));
```

<p class="muted">Spearman ρ of faculty collaboration strength with vs without these papers: ${H.rho_strength_papers}. The structure barely moves (mean degree ${H.without.mean_degree} → ${H.with.mean_degree}), but strength and "most collaborative" rankings would be distorted. Hence they are excluded from the graphs and kept in the CSVs, flagged <code>hyperauthored</code>.</p>
</div>

## Hub authors bridging multiple institutes (G_ind)

```js
display(Inputs.table(M.hubs, {columns: ["name", "inst", "faculty", "institutes_bridged", "degree", "betweenness"],
  header: {name: "Author", inst: "Institute", faculty: "Our faculty?", institutes_bridged: "Institutes in neighbourhood", degree: "Degree", betweenness: "Betweenness"},
  format: {betweenness: d3.format(".4f"), faculty: (x) => (x ? "yes" : "—")}, rows: 12, layout: "auto"}));
```
