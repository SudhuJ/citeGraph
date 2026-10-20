---
title: Overview
toc: false
---

# IISER Pune & IISER Kolkata, 2016–2026

<p class="muted">DPCN 2026 · Group 19. Every paper by a current regular faculty member, written while they were at the institute (source: OpenAlex). Papers with 100 or more authors, mostly from the CMS experiment, are counted separately on the <a href="./collaborations">Big collaborations</a> page and left out of everything else.</p>

```js
import {INST, instVar, pct, num, ORIGIN} from "./components/defs.js";
const papers = FileAttachment("data/papers.csv").csv({typed: true});
const faculty = FileAttachment("data/faculty.csv").csv({typed: true});
const origin = FileAttachment("data/origin.csv").csv({typed: true});
const conn = FileAttachment("data/connections.csv").csv({typed: true});
const M = FileAttachment("data/network_metrics.json").json();
const FC = FileAttachment("data/faccit_graph.json").json();
```

```js
const P = papers.filter((d) => !d.hyperauthored);
const byInst = (inst) => P.filter((d) => d.institution === inst);
const growth = (inst) => {
  const n = (y) => byInst(inst).filter((d) => d.year === y).length;
  return n(2025) / n(2016) - 1;
};
const ranked = P.filter((d) => /^Q[1-4]$/.test(d.quartile ?? ""));
const q1 = ranked.length ? ranked.filter((d) => d.quartile === "Q1").length / ranked.length : null;
const originShare = (inst, dir, cats) => {
  const rows = origin.filter((d) => d.institution === inst && d.direction === dir);
  return d3.sum(rows.filter((d) => cats.includes(d.category)), (d) => d.n) / d3.sum(rows, (d) => d.n);
};
const GF = M.coauthorship.G_fac.summary;
const topPartners = (inst) => conn.filter((d) => d.your_inst === inst).toSorted((a, b) => b.shared_papers - a.shared_papers)
  .slice(0, 3).map((d) => d.partner_inst).join(", ");
```

<div class="grid grid-cols-4">
  ${INST.map((inst) => {
    const p = byInst(inst), f = faculty.filter((d) => d.institution === inst);
    return html`<div class="card"><h2><span class="swatch" style="background:${instVar(inst)}"></span>${inst}</h2>
      <div class="big">${num(p.length)}</div><div class="muted">papers · ${num(d3.sum(p, (d) => d.citations))} citations</div>
      <div class="muted">${f.filter((d) => d.papers > 0).length} of ${f.length} faculty with papers · median h-index ${d3.median(f, (d) => d.h_index)}</div></div>`;
  })}
</div>

## What we found

<ol class="findings">
  <li><b>Output has grown steadily.</b> Between 2016 and 2025, yearly output rose ${pct(growth("IISER Kolkata"))} at Kolkata and ${pct(growth("IISER Pune"))} at Pune. Part of this growth is new faculty joining, so the per-faculty view matters. <a href="./output">Output & venues →</a></li>
  <li><b>Most papers appear in top-quartile journals.</b> ${q1 == null ? "Quartiles are not loaded yet." : html`${pct(q1)} of papers in ranked journals are in a Q1 venue. This uses SCImago's best quartile across subject categories, so it is an upper bound.`} <a href="./faculty">Faculty & departments →</a></li>
  <li><b>Faculty rarely co-author with each other.</b> ${GF.isolates} of ${GF.nodes} publishing faculty have no paper with another faculty member of either institute. The co-author groups that do exist follow departments, not institutes. <a href="./authorship-network">Collaboration →</a></li>
  <li><b>Inside the institutes, almost all citations are self-citations.</b> ${pct(M.citation.summary.self_share)} of citations between our own papers share an author. Only ${num(FC.summary.citation_links)} citation links go from one faculty member's work to a colleague they never co-authored with. <a href="./citation-network">Knowledge flow →</a></li>
  <li><b>Our papers are cited mostly from abroad.</b> About ${pct(originShare("IISER Pune", "in", ["abroad or unknown"]))} (Pune) and ${pct(originShare("IISER Kolkata", "in", ["abroad or unknown"]))} (Kolkata) of citations come from papers with no Indian author. Other Indian institutes give ${pct(originShare("IISER Pune", "in", ["other Indian only", "India + abroad"]))} and ${pct(originShare("IISER Kolkata", "in", ["other Indian only", "India + abroad"]))}. <a href="./connectivity">India & the world →</a></li>
  <li><b>Neighbours are among the strongest Indian partners.</b> About ${pct(P.filter((d) => d.institution === "IISER Pune" && d.coauthor_institutes).length / byInst("IISER Pune").length)} of Pune's papers and ${pct(P.filter((d) => d.institution === "IISER Kolkata" && d.coauthor_institutes).length / byInst("IISER Kolkata").length)} of Kolkata's have a co-author at another Indian institution. Pune's top partners are ${topPartners("IISER Pune")}. Kolkata's are ${topPartners("IISER Kolkata")}. <a href="./connectivity">India & the world →</a></li>
</ol>
