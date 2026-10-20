---
title: Collaboration
---

# Collaboration

<p class="muted">Two co-authorship graphs. <b>G_fac</b> holds only our publishing faculty, linked when two of them share a paper. <b>G_ind</b> adds their co-authors at other Indian institutions. Papers with 100 or more authors are left out of both.</p>

```js
import {graphView, legend} from "./components/graph.js";
import {INST, instColor, shortInst, pct, num, answer} from "./components/defs.js";
const M = FileAttachment("data/network_metrics.json").json();
const GF = FileAttachment("data/fac_graph.json").json();
const GI = FileAttachment("data/ind_graph.json").json();
```

```js
const SF = M.coauthorship.G_fac.summary, SI = M.coauthorship.G_ind.summary;
const crossPairs = GF.edges.filter(([s, t]) => GF.nodes[s].inst !== GF.nodes[t].inst).length;
const fc = M.faculty_comparison;
```

## Do faculty co-author with each other?

${answer(html`Not much. ${SF.isolates} of ${SF.nodes} publishing faculty (${pct(SF.isolates / SF.nodes)}) have no paper with another faculty member of either institute. The rest form ${SF.communities_leiden} groups, ${SF.communities_leiden_3plus} of them with three or more people. The groups match departments far better than institutes (NMI ${SF.nmi_community_department} vs ${SF.nmi_community_institute}). Only ${crossPairs} pairs of faculty link Pune and Kolkata.`)}

```js
const facColor = (n) => (n.inst === "IISER Pune" ? "pune" : "kolkata");
const gvF = graphView({
  nodes: GF.nodes, edges: GF.edges, height: 640,
  color: facColor, size: (n) => 3 + 1.6 * Math.sqrt(n.degree), label: (n) => n.label, labelThreshold: 4,
  edgeSize: (e) => 0.5 + Math.log2(1 + e[3]) * 0.45,
  tooltip: (n, deg) => `<b>${n.label}</b>${n.dept} · ${n.inst}<br>${deg} faculty co-authors · group #${n.community}`
});
invalidation.then(() => gvF.kill());
display(legend([["IISER Pune faculty", "var(--pune)"], ["IISER Kolkata faculty", "var(--kolkata)"]]));
display(gvF);
```
<p class="muted">Node size: number of faculty co-authors. Edge width: number of shared papers. Hover a node to see its neighbours.</p>

<details class="how"><summary>How it's computed</summary>
<ul>
<li>Edge weight is Newman's collaboration strength: each shared paper adds 1/(n−1), where n is its number of authors. A two-author paper ties its authors more strongly than a 30-author one.</li>
<li>Groups are found with the Leiden algorithm, maximising modularity (cross-checked with Louvain, NMI ${SF.nmi_leiden_louvain}). Faculty with no co-author are not counted as groups.</li>
<li>NMI (normalised mutual information) measures how well the groups match a known split: 1 means identical, 0 means unrelated.</li>
</ul>
</details>

## Who connects the groups?

```js
const brokers = fc.toSorted((a, b) => b.btw_ind - a.btw_ind);
```

${answer(html`A few faculty carry most of the shortest paths in the wider Indian network. The top broker is ${brokers[0].name} (${brokers[0].dept}, ${shortInst(brokers[0].inst)}), whose co-authors span ${brokers[0].partner_insts_ind} other institutes. Being central among colleagues and being central in India are related but not the same (Spearman ρ between the two betweenness rankings: ${M.spearman_fac_vs_ind.betweenness}).`)}

```js
const qf = view(Inputs.search(fc, {placeholder: "Search faculty…", columns: ["name", "dept", "inst"]}));
```

```js
display(Inputs.table(qf, {
  columns: ["name", "inst", "dept", "deg_fac", "btw_fac", "deg_ind", "btw_ind", "partner_insts_ind"],
  header: {name: "Faculty", inst: "Institute", dept: "Department", deg_fac: "Faculty co-authors", btw_fac: "Betweenness (G_fac)",
           deg_ind: "Indian co-authors", btw_ind: "Betweenness (G_ind)", partner_insts_ind: "Partner institutes"},
  format: {inst: shortInst, btw_fac: d3.format(".4f"), btw_ind: d3.format(".4f")}, sort: "btw_ind", reverse: true, rows: 12, layout: "auto"
}));
```

<details class="how"><summary>How it's computed</summary>
<p>Betweenness is the share of shortest paths between all pairs of people that pass through a person. Path length uses distance 1/strength, so strong collaborations count as short links. Values are normalised by the number of pairs.</p>
</details>

## What changes when we add Indian co-authors?

${answer(html`The network joins up. G_ind has ${num(SI.nodes)} people, and ${pct(SI.giant_share)} of them sit in one connected component (vs ${pct(SF.giant_share)} in G_fac). It splits into ${SI.communities_leiden} tightly knit groups (modularity ${SI.modularity_leiden}), each built around one or a few faculty labs.`)}

```js
const gvI = graphView({
  nodes: GI.nodes, edges: GI.edges, height: 760,
  color: (n) => (n.faculty ? facColor(n) : "context"),
  size: (n) => (n.faculty ? 3.5 + 0.55 * Math.sqrt(n.degree) : 2.8 + 0.35 * Math.sqrt(n.degree)),
  label: (n) => (n.faculty ? n.label : ""), labelThreshold: 7,
  edgeSize: (e) => 0.5 + Math.log2(1 + e[3]) * 0.45,
  tooltip: (n, deg) => `<b>${n.label}</b>${n.faculty ? `${n.dept} · ${n.inst}` : `co-author · ${n.inst}`}<br>degree ${deg} · group #${n.community}`
});
invalidation.then(() => gvI.kill());
display(legend([["IISER Pune faculty", "var(--pune)"], ["IISER Kolkata faculty", "var(--kolkata)"], ["Indian co-author (other institute)", "var(--context)"]]));
display(gvI);
```

<p class="caveat">G_ind is built outward from our faculty. An outside co-author only appears through one of our papers, so their degree counts only those papers, and every bridge between groups runs through our faculty by construction. The high modularity and clustering describe this sampling more than Indian science as a whole.</p>

```js
const keys = [["nodes", "People"], ["edges", "Co-author links"], ["isolates", "With no co-author"], ["giant_share", "Share in largest component"],
  ["mean_degree", "Mean co-authors"], ["transitivity", "Transitivity"], ["avg_path_gcc", "Average path (largest component)"],
  ["communities_leiden", "Groups (2+ people)"], ["modularity_leiden", "Modularity"],
  ["nmi_community_department", "Groups vs departments (NMI)"], ["nmi_community_institute", "Groups vs institutes (NMI)"]];
display(Inputs.table(keys.map(([k, metric]) => ({metric, G_fac: SF[k], G_ind: SI[k]})), {rows: 12, sort: null, layout: "auto", select: false}));
```

## Has collaboration grown over time?

```js
const snapTxt = (g) => {
  const s = M.snapshots.filter((d) => d.graph === g);
  return [s[0], s.at(-1)];
};
const [f0, f1] = snapTxt("G_fac");
```

${answer(html`The faculty network filled in over the decade. Counting all co-authorships up to each year, faculty-to-faculty links grew from ${f0.edges} (${f0.year}) to ${f1.edges} (${f1.year}), and the largest connected group went from ${pct(f0.giant_share)} to ${pct(f1.giant_share)} of linked faculty. These counts are cumulative, so they can only rise; the change in the share is the informative part.`)}

```js
display(resize((width) => Plot.plot({
  width, height: 260, x: {tickFormat: "d", label: null}, y: {grid: true, label: "share in largest component (%)", percent: true, domain: [0, 100]},
  color: {domain: ["G_fac", "G_ind"], range: ["var(--pune)", "var(--context)"], legend: true},
  marks: [Plot.line(M.snapshots, {x: "year", y: "giant_share", stroke: "graph", strokeWidth: 2}),
          Plot.dot(M.snapshots, {x: "year", y: "giant_share", fill: "graph", r: 3, tip: true,
            title: (d) => `${d.graph} up to ${d.year}\n${d.nodes} people · ${d.edges} links\nlargest component ${d3.format(".0%")(d.giant_share)}`})]
})));
```

<details class="how"><summary>How it's computed</summary>
<p>Each point is the graph of all co-authorships up to that year. People without any link yet are not counted.</p>
</details>

## How unequal is collaboration?

```js
const cc = ["G_fac", "G_ind"].flatMap((g) => M.coauthorship[g].degree_ccdf.map((d) => ({...d, graph: g})));
const degI = GI.nodes.map((n) => n.degree);
```

${answer(html`Very unequal. In G_ind the median person has ${d3.median(degI)} co-authors, while the best-connected have ${d3.sort(degI, d3.descending).slice(0, 3).join(", ")}. The distribution has a heavy tail.`)}

```js
display(resize((width) => Plot.plot({
  width, height: 280, x: {type: "log", label: "co-authors k", grid: true}, y: {type: "log", label: "share with at least k co-authors", grid: true},
  color: {domain: ["G_fac", "G_ind"], range: ["var(--pune)", "var(--context)"], legend: true},
  marks: [Plot.line(cc, {x: "k", y: "p", stroke: "graph", strokeWidth: 2}), Plot.dot(cc, {x: "k", y: "p", fill: "graph", r: 2.5, tip: true})]
})));
```

<p class="caveat">We do not claim a power law. A fitted exponent (G_ind: α = ${SI.powerlaw_degree?.alpha} above k = ${SI.powerlaw_degree?.xmin}) comes without a goodness-of-fit test or a comparison against a lognormal, so it only describes the tail's slope.</p>
