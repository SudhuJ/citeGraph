---
title: Knowledge flow
---

# Knowledge flow inside the two institutes

<p class="muted">The citation network: one node per paper by our faculty, and an arrow A → B when paper A cites paper B. Only citations between two of our own papers are used here; citations with the rest of India and the world are on <a href="./connectivity">India & the world</a>. Papers with 100 or more authors are left out.</p>

```js
import {graphView, legend} from "./components/graph.js";
import {INST, instColor, shortInst, pct, num, answer, measure, citationTerms} from "./components/defs.js";
const M = FileAttachment("data/network_metrics.json").json();
const G = FileAttachment("data/cit_graph.json").json();
const FC = FileAttachment("data/faccit_graph.json").json();
const GF = FileAttachment("data/fac_graph.json").json();
const origin = FileAttachment("data/origin.csv").csv({typed: true});
```

```js
const C = M.citation, S = C.summary, SN = C.summary_excl_self, FS = FC.summary;
const selfN = S.edges - SN.edges;
const IN = origin.filter((d) => d.direction === "in");
const recv = d3.sum(IN, (d) => d.n), fromOurs = d3.sum(IN.filter((d) => d.from_ours), (d) => d.n);
```

${citationTerms(origin)}

## Do our faculty build on each other's work?

${measure(html`Every citation where both papers are ours, split by whether the two papers share an author.`)}

${answer(html`Rarely. Citations from our own papers are a small part of what our papers receive: about ${pct(fromOurs / recv)} of all citations. Within that part, ${pct(S.self_share)} of the ${num(S.edges)} citations are self-citations, where the same person is on both papers. Only ${num(SN.edges)} go from one of our papers to a paper by different people. So when our faculty cite IISER work, it is almost always their own earlier work.`)}

<div class="grid grid-cols-4">
  <div class="card"><h2>Citations between our papers</h2><div class="big">${num(S.edges)}</div><div class="muted">among ${num(S.nodes)} papers · ${pct(fromOurs / recv)} of all citations we receive</div></div>
  <div class="card"><h2>…of which self-citations</h2><div class="big">${pct(S.self_share)}</div><div class="muted">${num(selfN)} links share an author</div></div>
  <div class="card"><h2>Between different people</h2><div class="big">${num(SN.edges)}</div><div class="muted">citations with no shared author</div></div>
  <div class="card"><h2>Papers on such a link</h2><div class="big">${num(SN.nodes - SN.isolates)}</div><div class="muted">citing or cited across groups</div></div>
</div>

```js
const onlyCross = view(Inputs.toggle({label: "Show only citations between different people", value: false}));
```

```js
// with the toggle on, keep only the non-self edges and the papers on them, sized by those citations
const Gv = (() => {
  if (!onlyCross) return G;
  const edges = G.edges.filter((e) => !e[2]);
  const keep = [...new Set(edges.flatMap(([s, t]) => [s, t]))].sort((a, b) => a - b);
  const re = new Map(keep.map((i, j) => [i, j]));
  return {nodes: keep.map((i) => G.nodes[i]), edges: edges.map(([s, t, x]) => [re.get(s), re.get(t), x])};
})();
const gv = graphView({
  nodes: Gv.nodes, edges: Gv.edges, directed: true, height: 620,
  color: (n) => (n.inst.includes(";") ? "context" : n.inst === "IISER Pune" ? "pune" : "kolkata"),
  size: (n) => (onlyCross ? 2.5 + 2 * Math.sqrt(n.indeg_ns) : 1.5 + 1.6 * Math.sqrt(n.indeg)),
  label: (n) => (n.title.length > 60 ? n.title.slice(0, 57) + "…" : n.title),
  labelThreshold: onlyCross ? 6 : 12, emphasise: (e) => !e[2],
  tooltip: (n) => `<b>${n.title}</b>${n.venue ?? ""} · ${n.year}<br>${n.inst}<br>cited by ${n.indeg} of our papers (${n.indeg_ns} by different people) · ${n.cites} citations in total`
});
invalidation.then(() => gv.kill());
display(legend([["IISER Pune paper", "var(--pune)"], ["IISER Kolkata paper", "var(--kolkata)"], ["joint Pune–Kolkata paper", "var(--context)"]]));
display(gv);
```
<p class="muted">${onlyCross
  ? html`Only the ${num(Gv.edges.length)} citations between different people in this part of the graph, and the ${num(Gv.nodes.length)} papers they touch. Node size: citations from other people's papers. Positions are kept from the full view, so the scattered pairs sit where their labs' clusters were.`
  : html`The largest connected part of the graph (${pct(C.visual_component_share)} of papers). Each tight cluster is mostly one lab's papers citing each other. Faint edges are self-citations; dark edges link papers with no shared author. Node size: citations from our other papers.`}</p>

<details class="how"><summary>How self-citations are identified</summary>
<p>A citation is a self-citation when the two papers share at least one author. That covers our faculty and also their students and postdocs. All OpenAlex profiles of a faculty member count as the same person, since OpenAlex sometimes splits one person into several profiles.</p>
</details>

## Which faculty draw on colleagues' work?

```js
// faculty pairs linked by citation who have also co-authored at some point
const coPairs = new Set(GF.edges.map(([s, t]) => [GF.nodes[s].id, GF.nodes[t].id].sort().join("|")));
const citPairs = new Set(FC.edges.map(([s, t]) => [FC.nodes[s].id, FC.nodes[t].id].sort().join("|")));
const citNotCo = [...citPairs].filter((p) => !coPairs.has(p)).length;
```

${measure(html`We merge papers into their faculty authors. Faculty A → B gets one link for every citation from a paper with A on it to a paper with B on it, where the two papers share no author. Then we count who cites and who is cited this way.`)}

${answer(html`About half. ${FS.faculty_citing_colleagues} of ${FS.faculty} publishing faculty cite a colleague's paper that they are not an author of, and ${FS.faculty_cited_by_colleagues} are cited that way. These ${num(FS.citation_links)} citations connect ${citPairs.size} pairs of faculty, and ${pct(citNotCo / citPairs.size)} of those pairs have never written a paper together. So citation links mostly join faculty who do not write together.`)}

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
<p class="muted">Arrow A → B: A's papers cite B's papers, with no shared author. Node size: citations received from colleagues. Faculty without such links are hidden. Unlike the co-authorship graph, the two colours mix.</p>

```js
display(Inputs.table(FC.nodes, {
  columns: ["label", "inst", "dept", "cited_by_colleagues", "cites_colleagues"],
  header: {label: "Faculty", inst: "Institute", dept: "Department", cited_by_colleagues: "Cited by colleagues", cites_colleagues: "Cites colleagues"},
  format: {inst: shortInst}, sort: "cited_by_colleagues", reverse: true, rows: 10, layout: "auto", select: false
}));
```

## Does knowledge cross departments and the two institutes?

```js
const kinds = ["same department", "same institute, other department", "Pune–Kolkata"];
const coKind = ([s, t]) => {
  const a = GF.nodes[s], b = GF.nodes[t];
  return a.inst !== b.inst ? kinds[2] : a.dept !== b.dept ? kinds[1] : kinds[0];
};
const cmp = [
  ...kinds.map((k) => ({graph: "Citing a colleague", kind: k,
    share: [FS.same_department_share, FS.same_institute_share - FS.same_department_share, 1 - FS.same_institute_share][kinds.indexOf(k)]})),
  ...kinds.map((k) => ({graph: "Co-authoring", kind: k, share: GF.edges.filter((e) => coKind(e) === k).length / GF.edges.length}))
];
const share = (g, k) => cmp.find((d) => d.graph === g && d.kind === k).share;
const flows = FC.dept_flow.map((d) => ({...d, from: `${shortInst(d.from_inst)} · ${d.from_dept}`, to: `${shortInst(d.to_inst)} · ${d.to_dept}`,
  kind: d.from_inst !== d.to_inst ? "between institutes" : d.from_dept !== d.to_dept ? "between departments" : "within department"}));
```

${measure(html`For the faculty-to-faculty citations above, and for faculty co-author links, the share that stays in one department, crosses departments within an institute, or crosses between Pune and Kolkata.`)}

${answer(html`Citation crosses institutes far more than co-authorship does. ${pct(share("Citing a colleague", "Pune–Kolkata"))} of colleague citations go between Pune and Kolkata, against ${pct(share("Co-authoring", "Pune–Kolkata"))} of co-author links. That is close to the roughly 50% we would expect if faculty cited colleagues at random, so for reading each other's work, the institute boundary hardly matters. For writing together, it almost always does.`)}

```js
display(resize((width) => Plot.plot({
  width, height: 130, marginLeft: 130, x: {percent: true, label: "share of links (%)"}, y: {label: null},
  color: {domain: kinds, range: ["var(--q1)", "var(--q2)", "var(--q3)"], legend: true},
  marks: [Plot.barX(cmp, Plot.stackX({x: "share", y: "graph", fill: "kind", order: kinds, inset: 1, tip: true,
    title: (d) => `${d.graph}\n${d.kind}: ${d3.format(".0%")(d.share)}`}))]
})));
```

```js
display(Inputs.table(flows, {
  columns: ["from", "to", "kind", "links"],
  header: {from: "Citing department", to: "Cited department", kind: "Type", links: "Citation links"},
  sort: "links", reverse: true, rows: 10, layout: "auto", select: false
}));
```

## Which papers do other groups here build on most?

```js
const R = C.pagerank_vs_indegree, T = C.top_indegree;
const h3 = C.indegree_hist_excl_self.filter((d) => ["3–5", "6–10", "11+"].includes(d.bin));
```

${measure(html`<i>In-degree</i>: for each paper, how many of our other papers by different people cite it. Self-citations are left out, so a lab citing its own work does not count.`)}

${answer(html`No paper stands out by much. The most-used one, "${T[0].title}" (${shortInst(T[0].inst)}, ${T[0].year}), is cited by ${T[0].indeg} papers from other groups, and only ${num(d3.sum(h3, (d) => d.papers))} papers are cited by three or more. PageRank, which also weighs how well cited the citing papers are, agrees only partly: ${R.top10_overlap} of its top 10 are in this top 10. With so few links, one extra citation reorders the list, so these rankings are weak evidence.`)}

```js
display(Inputs.table(T, {
  columns: ["title", "inst", "year", "indeg", "pr_rank", "cites_total", "doi"],
  header: {title: "Title", inst: "Institute", year: "Year", indeg: "Cited by other groups' papers", pr_rank: "PageRank rank", cites_total: "Citations (all)", doi: "DOI"},
  format: {inst: shortInst, year: (x) => x, doi: (x) => (x ? html`<a href="https://doi.org/${x}" target="_blank">${x}</a>` : "—")},
  width: {title: 380}, layout: "auto", sort: "indeg", reverse: true, select: false
}));
```

<details class="how"><summary>What PageRank is, and why not the clustering coefficient</summary>
<ul>
<li><b>PageRank</b> imagines a reader who starts at a random paper and keeps following a random reference, jumping to a new random paper 15% of the time. A paper's PageRank is the share of time the reader spends on it. A citation from a well-cited paper therefore counts for more than one from an uncited paper. The assignment asks for it, so we report its rank beside the plain count.</li>
<li>Across the ${R.cited_papers} papers cited at least once by another group, the two rankings have a rank correlation of ${R.spearman} (1 would be the same order).</li>
<li>The <b>clustering coefficient</b> answers a different question: whether a paper's neighbours also cite each other, that is, how tightly knit its neighbourhood is. It does not measure how much a paper is used, so it cannot rank importance.</li>
<li>For overall influence, the total citation counts on <a href="./output">Output & venues</a> are the better measure; this section is only about use inside the two institutes.</li>
</ul>
</details>

## How many of our papers are cited by our other papers?

```js
const binOrder = C.indegree_hist.map((d) => d.bin);
const HH = [...C.indegree_hist.map((d) => ({...d, kind: "any of our papers"})),
            ...C.indegree_hist_excl_self.map((d) => ({...d, kind: "papers by different people"}))];
const zero = (h) => h.find((d) => d.bin === "0").papers / d3.sum(h, (d) => d.papers);
```

${measure(html`For each paper, the number of our other papers that cite it, counted once with self-citations and once without.`)}

${answer(html`Counting self-citations, ${pct(1 - zero(C.indegree_hist))} of our papers are cited by at least one of our other papers, mostly by the same lab's later work. Leaving self-citations out, ${pct(zero(C.indegree_hist_excl_self))} are never cited by anyone else at the two institutes.`)}

```js
display(resize((width) => Plot.plot({
  width, height: 260, x: {label: "times cited by our other papers", domain: binOrder}, y: {grid: true, label: "papers"},
  fx: {label: null}, color: {domain: ["any of our papers", "papers by different people"], range: ["var(--pune)", "var(--context)"], legend: true},
  marks: [Plot.barY(HH, {fx: "kind", x: "bin", y: "papers", fill: "kind", inset: 2, tip: true}), Plot.ruleY([0])]
})));
```
