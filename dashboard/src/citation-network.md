---
title: Citation network
---

# Citation network

<p class="muted">Directed graph: nodes are corpus papers, an edge A → B means paper A cites paper B. Analysis is <b>within</b> the two institutes (both endpoints in the corpus). Cross-institute Indian edges are in <code>citation_network.csv</code> and in the flow charts below.</p>

```js
import {graphView, legend} from "./components/graph.js";
```

```js
const M = FileAttachment("data/network_metrics.json").json();
const G = FileAttachment("data/cit_graph.json").json();
const INST = ["IISER Pune", "IISER Kolkata"];
const instColor = {domain: INST, range: ["var(--pune)", "var(--kolkata)"], legend: true};
```

```js
const C = M.citation, S = C.summary;
```

<div class="grid grid-cols-4">
  <div class="card"><h2>Papers (nodes)</h2><div class="big">${S.nodes.toLocaleString()}</div><div class="muted">${S.isolates.toLocaleString()} not linked to another corpus paper</div></div>
  <div class="card"><h2>Internal citations</h2><div class="big">${S.edges.toLocaleString()}</div><div class="muted">mean degree ${S.mean_degree}, density ${S.density}</div></div>
  <div class="card"><h2>Largest component</h2><div class="big">${d3.format(".0%")(S.giant_share)}</div><div class="muted">${S.components.toLocaleString()} weak components · avg path ${S.avg_path_gcc}</div></div>
  <div class="card"><h2>Clustering</h2><div class="big">${S.transitivity}</div><div class="muted">transitivity · degree assortativity ${S.assortativity_degree}</div></div>
</div>

```js
const colorBy = view(Inputs.radio(["Institute", "Publication year"], {value: "Institute", label: "Colour by"}));
const sizeBy = view(Inputs.radio(["PageRank", "In-degree", "Total citations"], {value: "PageRank", label: "Size by"}));
```

```js
// sequential year ramp: light→dark on a light surface, dark→light on a dark one (tokens in style.css)
const yearColor = (y, t) => d3.interpolateRgb(t.rampLo, t.rampHi)((y - 2016) / 10);
const sizeFn = {
  "PageRank": (n) => 1.5 + 220 * Math.sqrt(n.pr),
  "In-degree": (n) => 1.5 + 2.2 * Math.sqrt(n.indeg),
  "Total citations": (n) => 1.5 + 0.35 * Math.sqrt(n.cites)
}[sizeBy];
const view_ = graphView({
  nodes: G.nodes, edges: G.edges, directed: true, height: 640,
  color: colorBy === "Institute"
    ? (n) => (n.inst.includes(";") ? "context" : n.inst === "IISER Pune" ? "pune" : "kolkata")
    : (n, t) => yearColor(n.year, t),
  size: sizeFn, label: (n) => (n.title.length > 60 ? n.title.slice(0, 57) + "…" : n.title),
  labelThreshold: 12,
  tooltip: (n) => `<b>${n.title}</b>${n.venue ?? ""} · ${n.year}<br>${n.inst}<br>in-degree (corpus) ${n.indeg} · out ${n.outdeg}<br>PageRank ${n.pr.toExponential(2)} · ${n.cites} citations total`
});
invalidation.then(() => view_.kill());
display(colorBy === "Institute"
  ? legend([["IISER Pune", "var(--pune)"], ["IISER Kolkata", "var(--kolkata)"], ["joint Pune–Kolkata paper", "var(--context)"]])
  : legend([["2016", "var(--ramp-lo)"], ["2021", "color-mix(in oklab, var(--ramp-lo), var(--ramp-hi))"], ["2026", "var(--ramp-hi)"]]));
display(view_);
```
<p class="muted">Shows the largest weakly-connected component (${d3.format(".0%")(C.visual_component_share)} of papers). Layout: igraph DrL, precomputed.</p>

## Most influential papers (PageRank, top 10)

```js
const prHyper = view(Inputs.toggle({label: "Include ≥100-author collaboration papers", value: false}));
```

<p class="muted">CMS collaboration papers cite each other densely and soak up PageRank (${C.top_pagerank.filter((p) => p.hyperauthored).length} of the top 10 when included), so by default PageRank is recomputed on the graph without them.</p>

```js
display(Inputs.table(prHyper ? C.top_pagerank : C.top_pagerank_excl_hyper, {
  columns: ["title", "inst", "year", "pagerank", "indeg", "cites_total", "doi"],
  header: {title: "Title", inst: "Institute", year: "Year", pagerank: "PageRank", indeg: "In-degree (corpus)", cites_total: "Citations (all)", doi: "DOI"},
  format: {pagerank: (x) => x.toExponential(2), year: (x) => x, doi: (x) => (x ? html`<a href="https://doi.org/${x}" target="_blank">${x}</a>` : "—")},
  width: {title: 380}, layout: "auto", sort: "pagerank", reverse: true
}));
```

<div class="grid grid-cols-2">
<div class="card">

## In-degree distribution

```js
display(resize((width) => Plot.plot({
  width, height: 300, x: {type: "log", label: "in-degree k (citations from corpus papers)", grid: true},
  y: {type: "log", label: "P(K ≥ k)", grid: true},
  marks: [
    Plot.line(C.indegree_ccdf, {x: "k", y: "p", stroke: "var(--pune)", strokeWidth: 2}),
    Plot.dot(C.indegree_ccdf, {x: "k", y: "p", fill: "var(--pune)", r: 3, tip: true})
  ]
})));
```
<p class="muted">Complementary CDF. Power-law tail fit (discrete MLE, igraph): α = ${C.powerlaw_indegree?.alpha}, k<sub>min</sub> = ${C.powerlaw_indegree?.xmin}, KS D = ${C.powerlaw_indegree?.ks_D} (n<sub>tail</sub> = ${C.powerlaw_indegree?.n_tail}).</p>
</div>
<div class="card">

## Citation flow with other Indian institutes

```js
display(resize((width) => Plot.plot({
  width, height: 300, x: {tickFormat: "d", label: null}, y: {grid: true, label: "citations"}, fy: {label: null},
  color: instColor,
  marks: [
    Plot.ruleY([0]),
    Plot.line(C.flow_year, {x: "year", y: "citations", z: "direction", fy: "institution", stroke: "institution",
      strokeWidth: 2, strokeDasharray: (d) => (d.direction === "out" ? "5,3" : null)}),
    Plot.dot(C.flow_year, {x: "year", y: "citations", fy: "institution", fill: "institution", r: 3, tip: true,
      title: (d) => `${d.institution} · ${d.year}\n${d.direction === "in" ? "received from" : "given to"} other Indian institutes: ${d.citations}`}),
    Plot.text(C.flow_year.filter((d) => d.year === 2023), {x: "year", y: "citations", fy: "institution",
      text: (d) => (d.direction === "in" ? "in-flow" : "out-flow"), dy: -10, fill: "var(--theme-foreground-muted)"})
  ]
})));
```
<p class="muted">Solid line: in-flow (Indian papers citing us, by citing year). Dashed: out-flow (our papers citing Indian work).</p>
</div>
</div>

<div class="grid grid-cols-4">
  ${INST.map((i) => html`<div class="card"><h2>${i} · impact ratio</h2><div class="big">${C.flow_total[i].impact_ratio}</div>
  <div class="muted">in-cites ${C.flow_total[i].in.toLocaleString()} ÷ out-cites ${C.flow_total[i].out.toLocaleString()}</div></div>`)}
</div>

## Top 10 Indian institutes citing our work

```js
display(resize((width) => Plot.plot({
  width, height: 360, marginLeft: 200, x: {grid: true, label: "citations received"}, y: {label: null}, fx: {label: null},
  color: instColor,
  marks: [
    Plot.barX(C.top_citing_institutes, {x: "citations", y: "partner", fx: "institution", fill: "institution",
      sort: {y: "-x"}, tip: true, title: (d) => `${d.partner} (${d.cluster}) → ${d.institution}: ${d.citations}`}),
    Plot.ruleX([0])
  ]
})));
```

## Indian papers citing the most of our work

```js
display(Inputs.table(C.top_citing_papers, {
  columns: ["institution", "title", "year", "corpus_papers_cited", "insts"],
  header: {institution: "Cites work of", title: "Citing paper", year: "Year", corpus_papers_cited: "Our papers cited", insts: "Citing institutes"},
  format: {year: (x) => x}, width: {title: 360, insts: 260}, layout: "auto"
}));
```
