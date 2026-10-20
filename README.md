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
| `group19_data.csv` (extra columns) | also `large_team` (>10 authors), `sjr`, `if_proxy` (SCImago cites/doc over 2 years, an open stand-in for the impact factor) |
| `citation_network.csv` | `source_doi, target_doi, source_inst, target_inst, year` + `edge_kind` (internal / in / out), `self_citation`, `involves_hyper` |
| `authorship_network.csv` | `author_a, author_b, paper_doi, inst_a, inst_b, year` + node IDs, faculty flags, cross-institution/cluster flags |
| `indian_connections.csv` | `your_inst, partner_inst, shared_papers, total_citations` + `cites_in, cites_out, partner_cluster, cross_cluster, jaccard_topics`, `shared_papers_incl_hyper` (counts leave out 100+ author papers and self-citations) |
| `citation_origin.csv` | per paper and direction (cited by / citing): links in each origin category (self, own institute, other Indian only, India + abroad, abroad or unknown) |
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
- **Papers with 100+ authors:** OpenAlex truncates author lists at 100. Those papers (almost all CMS) stay in the CSVs, flagged `hyperauthored`, and are left out of every statistic and graph; the dashboard's *Big collaborations* page describes them. Papers with 11–99 authors stay in, flagged `large_team`.
- **Self-citation** = the two papers share an author. 96% of citations between our own papers are self-citations, so the knowledge-flow analysis works on the rest, aggregated to faculty.
- **Citation origin:** every citation link goes into the first matching category: self, same IISER, India + abroad, other Indian only, then a remainder (no Indian author or unknown) from OpenAlex totals.
- **Quartile** = SCImago best quartile for the nearest year not after publication; CORE rank for conference papers.
- See the dashboard's *Methods & data* page for the full list.

## Inputs not in the repo

- **Raw OpenAlex data** (`data/raw/`, ~1 GB) and the API cache are gitignored. `make stage` onwards needs `data/raw/`.
- **SCImago rankings:** download the yearly CSVs from scimagojr.com (blocked for scripts) with type **All types** into `ref/scimago/scimago_<year>.csv`, then run `make build networks export report`. They give the quartile, SJR and the impact-factor proxy. The build keeps journals, conferences & proceedings, and book series, and drops trade journals.
- **Topic profiles** (`data/stage/inst_subfields.parquet`, from `make topics`) need an OpenAlex API key. Without them the topic Jaccard columns stay empty.
- **CORE ranks (optional, ICORE2026 export included):** CORE portal export → `ref/core.csv` (no header row; rank in the 5th column). IISER output is almost all journals, so this changes little.
