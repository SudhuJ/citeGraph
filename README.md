# citeGraph
Citation-Network for DPCN, Monsoon 26 · **Group 19: IISER Pune & IISER Kolkata**, 2016–2026.

**Live dashboard: https://sudhuj.github.io/citeGraph/**

Maps every paper by the current regular faculty of both institutes and builds the
citation and co-authorship networks, the Indian connectivity analysis, an interactive
dashboard and a short statistics report. Data source: [OpenAlex](https://openalex.org) (CC0).

## Stack (open source, minimal dependencies)

| Layer | Tool |
|---|---|
| Python toolchain | uv · Python 3.14 · ruff |
| Fetching | httpx (OpenAlex REST, cached on disk) · selectolax (roster scraping) |
| Data | DuckDB (the only data engine: JSON → Parquet → CSV, fuzzy joins in SQL) |
| Networks | python-igraph 1.0 (PageRank, betweenness, Leiden/Louvain, layouts, power-law fits) |
| Dashboard | Observable Framework 1.13 (static site) + sigma.js 4 / graphology (WebGL graphs, vendored with esbuild) |
| Report | Typst (via the `typst` PyPI package) + Lilaq plots |

## Quick start

```bash
make setup          # uv sync + npm install + vendor the graph bundle
make dash           # dashboard on http://localhost:3000 (data already built)
```

Rebuilding from scratch needs a free OpenAlex API key in `.env` (`OPENALEX_API_KEY=…`):

```bash
make roster match   # scrape rosters, match to OpenAlex → review data/faculty_review.csv
make data           # fetch → stage → institutions → topics → build → networks → export → check
make report         # report/report.pdf
make site           # static dashboard in dashboard/dist/
make deploy         # build + publish to https://sudhuj.github.io/citeGraph/
```

All API responses are cached in `data/cache/`, so re-runs cost nothing. A full fetch uses roughly 3k of the 10k daily credits.

## Deliverables (`data/out/`)

| File | Content |
|---|---|
| `group19_data.csv` | faculty × paper rows with every §5 column, plus `fac_id, department, openalex_id, field, subfield, n_authors, hyperauthored, affiliation_check` |
| `citation_network.csv` | `source_doi, target_doi, source_inst, target_inst, year` + `edge_kind` (internal / in / out) |
| `authorship_network.csv` | `author_a, author_b, paper_doi, inst_a, inst_b, year` + node IDs, faculty flags, cross-institution/cluster flags |
| `indian_connections.csv` | `your_inst, partner_inst, shared_papers, total_citations` + `cites_in, cites_out, partner_cluster, cross_cluster, jaccard_topics` |
| `faculty_stats.csv`, `network_*.csv` | faculty metrics, paper-level PageRank, faculty centralities |

`make check` validates these against the instruction note.

## Pipeline

```
pipeline/faculty.py        regular-faculty rosters (websites)          → data/faculty_seed.csv
pipeline/match_authors.py  roster → OpenAlex author profiles           → data/faculty.csv (+ review list)
pipeline/fetch.py          works, Indian citing / cited works          → data/raw/*.jsonl
pipeline/stage.sql         flatten JSON                                → data/stage/*.parquet
pipeline/institutions.py   Indian institutions → course clusters       → ref/institutions.csv
pipeline/topics.py         subfield profiles for topic Jaccard
pipeline/build.py          the four deliverable CSVs (DuckDB)          → data/out/
pipeline/networks.py       igraph analysis + layouts                   → dashboard/src/data/
pipeline/export.py         dashboard tables, downloads
pipeline/report.py         report/data.json → report/report.pdf
```

## Methodological decisions

- **Faculty** = regular faculty on the institute websites (no visiting/adjunct/emeritus). A paper counts only if it lists the faculty member with their IISER affiliation. Manual matching fixes go in `ref/author_overrides.csv`.
- **Two authorship graphs**, because the brief says both "faculty members" and "authors": G_fac (faculty only) and G_ind (faculty + Indian co-authors). They are compared on the dashboard and in the report.
- **Hyperauthorship:** OpenAlex truncates author lists at 100. Those papers (CMS etc.) stay in the CSVs, flagged, but are excluded from the co-authorship graphs and from the default PageRank ranking. Sensitivity results are shown.
- **Quartile** = SCImago best quartile for the nearest year not after publication; CORE rank for conference papers.
- See the dashboard's *Methods & data* page for the full list.

## Pending inputs

- **SCImago quartiles:** download the yearly CSVs from scimagojr.com (blocked for scripts) with type **All types** into `ref/scimago/scimago_<year>.csv`, then run `make build networks export report`. The build keeps journals, conferences & proceedings, and book series, and drops trade journals.
- **CORE ranks (optional, ICORE2026 export included):** CORE portal export → `ref/core.csv` (no header row; rank in the 5th column). IISER output is almost all journals, so this changes little.
