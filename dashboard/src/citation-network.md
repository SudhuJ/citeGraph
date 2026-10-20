---
title: Knowledge flow
---

# Knowledge flow inside the two institutes

<p class="muted">The citation network: nodes are our papers, and an arrow A → B means paper A cites paper B. Only citations between our own papers are used here. Citations with the rest of India and the world are on <a href="./connectivity">India & the world</a>. Papers with 100 or more authors are left out.</p>

```js
import {graphView, legend} from "./components/graph.js";
import {INST, instColor, shortInst, pct, num, answer} from "./components/defs.js";
const M = FileAttachment("data/network_metrics.json").json();
const G = FileAttachment("data/cit_graph.json").json();
const FC = FileAttachment("data/faccit_graph.json").json();
const GF = FileAttachment("data/fac_graph.json").json();
```

```js
const C = M.citation, S = C.summary, SN = C.summary_excl_self, FS = FC.summary;
const selfN = S.edges - SN.edges;
```

## Do groups build on each other's work?

${answer(html`Rarely. Of ${num(S.edges)} citations between our own papers, ${pct(S.self_share)} are self-citations: the citing and cited papers share an author. Only ${num(SN.edges)} citations go from one group's paper to a paper by different people. Within the institutes, citation mostly records how a lab builds on its own earlier work.`)}

<div class="grid grid-cols-4">
  <div class="card"><h2>Citations between our papers</h2><div class="big">${num(S.edges)}</div><div class="muted">among ${num(S.nodes)} papers</div></div>
  <div class="card"><h2>Self-citations</h2><div class="big">${pct(S.self_share)}</div><div class="muted">${num(selfN)} links share an author</div></div>
  <div class="card"><h2>Between different people</h2><div class="big">${num(SN.edges)}</div><div class="muted">citations with no shared author</div></div>
  <div class="card"><h2>Papers on such a link</h2><div class="big">${num(SN.nodes - SN.isolates)}</div><div class="muted">citing or cited across groups</div></div>
</div>

```js
const onlyCross = view(Inputs.toggle({label: "Show only citations between different people", value: false}));
```

```js
const gv = graphView({
  nodes: G.nodes, edges: G.edges, directed: true, height: 620,
  color: (n) => (n.inst.includes(";") ? "context" : n.inst === "IISER Pune" ? "pune" : "kolkata"),
  size: (n) => 1.5 + 1.6 * Math.sqrt(n.indeg), label: (n) => (n.title.length > 60 ? n.title.slice(0, 57) + "…" : n.title),
  labelThreshold: 12, emphasise: (e) => !e[2], hideEdge: onlyCross ? (e) => e[2] : null,
  tooltip: (n) => `<b>${n.title}</b>${n.venue ?? ""} · ${n.year}<br>${n.inst}<br>cited by ${n.indeg} of our papers (${n.indeg_ns} by different people) · ${n.cites} citations in total`
});
invalidation.then(() => gv.kill());
display(legend([["IISER Pune paper", "var(--pune)"], ["IISER Kolkata paper", "var(--kolkata)"], ["joint Pune–Kolkata paper", "var(--context)"]]));
display(gv);
```
<p class="muted">The largest connected part of the graph (${pct(C.visual_component_share)} of papers). Faint edges are self-citations; dark edges link papers with no shared author. Node size: citations from our other papers.</p>

<details class="how"><summary>How it's computed</summary>
<p>A citation is a self-citation when the two papers share at least one author. That covers our faculty and also their students and postdocs. All OpenAlex profiles of a faculty member count as the same person, since OpenAlex sometimes splits one person into several profiles.</p>
</details>

## Which faculty draw on colleagues' work?

${answer(html`About half. ${FS.faculty_citing_colleagues} of ${FS.faculty} publishing faculty cite at least one colleague they never co-authored with, and ${FS.faculty_cited_by_colleagues} are cited that way. These ${num(FS.citation_links)} links connect ${FS.faculty_pairs} pairs of faculty.`)}

```js
const gf = graphView({
  nodes: FC.nodes, edges: FC.edges, directed: true, height: 620,
  color: (n) => (n.inst === "IISER Pune" ? "pune" : "kolkata"),
  size: (n) => 3 + 1.4 * Math.sqrt(n.cited_by_colleagues), label: (n) => n.label, labelThreshold: 5,
  edgeSize: (e) => 0.5 + Math.log2(1 + e[2]) * 0.6,
  tooltip: (n) => `<b>${n.label}</b>${n.dept} · ${n.inst}<br>cited ${n.cited_by_colleagues}× by colleagues · cites colleagues ${n.cites_colleagues}×`
});
invalidation.then(() => gf.kill());
display(legend([["IISER Pune faculty", "var(--pune)"], ["IISER Kolkata faculty", "var(--kolkata)"]]));
display(gf);
```
<p class="muted">Arrow A → B: A's papers cite B's papers, with no shared author. Node size: citations received from colleagues. Faculty without such links are hidden.</p>

```js
display(Inputs.table(FC.nodes, {
  columns: ["label", "inst", "dept", "cited_by_colleagues", "cites_colleagues", "pagerank"],
  header: {label: "Faculty", inst: "Institute", dept: "Department", cited_by_colleagues: "Cited by colleagues", cites_colleagues: "Cites colleagues", pagerank: "PageRank"},
  format: {inst: shortInst}, sort: "cited_by_colleagues", reverse: true, rows: 10, layout: "auto", select: false
}));
```

<details class="how"><summary>How it's computed</summary>
<p>Faculty A → B gets one unit for every citation from a paper with A to a paper with B where the two papers share no author. PageRank (damping 0.85, weighted) ranks faculty whose work is cited by colleagues who are themselves cited.</p>
</details>

## Does knowledge cross departments and the two institutes?

```js
// faculty co-author pairs that span Pune and Kolkata, for comparison
const crossPairs = GF.edges.filter(([s, t]) => GF.nodes[s].inst !== GF.nodes[t].inst).length;
const flows = FC.dept_flow.map((d) => ({...d, from: `${shortInst(d.from_inst)} · ${d.from_dept}`, to: `${shortInst(d.to_inst)} · ${d.to_dept}`,
  kind: d.from_inst !== d.to_inst ? "between institutes" : d.from_dept !== d.to_dept ? "between departments" : "within department"}));
```

${answer(html`Yes, much more than co-authorship does. ${pct(1 - FS.same_institute_share)} of these colleague citations go between Pune and Kolkata, close to the roughly 50% we would expect if faculty cited colleagues at random. Co-authorship links almost never cross (${crossPairs} faculty pairs). Another ${pct(FS.same_institute_share - FS.same_department_share)} go between departments of the same institute. Faculty read each other's work across the two institutes even when they do not write together.`)}

```js
display(Inputs.table(flows, {
  columns: ["from", "to", "kind", "links"],
  header: {from: "Citing department", to: "Cited department", kind: "Type", links: "Citation links"},
  sort: "links", reverse: true, rows: 12, layout: "auto", select: false
}));
```

## Which papers are most central?

```js
const withSelf = view(Inputs.toggle({label: "Count self-citations", value: false}));
```

${answer(html`With self-citations left out, the citation graph is very sparse, so these rankings rest on only a few citations each. With self-citations included, PageRank mostly rewards long chains of a lab citing its own papers.`)}

```js
display(Inputs.table(withSelf ? C.top_pagerank_with_self : C.top_pagerank, {
  columns: ["title", "inst", "year", "pagerank", "indeg", "cites_total", "doi"],
  header: {title: "Title", inst: "Institute", year: "Year", pagerank: "PageRank", indeg: withSelf ? "Cited by our papers" : "Cited by other groups", cites_total: "Citations (all)", doi: "DOI"},
  format: {pagerank: (x) => x.toExponential(2), year: (x) => x, doi: (x) => (x ? html`<a href="https://doi.org/${x}" target="_blank">${x}</a>` : "—")},
  width: {title: 380}, layout: "auto", sort: "pagerank", reverse: true, select: false
}));
```

<details class="how"><summary>How it's computed</summary>
<p>PageRank with damping 0.85 on the directed citation graph between our papers. A paper ranks high when it is cited by papers that are themselves cited. For overall influence, the total citation counts on <a href="./output">Output & venues</a> are the better measure.</p>
</details>

## How unequal are citations inside the corpus?

```js
const cc = [...C.indegree_ccdf.map((d) => ({...d, graph: "all citations"})), ...C.indegree_ccdf_excl_self.map((d) => ({...d, graph: "different people only"}))];
display(resize((width) => Plot.plot({
  width, height: 280, x: {type: "log", label: "times cited by our other papers (k)", grid: true},
  y: {type: "log", label: "share of cited papers with at least k", grid: true},
  color: {domain: ["all citations", "different people only"], range: ["var(--pune)", "var(--context)"], legend: true},
  marks: [Plot.line(cc, {x: "k", y: "p", stroke: "graph", strokeWidth: 2}), Plot.dot(cc, {x: "k", y: "p", fill: "graph", r: 3, tip: true})]
})));
```

<p class="caveat">The distribution is heavy-tailed. We do not claim a power law: the fitted exponent (α = ${C.powerlaw_indegree?.alpha} above k = ${C.powerlaw_indegree?.xmin}) has no goodness-of-fit test or lognormal comparison behind it.</p>
