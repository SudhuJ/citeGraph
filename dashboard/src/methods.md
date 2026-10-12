---
title: Methods & data
---

# Methods & data

```js
const faculty = FileAttachment("data/faculty.csv").csv({typed: true});
const M = FileAttachment("data/network_metrics.json").json();
```

## Downloads (Week-2 deliverables)

```js
const files = [
  [FileAttachment("downloads/group19_data.csv"), "faculty × paper rows, all §5 columns plus extras"],
  [FileAttachment("downloads/citation_network.csv"), "directed edges (edge_kind: internal / in / out)"],
  [FileAttachment("downloads/authorship_network.csv"), "co-author pairs (faculty + Indian co-authors)"],
  [FileAttachment("downloads/indian_connections.csv"), "your_inst × partner_inst aggregates"]
];
display(html`<ul>${files.map(([f, d]) => html`<li><a href=${f.href} download=${f.name}>${f.name}</a>: ${d}</li>`)}</ul>`);
```

## Pipeline

| Step | Tool | What it does |
|---|---|---|
| Roster | httpx + selectolax | Scrapes the **regular-faculty** pages of both institutes (visiting, adjunct and emeritus excluded). |
| Author matching | OpenAlex + Python | Matches each name against every OpenAlex author ever affiliated with the institute. It keeps all compatible profiles (OpenAlex often splits one person into several) and drops namesakes with a different ORCID. Manual fixes live in `ref/author_overrides.csv`. |
| Works | OpenAlex API | All works 2016–2026 of the matched profiles, batched OR-filters, every response cached. |
| Citation links | OpenAlex API | `cites:` / `cited_by:` filters combined with `institutions.country_code:IN` give the Indian in-flow and out-flow without fetching ~400k references. |
| Build | DuckDB | Flattens the JSON to Parquet, dedupes papers, joins SCImago quartiles by ISSN + year, derives the Indian flags and writes the four CSVs. |
| Networks | python-igraph | PageRank, centralities, Leiden/Louvain, power-law fits, layouts. |
| Dashboard | Observable Framework + sigma.js 4 | Static site; WebGL graphs. |

## Key decisions

1. **Faculty only, affiliated at the time.** A faculty × paper row is kept only if the paper lists the faculty member with their IISER affiliation. Papers from before they joined are dropped. The exceptions are rows where the author list was truncated or had no parsed affiliation; those are kept and labelled in `affiliation_check`.
2. **Row grain** of `group19_data.csv` is faculty × paper. Paper-level statistics deduplicate first. Duplicate records (same DOI, or same normalised title + year) collapse onto the most-cited one.
3. **Kept types:** article, review, letter and conference-paper in journals, conferences or book series. Preprints, datasets, errata and peer reviews are dropped, and so are meeting-abstract venues that OpenAlex files as journals (APS/AGU/EGU/Goldschmidt/JpGU abstracts, ChemInform).
4. **Quartile** = SCImago "best quartile" for the closest SCImago year not after publication. SCImago ranks journals, conference proceedings and book series, and all three are used; trade journals are excluded. CORE ranks are used for conference papers when `ref/core.csv` is present.
5. **h-index:** the dataset (2016–2026) window is the primary measure; the OpenAlex lifetime value is shown for reference.
6. **Hyperauthorship:** OpenAlex truncates author lists at 100. Those ${M.hyperauthorship.hyper_papers} papers stay in the CSVs (`hyperauthored = true`) but are left out of the co-authorship graphs. The sensitivity analysis is on the authorship page.
7. **Two authorship graphs** (G_fac, G_ind), because the brief says both "faculty members" and "authors". Students and postdocs at our own institutes are in neither graph.
8. **Indian flags** (`cites_indian_inst`, `cited_by_indian_inst`, `coauthor_institutes`) refer to Indian institutions *other than the row's own institute*. IISER Pune ↔ IISER Kolkata counts as cross-institute.
9. **`total_citations`** in `indian_connections.csv` = citation links in both directions between the two institutions (`cites_in` + `cites_out` are given separately).

## Coverage

```js
const matched = faculty.filter((d) => d.matched).length, withPapers = faculty.filter((d) => d.papers > 0).length;
```

${matched} of ${faculty.length} roster faculty were matched to OpenAlex profiles; ${withPapers} have at least one paper in the window. The unmatched ones are recent hires whose earlier papers carry other affiliations. Faculty listed on the website but publishing under an unexpected name can be added in `ref/author_overrides.csv`.

```js
display(Inputs.table(faculty.filter((d) => d.papers === 0), {columns: ["name", "institution", "department", "designation", "matched"], layout: "auto", rows: 10}));
```
