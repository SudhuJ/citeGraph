# citeGraph — DPCN 2026 Group 19 pipeline. Every OpenAlex response is cached in data/cache,
# so re-running any step costs no API credits. Needs OPENALEX_API_KEY in .env for fresh fetches.
PY := uv run
.PHONY: setup roster match fetch stage institutions topics build networks export report data check dash site clean

setup:                       ## install Python + dashboard dependencies
	uv sync
	npm --prefix dashboard install
	npm --prefix dashboard run vendor

roster:                      ## scrape regular-faculty rosters -> data/faculty_seed.csv
	$(PY) pipeline/faculty.py
match:                       ## roster -> OpenAlex author IDs (+ ref/author_overrides.csv)
	$(PY) pipeline/match_authors.py
fetch:                       ## works + Indian citation links -> data/raw/*.jsonl
	$(PY) pipeline/fetch.py
stage:                       ## raw JSONL -> data/stage/*.parquet
	$(PY) pipeline/runsql.py pipeline/stage.sql
institutions:                ## classify Indian institutions -> ref/institutions.csv
	$(PY) pipeline/institutions.py
topics:                      ## subfield profiles for topic Jaccard
	$(PY) pipeline/topics.py
build:                       ## the four deliverable CSVs -> data/out/
	$(PY) pipeline/build.py
networks:                    ## igraph metrics + layouts -> dashboard/src/data/
	$(PY) pipeline/networks.py
export:                      ## dashboard tables + downloads
	$(PY) pipeline/export.py
report:                      ## statistics report -> report/report.pdf
	$(PY) pipeline/report.py
check:                       ## validate deliverables against the instruction note
	$(PY) pipeline/check.py

data: fetch stage institutions topics build networks export check   ## full pipeline after `match`

dash:                        ## live dashboard at http://localhost:3000
	npm --prefix dashboard run dev
site:                        ## static dashboard -> dashboard/dist/
	npm --prefix dashboard run build

clean:                       ## remove derived files (keeps the API cache and raw data)
	rm -rf data/stage data/out data/citegraph.duckdb dashboard/dist report/report.pdf report/data.json
