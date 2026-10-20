---
title: Faculty & departments
---

# Faculty & departments

<p class="muted">Every number here leaves out papers with 100 or more authors (see <a href="./collaborations">Big collaborations</a>). Papers with 11–99 authors stay in and are counted in the "&gt;10 authors" column.</p>

```js
import {INST, instColor, shortInst, pct, num, answer, measure, shareBar} from "./components/defs.js";
const faculty = FileAttachment("data/faculty.csv").csv({typed: true});
const depts = FileAttachment("data/departments.csv").csv({typed: true});
```

```js
const pick = view(Inputs.radio(["Both", ...INST], {value: "Both", label: "Institute"}));
```

```js
const F = faculty.filter((d) => pick === "Both" || d.institution === pick);
const D = depts.filter((d) => (pick === "Both" || d.institution === pick) && d.papers > 0)
  .map((d) => ({...d, papers_per_faculty: d.papers / d.faculty_with_papers}));
const qLoaded = depts.some((d) => d.q1_share != null);
const ranked50 = (key) => D.filter((d) => d.journal_papers >= 50 && d[key] != null).toSorted((a, b) => b[key] - a[key]);
const best = (key) => ranked50(key)[0];
const worst = (key) => ranked50(key).at(-1);
const dn = (d) => `${shortInst(d.institution)} ${d.department}`;
```

## How do departments compare?

${measure(html`For each department: papers, citations, the median h-index of its faculty, and the two bars the course asked for: the share of ranked journal papers in Q1 venues, and the share in Q1 venues whose impact-factor proxy is above 5.`)}

${qLoaded
  ? answer(html`On Q1 alone, departments are fairly close: among those with at least 50 journal papers, the Q1 share runs from ${pct(worst("q1_share").q1_share)} (${dn(worst("q1_share"))}) to ${pct(best("q1_share").q1_share)} (${dn(best("q1_share"))}). The stricter Q1 & IF>5 bar spreads them out, from ${pct(worst("q1_if5_share").q1_if5_share)} (${dn(worst("q1_if5_share"))}) to ${pct(best("q1_if5_share").q1_if5_share)} (${dn(best("q1_if5_share"))}). Much of that spread follows how often each field cites: even the leading mathematics journals have an impact-factor proxy below 5.`)
  : answer(html`Quartile shares need the SCImago files, which are not loaded yet. Output per faculty member is highest in ${shortInst(D.toSorted((a, b) => b.papers_per_faculty - a.papers_per_faculty)[0].institution)} ${D.toSorted((a, b) => b.papers_per_faculty - a.papers_per_faculty)[0].department}.`)}

```js
display(Inputs.table(D, {
  columns: ["institution", "department", "faculty", "papers", "papers_per_faculty", "citations", "median_h", "q1_share", "q1_if5_share", "large_team_share"],
  header: {institution: "Institute", department: "Department", faculty: "Faculty", papers: "Papers", papers_per_faculty: "Papers / faculty",
           citations: "Citations", median_h: "Median h", q1_share: "Q1 share", q1_if5_share: "Q1 & IF>5 share", large_team_share: ">10 authors"},
  format: {institution: shortInst, papers_per_faculty: d3.format(".1f"), q1_share: (x) => shareBar(x), q1_if5_share: (x) => shareBar(x),
           large_team_share: (x) => pct(x)},
  sort: "papers", reverse: true, layout: "auto", select: false, rows: 16
}));
```

<p class="caveat">Departments differ in how much and where their fields publish. Mathematics writes fewer, longer papers, and its journals have lower citation rates, so its impact-factor shares are lower by nature. Compare a department with itself across the two institutes, not with other fields.</p>
<details class="how"><summary>How it's computed</summary>
<ul>
<li>A paper counts once in every department that has an author on it.</li>
<li><b>Q1 share</b> = Q1 papers ÷ journal papers whose venue SCImago ranks.</li>
<li><b>Q1 & IF>5</b> adds a second condition: the journal's SCImago citations per document over two years (our open stand-in for the impact factor) is above 5.</li>
<li><b>Median h</b> is the median of the faculty members' h-index over 2016–2026 papers.</li>
</ul>
</details>

## Who are the most productive and most cited faculty?

```js
const q = view(Inputs.search(F, {placeholder: "Search faculty…", columns: ["name", "department", "institution"]}));
```

```js
display(Inputs.table(q, {
  columns: ["name", "institution", "department", "designation", "papers", "citations", "h_index", "h_index_lifetime", "q1_share", "top_journal", "large_team_papers", "hyper_papers"],
  header: {name: "Name", institution: "Institute", department: "Department", designation: "Designation", papers: "Papers",
           citations: "Citations", h_index: "h-index (2016–26)", h_index_lifetime: "h-index (career)", q1_share: "Q1 share",
           top_journal: "Most frequent journal", large_team_papers: ">10 authors", hyper_papers: "100+ authors (excluded)"},
  format: {institution: shortInst, q1_share: (x) => pct(x),
           name: (x, i, data) => html`<a href=${data[i].profile_url} target="_blank">${x}</a>`},
  width: {name: 190, department: 170, designation: 170, top_journal: 220},
  sort: "h_index", reverse: true, rows: 15, layout: "auto"
}));
```

<details class="how"><summary>How it's computed</summary>
<p><b>h-index (2016–26)</b>: the largest h such that h of the person's papers in this dataset have at least h citations each. <b>Career h-index</b> is OpenAlex's value over the whole career, including papers before 2016, at other institutions and with 100+ authors, so the two are not comparable.</p>
</details>

## How is impact spread across faculty?

```js
const hs = F.filter((d) => d.papers > 0);
const top10share = (inst) => {
  const c = hs.filter((d) => d.institution === inst).map((d) => d.citations).sort(d3.descending);
  return d3.sum(c.slice(0, Math.ceil(c.length / 10))) / d3.sum(c);
};
```

${measure(html`The share of each institute's citations held by its top 10% of faculty, and each faculty member's h-index: the largest h such that h of their 2016–26 papers have at least h citations each.`)}

${answer(html`Impact is concentrated. The top 10% of faculty by citations account for ${(pick === "Both" ? INST : [pick]).map((i) => `${pct(top10share(i))} of ${shortInst(i)}'s citations`).join(" and ")}. The median 2016–26 h-index is ${d3.median(hs, (d) => d.h_index)}.`)}

<div class="grid grid-cols-2">
<div class="card">

### h-index distribution

```js
display(resize((width) => Plot.plot({
  width, height: 300, x: {label: "h-index (2016–2026 papers)"}, y: {grid: true, label: "faculty"},
  color: instColor, fy: {label: null},
  marks: [
    Plot.rectY(hs, Plot.binX({y: "count"}, {x: "h_index", fill: "institution", fy: "institution", interval: 2, inset: 1, tip: true})),
    Plot.ruleY([0])
  ]
})));
```
</div>
<div class="card">

### Papers vs citations

```js
display(resize((width) => Plot.plot({
  width, height: 300, x: {type: "log", label: "papers (log)", grid: true}, y: {type: "log", label: "citations (log)", grid: true},
  color: instColor,
  marks: [
    Plot.dot(hs.filter((d) => d.citations > 0), {x: "papers", y: "citations", fill: "institution", r: 4,
      stroke: "var(--theme-background)", tip: true, title: (d) => `${d.name}\n${d.department}\n${d.papers} papers · ${d.citations} citations · h=${d.h_index}`})
  ]
})));
```
</div>
</div>
