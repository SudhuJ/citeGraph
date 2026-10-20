// Shared definitions for every page: institutes, colour roles, formatting, small widgets.
import {html} from "npm:htl";
import * as d3 from "npm:d3";

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

// inline bar for table cells: share of a 0–1 value
export const shareBar = (x, color = "var(--q2)") => x == null
  ? html`<span class="muted">—</span>`
  : html`<span class="cellbar"><span style="width:${Math.round(x * 100)}%;background:${color}"></span></span> ${pct(x)}`;
