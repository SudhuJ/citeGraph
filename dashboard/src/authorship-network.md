---
title: Collaboration
---

# Collaboration

```js
import {graphView, legend} from "./components/graph.js";
import {INST, instColor, shortInst, pct, num, answer, measure} from "./components/defs.js";
const M = FileAttachment("data/network_metrics.json").json();
const GF = FileAttachment("data/fac_graph.json").json();
const GI = FileAttachment("data/ind_graph.json").json();
```

```js
const SF = M.coauthorship.G_fac.summary, SI = M.coauthorship.G_ind.summary;
const fc = M.faculty_comparison;
const deptOf = (n) => `${shortInst(n.inst)} · ${n.dept}`;
// neighbours in G_fac
const nbF = GF.nodes.map(() => new Set());
GF.edges.forEach(([s, t]) => { nbF[s].add(t); nbF[t].add(s); });
// each faculty co-author link: same department, other department in the same institute, or the other institute
const linkKind = ([s, t]) => {
  const a = GF.nodes[s], b = GF.nodes[t];
  return a.inst !== b.inst ? "Pune–Kolkata" : a.dept !== b.dept ? "same institute, other department" : "same department";
};
const kinds = ["same department", "same institute, other department", "Pune–Kolkata"];
const kindN = Object.fromEntries(kinds.map((k) => [k, GF.edges.filter((e) => linkKind(e) === k).length]));
const linked = GF.nodes.filter((n, i) => nbF[i].size > 0).length;
// a readable "Pune Chemistry 9, Kolkata Chemical Sciences 3" summary of a set of faculty
const mix = (people, key = deptOf, top = 3, unit = "") => d3.rollups(people, (v) => v.length, key)
  .sort((a, b) => b[1] - a[1]).slice(0, top).map(([k, n]) => (unit ? `${k} (${n} ${unit})` : `${k} ${n}`)).join(", ");
```

<div class="terms">
<h3>The two graphs on this page</h3>
<dl>
<dt>G_fac, the faculty graph</dt>
<dd>One node for each of our ${SF.nodes} publishing faculty at IISER Pune and IISER Kolkata. Two faculty are linked if they wrote at least one paper together in 2016–26.</dd>
<dt>G_ind, the Indian graph</dt>
<dd>G_fac plus every co-author on our papers whose affiliation is an Indian institution other than the two IISERs, for example CSIR-NCL, TIFR or Savitribai Phule Pune University. That adds ${num(SI.nodes - SF.nodes)} people. Our own students and postdocs are not in it, and neither are foreign co-authors.</dd>
<dt>Groups</dt>
<dd>Found with the Leiden algorithm. It splits a graph into groups whose members have many more links among themselves than the same number of links placed at random would give. Groups are not the same as connected pieces of the graph: one connected cluster can split into several groups if it has dense cores joined by a few links.</dd>
</dl>
<p class="muted">Papers with 100 or more authors are left out of both graphs (see <a href="./collaborations">Big collaborations</a>). A link is stronger when two people share more papers and when those papers have fewer authors.</p>
</div>

## Do faculty co-author with each other?

${measure(html`In G_fac, how many faculty have at least one faculty co-author, and, for every co-author link, whether the two people are in the same department, in different departments of the same institute, or at different institutes.`)}

${answer(html`Within their own institute, yes; across the two institutes, almost never. ${num(linked)} of ${SF.nodes} faculty (${pct(linked / SF.nodes)}) have at least one faculty co-author. Of the ${GF.edges.length} links between them, ${pct(kindN["same department"] / GF.edges.length)} stay in one department and ${pct(kindN["same institute, other department"] / GF.edges.length)} cross departments within an institute. Only ${kindN["Pune–Kolkata"]} links (${pct(kindN["Pune–Kolkata"] / GF.edges.length)}) join Pune and Kolkata. Departments are not walls, but the two institutes are nearly separate.`)}

```js
const isoDept = d3.rollups(GF.nodes.map((n, i) => ({...n, iso: nbF[i].size === 0})), (v) => ({n: v.length, iso: d3.sum(v, (d) => d.iso)}), deptOf)
  .map(([dept, m]) => ({dept, ...m, share: m.iso / m.n, inst: dept.startsWith("Pune") ? "IISER Pune" : "IISER Kolkata"}))
  .filter((d) => d.n >= 5).sort((a, b) => b.share - a.share);
```

${answer(html`How isolated faculty are depends on the field. In ${isoDept.slice(0, 2).map((d) => `${d.dept} ${pct(d.share)}`).join(" and ")} of faculty have no faculty co-author, against ${isoDept.slice(-2).map((d) => `${pct(d.share)} in ${d.dept}`).join(" and ")}. Part of this is how the fields work: mathematics and the humanities often publish alone or with students, and students are not in this graph.`)}

```js
display(resize((width) => Plot.plot({
  width, height: 30 + 22 * isoDept.length, marginLeft: 260, x: {percent: true, label: "faculty with no faculty co-author (%)", grid: true, domain: [0, 100]},
  y: {label: null, domain: isoDept.map((d) => d.dept)}, color: instColor,
  marks: [Plot.barX(isoDept, {x: "share", y: "dept", fill: "inst", inset: 2, tip: true, title: (d) => `${d.dept}\n${d.iso} of ${d.n} faculty have no faculty co-author`}),
          Plot.ruleX([0])]
})));
```
<p class="muted">Departments with at least 5 publishing faculty.</p>

```js
const facColor = (n) => (n.inst === "IISER Pune" ? "pune" : "kolkata");
const gvF = graphView({
  nodes: GF.nodes, edges: GF.edges, height: 600,
  color: facColor, size: (n) => 3 + 1.6 * Math.sqrt(n.degree), label: (n) => n.label, labelThreshold: 4,
  edgeSize: (e) => 0.5 + Math.log2(1 + e[3]) * 0.45,
  tooltip: (n, deg) => `<b>${n.label}</b>${n.dept} · ${n.inst}<br>${deg} faculty co-authors · group #${n.community}`
});
invalidation.then(() => gvF.kill());
display(legend([["IISER Pune faculty", "var(--pune)"], ["IISER Kolkata faculty", "var(--kolkata)"]]));
display(gvF);
```
<p class="muted">G_fac. Node size: number of faculty co-authors. Edge width: number of shared papers. The two colours barely mix: the few Pune–Kolkata links are the only bridges. Faculty with no faculty co-author sit around the edge.</p>

## What are the co-author groups made of?

```js
const groupsF = d3.groups(GF.nodes.map((n, i) => ({...n, i})).filter((n) => nbF[n.i].size > 0), (n) => n.community)
  .map(([id, v]) => ({id, size: v.length, insts: new Set(v.map((n) => n.inst)).size, depts: new Set(v.map(deptOf)).size,
    pune: v.filter((n) => n.inst === "IISER Pune").length, kolkata: v.filter((n) => n.inst === "IISER Kolkata").length,
    mix: mix(v), members: v.toSorted((a, b) => b.degree - a.degree).slice(0, 3).map((n) => n.label).join(", ")}))
  .filter((g) => g.size >= 2).sort((a, b) => b.size - a.size);
const g3 = groupsF.filter((g) => g.size >= 3);
// "mixed": at least two members from each institute
const mixed = g3.filter((g) => Math.min(g.pune, g.kolkata) >= 2);
const range = (xs) => (d3.min(xs) === d3.max(xs) ? `${d3.min(xs)}` : `${d3.min(xs)}–${d3.max(xs)}`);
```

${measure(html`The groups Leiden finds in G_fac. For each group: its size, which institutes and departments its members come from, and its best-connected members.`)}

${answer(html`There are ${groupsF.length} groups of two or more faculty, ${g3.length} of them with three or more. Of those ${g3.length}, ${g3.length - mixed.length} have at most one member from the other institute, while ${g3.filter((g) => g.depts > 1).length} mix departments. The largest are interdisciplinary: ${groupsF.slice(0, 2).map((g) => `${g.size} people (${g.mix})`).join(" and ")}. ${mixed.length ? `Only ${mixed.length} ${mixed.length === 1 ? "group has" : "groups have"} at least two members at each IISER: ${mixed.map((g) => `${g.size} people (${g.pune} Pune, ${g.kolkata} Kolkata)`).join(", ")}.` : "No group has two or more members at each IISER."} So the real research units are cross-department clusters inside one institute.`)}

```js
display(Inputs.table(groupsF, {
  columns: ["id", "size", "pune", "kolkata", "mix", "members"],
  header: {id: "Group", size: "Faculty", pune: "Pune", kolkata: "Kolkata", mix: "Main departments (faculty in each)", members: "Best-connected members"},
  format: {id: (x) => `#${x}`}, width: {mix: 360, members: 300}, rows: 12, layout: "auto", select: false
}));
```

<details class="how"><summary>How groups are found</summary>
<ul>
<li>Leiden maximises <i>modularity</i>: the share of link strength that falls inside groups, minus the share expected if the same links were placed at random. G_fac's best split scores ${SF.modularity_leiden} on a scale up to 1, which means the groups are clear-cut.</li>
<li>Faculty with no faculty co-author are left out; Leiden would make each of them a group of one.</li>
<li>Louvain, an older algorithm with the same goal, gives almost the same groups (agreement score ${SF.nmi_leiden_louvain}, where 1 means identical).</li>
</ul>
</details>

## Who connects the groups?

```js
const brokers = GF.nodes.map((n, i) => ({...n, i,
    groups: new Set([n.community, ...[...nbF[i]].map((j) => GF.nodes[j].community)]).size,
    depts: new Set([...nbF[i]].map((j) => deptOf(GF.nodes[j]))).size,
    otherInst: [...nbF[i]].some((j) => GF.nodes[j].inst !== n.inst)}))
  .sort((a, b) => b.betweenness - a.betweenness).slice(0, 10);
const top5 = brokers.slice(0, 5);
```

${measure(html`<i>Betweenness</i>. Take every pair of faculty and find the shortest chain of co-authors between them. A person's betweenness is the share of these chains that pass through them. Someone with high betweenness is a bridge: without them, many pairs would be further apart or not connected at all.`)}

${answer(html`A handful of people hold the network together, and they are the ones whose co-authors span departments. Each of the top five, ${top5.map((d) => `${d.label} (${shortInst(d.inst)}, ${d.dept})`).join(", ")}, has faculty co-authors in ${range(top5.map((d) => d.depts))} departments and touches ${range(top5.map((d) => d.groups))} groups. ${top5.filter((d) => d.otherInst).length} of the five also have a co-author at the other IISER, which makes them the few links between Pune and Kolkata.`)}

```js
display(Inputs.table(brokers, {
  columns: ["label", "inst", "dept", "degree", "depts", "groups", "betweenness"],
  header: {label: "Faculty", inst: "Institute", dept: "Department", degree: "Faculty co-authors", depts: "Their departments", groups: "Groups touched", betweenness: "Betweenness"},
  format: {inst: shortInst, betweenness: d3.format(".3f")}, sort: "betweenness", reverse: true, layout: "auto", select: false
}));
```

```js
const brokersI = fc.toSorted((a, b) => b.btw_ind - a.btw_ind).slice(0, 5);
```

${answer(html`In the wider Indian network (G_ind), the top bridges are ${brokersI.slice(0, 3).map((d) => `${d.name} (${shortInst(d.inst)}, co-authors at ${d.partner_insts_ind} institutes)`).join(", ")}. Bridging among colleagues and bridging in India go together but are not the same: the two rankings agree only partly (rank correlation ${M.spearman_fac_vs_ind.betweenness}, where 1 would be the same order).`)}

<details class="how"><summary>How betweenness is computed</summary>
<p>Shortest chains use distance 1/strength, so two people who share many small-team papers are "close". Values are normalised by the number of pairs, so they lie between 0 and 1. In G_ind, the outside co-authors also count as possible bridges.</p>
</details>

## What changes when we add Indian co-authors?

```js
const groupsI = d3.groups(GI.nodes, (n) => n.community).map(([id, v]) => {
  const f = v.filter((n) => n.faculty), e = v.filter((n) => !n.faculty);
  return {id, size: v.length, faculty: f.length, insts: new Set(f.map((n) => n.inst)).size,
    mix: mix(f), partners: mix(e, (n) => n.inst, 3, "people")};
}).filter((g) => g.size >= 2).sort((a, b) => b.faculty - a.faculty || b.size - a.size);
const oneLab = groupsI.filter((g) => g.faculty === 1).length;
const both = groupsI.filter((g) => g.insts > 1);
```

${measure(html`In G_ind: how much of the graph is one connected piece, how many of our faculty each Leiden group contains, and which institutes the outside members come from.`)}

${answer(html`Outside co-authors join the network up. ${pct(SI.giant_share)} of G_ind is one connected piece, against ${pct(SF.giant_share)} of G_fac, because many faculty who never write together share a collaborator elsewhere. Leiden finds ${groupsI.length} groups, and ${oneLab} of them contain exactly one of our faculty: each is one lab and its outside collaborators. The groups with several faculty are where labs meet, and ${both.length} groups contain faculty from both IISERs. The largest has ${both[0]?.faculty} of our faculty (${both[0]?.mix}), and its main outside members are from ${both[0]?.partners}. Pune and Kolkata faculty who rarely co-author directly end up in the same groups through shared outside partners.`)}

```js
display(Inputs.table(groupsI.filter((g) => g.faculty >= 3), {
  columns: ["id", "size", "faculty", "mix", "partners"],
  header: {id: "Group", size: "People", faculty: "Our faculty", mix: "Our faculty by department", partners: "Main outside institutes"},
  format: {id: (x) => `#${x}`}, width: {mix: 320, partners: 360}, rows: 10, layout: "auto", select: false
}));
```
<p class="muted">Groups with three or more of our faculty.</p>

```js
const gvI = graphView({
  nodes: GI.nodes, edges: GI.edges, height: 720,
  color: (n) => (n.faculty ? facColor(n) : "context"),
  size: (n) => (n.faculty ? 3.5 + 0.55 * Math.sqrt(n.degree) : 2.8 + 0.35 * Math.sqrt(n.degree)),
  label: (n) => (n.faculty ? n.label : ""), labelThreshold: 7,
  edgeSize: (e) => 0.5 + Math.log2(1 + e[3]) * 0.45,
  tooltip: (n, deg) => `<b>${n.label}</b>${n.faculty ? `${n.dept} · ${n.inst}` : `co-author · ${n.inst}`}<br>${deg} co-authors · group #${n.community}`
});
invalidation.then(() => gvI.kill());
display(legend([["IISER Pune faculty", "var(--pune)"], ["IISER Kolkata faculty", "var(--kolkata)"], ["Indian co-author (other institute)", "var(--context)"]]));
display(gvI);
```

<p class="caveat">G_ind is built outward from our faculty. An outside co-author appears only through one of our papers, so every link between two outside people comes from a paper with one of our faculty on it. The graph therefore shows our faculty's Indian neighbourhood, not Indian science as a whole.</p>

## Has collaboration grown over time?

```js
const [f0, f1] = (() => { const s = M.snapshots.filter((d) => d.graph === "G_fac"); return [s[0], s.at(-1)]; })();
```

${measure(html`G_fac and G_ind rebuilt with all papers up to each year, and the share of linked people who sit in the largest connected piece.`)}

${answer(html`Yes, the faculty network has knitted together. Faculty-to-faculty links grew from ${f0.edges} (up to ${f0.year}) to ${f1.edges} (up to ${f1.year}), and the largest connected piece went from ${pct(f0.giant_share)} to ${pct(f1.giant_share)} of linked faculty. The counts are cumulative, so they can only rise; the growing share is the informative part: new links increasingly join existing clusters rather than forming separate ones.`)}

```js
display(resize((width) => Plot.plot({
  width, height: 260, x: {tickFormat: "d", label: null}, y: {grid: true, label: "share in largest connected piece (%)", percent: true, domain: [0, 100]},
  color: {domain: ["G_fac", "G_ind"], range: ["var(--pune)", "var(--context)"], legend: true},
  marks: [Plot.line(M.snapshots, {x: "year", y: "giant_share", stroke: "graph", strokeWidth: 2}),
          Plot.dot(M.snapshots, {x: "year", y: "giant_share", fill: "graph", r: 4, tip: true,
            title: (d) => `${d.graph} up to ${d.year}\n${d.nodes} people · ${d.edges} links\nlargest piece ${d3.format(".0%")(d.giant_share)}`})]
})));
```

## How many co-authors does a typical person have?

```js
const bins = [[0, 0, "0"], [1, 1, "1"], [2, 2, "2"], [3, 5, "3–5"], [6, 10, "6–10"], [11, 20, "11–20"], [21, 1e9, "21+"]];
const hist = (g, name) => bins.map(([lo, hi, bin]) => ({graph: name, bin, share: g.nodes.filter((n) => n.degree >= lo && n.degree <= hi).length / g.nodes.length}));
const H = [...hist(GF, "G_fac (faculty co-authors)"), ...hist(GI, "G_ind (all Indian co-authors)")];
const degI = GI.nodes.map((n) => n.degree), degF = GF.nodes.map((n) => n.degree);
```

${measure(html`Each person's number of co-authors in the graph (their <i>degree</i>).`)}

${answer(html`Few, with a long tail. In G_fac the median faculty member has ${d3.median(degF)} faculty co-author${d3.median(degF) === 1 ? "" : "s"} and the most connected have ${d3.sort(degF, d3.descending).slice(0, 3).join(", ")}. In G_ind the median person has ${d3.median(degI)} co-authors and the most connected have ${d3.sort(degI, d3.descending).slice(0, 3).join(", ")}. A few large labs account for a big share of all links.`)}

```js
display(resize((width) => Plot.plot({
  width, height: 240, x: {label: "number of co-authors", domain: bins.map((b) => b[2])}, y: {percent: true, grid: true, label: "share of people (%)"},
  fx: {label: null}, color: {domain: ["G_fac (faculty co-authors)", "G_ind (all Indian co-authors)"], range: ["var(--pune)", "var(--context)"], legend: true},
  marks: [Plot.barY(H, {fx: "graph", x: "bin", y: "share", fill: "graph", inset: 2, tip: true}), Plot.ruleY([0])]
})));
```

<details class="how"><summary>All graph statistics</summary>

```js
const keys = [["nodes", "People"], ["edges", "Co-author links"], ["isolates", "With no co-author"], ["giant_share", "Share in largest connected piece"],
  ["mean_degree", "Mean co-authors"], ["transitivity", "Transitivity (share of co-author pairs whose co-authors also co-author)"], ["avg_path_gcc", "Average shortest chain (largest piece)"],
  ["communities_leiden", "Groups (2+ people)"], ["modularity_leiden", "Modularity"]];
display(Inputs.table(keys.map(([k, metric]) => ({metric, G_fac: SF[k], G_ind: SI[k]})), {rows: 12, sort: null, layout: "auto", select: false}));
```
</details>
