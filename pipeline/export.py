"""Export compact tables for the dashboard (dashboard/src/data/) and the report.

  faculty.csv      one row per faculty: papers, citations, h-index (2016–26 window and
                   OpenAlex lifetime), Q1 share, top journal
  papers.csv       one row per (institution, paper)
  connections.csv  copy of indian_connections.csv
"""

import json
import shutil

import duckdb
from oa import ROOT

OUT = ROOT / "dashboard" / "src" / "data"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / "data" / "citegraph.duckdb"))
    lifetime = {}
    for line in (ROOT / "data/raw/authors.jsonl").open():
        a = json.loads(line)
        lifetime[a["id"].rsplit("/", 1)[-1]] = a["summary_stats"]["h_index"]
    con.execute("CREATE OR REPLACE TABLE lifetime_h (author_id VARCHAR, h INT)")
    con.executemany("INSERT INTO lifetime_h VALUES (?, ?)", list(lifetime.items()))

    con.execute(f"""
    CREATE OR REPLACE TABLE faculty_stats AS
    WITH r AS (
      SELECT fac_id, citations, row_number() OVER (PARTITION BY fac_id ORDER BY citations DESC) AS rk
      FROM data_rows
    ), h AS (SELECT fac_id, coalesce(max(rk) FILTER (citations >= rk), 0) AS h_index FROM r GROUP BY 1),
    tj AS (
      SELECT fac_id, journal_name AS top_journal FROM data_rows WHERE journal_name IS NOT NULL
      GROUP BY fac_id, journal_name QUALIFY row_number() OVER (PARTITION BY fac_id ORDER BY count(*) DESC, journal_name) = 1
    ), agg AS (
      SELECT fac_id, count(*) AS papers, sum(citations) AS citations,
             count(*) FILTER (quartile = 'Q1') / nullif(count(*) FILTER (quartile LIKE 'Q%'), 0) AS q1_share,
             count(*) FILTER (hyperauthored) AS hyper_papers,
             count(*) FILTER (NOT hyperauthored) AS papers_excl_hyper
      FROM data_rows GROUP BY 1
    ), lh AS (
      SELECT p.fac_id, max(l.h) AS h_index_lifetime FROM fac_profiles p JOIN lifetime_h l USING (author_id) GROUP BY 1
    )
    SELECT f.fac_id, f.name, f.institution, f.department, f.designation,
           coalesce(agg.papers, 0) AS papers, coalesce(agg.citations, 0) AS citations,
           coalesce(h.h_index, 0) AS h_index, lh.h_index_lifetime, round(agg.q1_share, 3) AS q1_share,
           tj.top_journal, coalesce(agg.hyper_papers, 0) AS hyper_papers,
           coalesce(agg.papers_excl_hyper, 0) AS papers_excl_hyper,
           f.openalex_ids <> '' AS matched, f.profile_url
    FROM faculty f LEFT JOIN agg USING (fac_id) LEFT JOIN h USING (fac_id)
    LEFT JOIN tj USING (fac_id) LEFT JOIN lh USING (fac_id)
    ORDER BY f.institution, f.name;
    COPY faculty_stats TO '{OUT / "faculty.csv"}';
    COPY faculty_stats TO '{ROOT / "data/out/faculty_stats.csv"}';

    COPY (
      SELECT DISTINCT institution, regexp_extract(openalex_id, '[^/]+$') AS work_id, title, year, type,
             journal_name, doi, citations, quartile, field, subfield, n_authors, hyperauthored,
             cites_indian_inst, cited_by_indian_inst
      FROM data_rows ORDER BY institution, year
    ) TO '{OUT / "papers.csv"}';

    COPY (SELECT * EXCLUDE (partner_id) FROM connections) TO '{OUT / "connections.csv"}';
    """)
    dl = ROOT / "dashboard" / "src" / "downloads"
    dl.mkdir(exist_ok=True)
    for f in ("group19_data", "citation_network", "authorship_network", "indian_connections"):
        shutil.copy(ROOT / "data" / "out" / f"{f}.csv", dl / f"{f}.csv")
    print(con.sql("""SELECT institution, count(*) faculty, median(h_index) med_h, max(h_index) max_h,
                            median(h_index_lifetime) med_h_life FROM faculty_stats GROUP BY 1""").fetchall())


if __name__ == "__main__":
    main()
