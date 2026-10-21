// Shared definitions for every page: institutes, colour roles, formatting, small widgets.
import {html} from "../../_npm/htl@1.0.0/11521f02.js";
import * as d3 from "../../_npm/d3@7.9.0/080cf928.js";

export const INST = ["IISER Pune", "IISER Kolkata"];
export const instVar = (i) => (i === "IISER Pune" ? "var(--pune)" : "var(--kolkata)");
export const instColor = {domain: INST, range: ["var(--pune)", "var(--kolkata)"], legend: true};
export const shortInst = (i) => i.replace("IISER ", "");

export const pct = (x, digits = 0) => (x == null || Number.isNaN(x) ? "—" : d3.format(`.${digits}%`)(x));
export const num = (x) => (x == null ? "—" : Math.round(x).toLocaleString("en-US"));

// "Top journal" papers for the top-30 list: ranked Q1 by SCImago with the impact-factor
// proxy (SCImago cites per document, 2 years) above 5. One definition used everywhere.
export const TOP_JOURNAL_RULE = "SCImago Q1 and impact-factor proxy above 5";
export const isTopJournal = (d) => d.quartile === "Q1" && d.if_proxy > 5;
export const hasQuartiles = (papers) => papers.some((d) => /^Q[1-4]$/.test(d.quartile ?? ""));

// Citation origin: ordered from closest to farthest, so the colours are one ordinal ramp
// (validated: dataviz ordinal checks, light and dark); the remainder is neutral grey.
export const ORIGIN = ["self", "own institute", "other Indian only", "India + abroad", "abroad or unknown"];
export const originLabel = {
  "self": "Self-citation (shared author)",
  "own institute": "Same IISER, different people",
  "other Indian only": "Other Indian institutes only",
  "India + abroad": "Indian and foreign authors",
  "abroad or unknown": "No Indian author, or unknown"
};
export const originColor = {domain: ORIGIN, range: ["var(--q1)", "var(--q2)", "var(--q3)", "var(--q4)", "var(--qna)"]};

// umbrella bodies that record overlap with the labs they cover (not labs themselves)
export const UMBRELLA = new Set(["Academy of Scientific and Innovative Research", "Homi Bhabha National Institute",
  "Council of Scientific and Industrial Research"]);
export const instName = (name) => (UMBRELLA.has(name) ? `${name} (an umbrella body)` : name);

// one sentence that answers the section's question
export const answer = (content) => html`<div class="answer">${content}</div>`;
// what we measured to answer it (shown before the answer)
export const measure = (content) => html`<p class="measure">${content}</p>`;

// inline bar for table cells: share of a 0–1 value
export const shareBar = (x, color = "var(--q2)") => x == null
  ? html`<span class="muted">—</span>`
  : html`<span class="cellbar"><span style="width:${Math.round(x * 100)}%;background:${color}"></span></span> ${pct(x)}`;

// "Our papers" (any of our faculty on it) and "self-citation" (the same person on both papers)
// are independent: this box defines both and splits one institute's incoming citations 2×2.
export function citationTerms(origin) {
  const rows = origin.filter((d) => d.direction === "in");
  const cell = (inst, ours, self) => d3.sum(rows.filter((d) => d.institution === inst && d.from_ours === ours
    && (d.category === "self") === self), (d) => d.n);
  const tab = (inst) => {
    const tot = d3.sum(rows.filter((d) => d.institution === inst), (d) => d.n);
    const c = (ours, self) => html`<td class=${ours && !self ? "hi" : ""}>${num(cell(inst, ours, self))} <span class="muted">(${pct(cell(inst, ours, self) / tot, 1)})</span></td>`;
    return html`<table class="xtab">
      <tr><th>${inst}: the citing paper…</th><th>shares an author</th><th>shares no author</th></tr>
      <tr><td>is one of our papers</td>${c(true, true)}${c(true, false)}</tr>
      <tr><td>is not one of our papers</td>${c(false, true)}${c(false, false)}</tr>
      <tr><td class="muted">all ${num(tot)} citations received</td><td></td><td></td></tr></table>`;
  };
  return html`<div class="terms"><h3>Two terms that are easy to confuse</h3>
    <dl><dt>Our papers</dt><dd>Papers with at least one IISER Pune or IISER Kolkata faculty member among the authors.</dd>
    <dt>Self-citation</dt><dd>The citing and the cited paper share at least one author: the same person is on both.</dd></dl>
    <p>The two are independent. A Pune chemist citing a Kolkata physicist is one of our papers citing another, but not a self-citation.
    A former student, now at another university, citing a paper they wrote with their IISER advisor is a self-citation, but not from one of our papers.
    The tables split every citation our papers receive both ways. The bold cell (one of our papers, no shared author) is faculty building on colleagues' work.
    Self-citations can only be detected when the citing paper has an Indian author, because we fetched author lists only for those, so the bottom-left cell is a lower bound.</p>
    <div class="grid grid-cols-2">${INST.map(tab)}</div></div>`;
}
