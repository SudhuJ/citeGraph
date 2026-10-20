"""Export compact tables for the dashboard (dashboard/src/data/) and the report.

  faculty.csv      one row per faculty: papers, citations, h-index (2016–26 window and
                   OpenAlex lifetime), Q1 share, top journal. Everything except the
                   hyper_* columns leaves out papers with >=100 authors.
  departments.csv  one row per (institute, department), same rule
  papers.csv       one row per (institution, paper)
  origin.csv       citation origin by institute, direction, category, from_ours, publication year
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
    WITH main AS (SELECT * FROM data_rows WHERE NOT hyperauthored),
    r AS (
      SELECT fac_id, citations, row_number() OVER (PARTITION BY fac_id ORDER BY citations DESC) AS rk
      FROM main
    ), h AS (SELECT fac_id, coalesce(max(rk) FILTER (citations >= rk), 0) AS h_index FROM r GROUP BY 1),
    tj AS (
      SELECT fac_id, journal_name AS top_journal FROM main WHERE journal_name IS NOT NULL
      GROUP BY fac_id, journal_name QUALIFY row_number() OVER (PARTITION BY fac_id ORDER BY count(*) DESC, journal_name) = 1
    ), agg AS (
      SELECT fac_id, count(*) FILTER (NOT hyperauthored) AS papers,
             sum(citations) FILTER (NOT hyperauthored) AS citations,
             count(*) FILTER (NOT hyperauthored AND quartile = 'Q1')
               / nullif(count(*) FILTER (NOT hyperauthored AND quartile LIKE 'Q%'), 0) AS q1_share,
             count(*) FILTER (NOT hyperauthored AND quartile = 'Q1' AND if_proxy > 5)
               / nullif(count(*) FILTER (NOT hyperauthored AND quartile LIKE 'Q%'), 0) AS q1_if5_share,
             count(*) FILTER (NOT hyperauthored AND large_team) AS large_team_papers,
             min(year) FILTER (NOT hyperauthored) AS first_year,
             count(*) FILTER (hyperauthored) AS hyper_papers,
             sum(citations) FILTER (hyperauthored) AS hyper_citations
      FROM data_rows GROUP BY 1
    ), lh AS (
      SELECT p.fac_id, max(l.h) AS h_index_lifetime FROM fac_profiles p JOIN lifetime_h l USING (author_id) GROUP BY 1
    )
    SELECT f.fac_id, f.name, f.institution, f.department, f.designation,
           coalesce(agg.papers, 0) AS papers, coalesce(agg.citations, 0) AS citations,
           coalesce(h.h_index, 0) AS h_index, lh.h_index_lifetime, round(agg.q1_share, 3) AS q1_share,
           round(agg.q1_if5_share, 3) AS q1_if5_share, tj.top_journal,
           coalesce(agg.large_team_papers, 0) AS large_team_papers, agg.first_year,
           coalesce(agg.hyper_papers, 0) AS hyper_papers, coalesce(agg.hyper_citations, 0) AS hyper_citations,
           coalesce(f.openalex_ids, '') <> '' AS matched, f.profile_url
    FROM faculty f LEFT JOIN agg USING (fac_id) LEFT JOIN h USING (fac_id)
    LEFT JOIN tj USING (fac_id) LEFT JOIN lh USING (fac_id)
    ORDER BY f.institution, f.name;
    COPY faculty_stats TO '{OUT / "faculty.csv"}';
    COPY faculty_stats TO '{ROOT / "data/out/faculty_stats.csv"}';

    COPY (
      SELECT DISTINCT institution, regexp_extract(openalex_id, '[^/]+$') AS work_id, title, year, type,
             journal_name, doi, citations, quartile, sjr, if_proxy, field, subfield, n_authors,
             large_team, hyperauthored, coauthor_institutes, cites_indian_inst, cited_by_indian_inst
      FROM data_rows ORDER BY institution, year
    ) TO '{OUT / "papers.csv"}';

    -- departments: a paper counts once per department it has an author in
    COPY (
      WITH p AS (
        SELECT DISTINCT institution, department, openalex_id, citations, type, quartile, if_proxy, large_team
        FROM data_rows WHERE NOT hyperauthored
      ), pa AS (
        SELECT institution, department, count(*) AS papers, sum(citations) AS citations,
               count(*) FILTER (type = 'journal') AS journal_papers,
               -- shares of journal papers whose venue SCImago ranks (same rule as faculty.csv)
               count(*) FILTER (type = 'journal' AND quartile = 'Q1')
                 / nullif(count(*) FILTER (type = 'journal' AND quartile LIKE 'Q%'), 0) AS q1_share,
               count(*) FILTER (type = 'journal' AND quartile = 'Q1' AND if_proxy > 5)
                 / nullif(count(*) FILTER (type = 'journal' AND quartile LIKE 'Q%'), 0) AS q1_if5_share,
               count(*) FILTER (large_team) / count(*) AS large_team_share
        FROM p GROUP BY ALL
      ), fa AS (
        SELECT institution, department, count(*) AS faculty, count(*) FILTER (papers > 0) AS faculty_with_papers,
               median(h_index) AS median_h
        FROM faculty_stats GROUP BY ALL
      )
      SELECT fa.*, coalesce(pa.papers, 0) AS papers, coalesce(pa.citations, 0) AS citations,
             coalesce(pa.journal_papers, 0) AS journal_papers, round(pa.q1_share, 3) AS q1_share,
             round(pa.q1_if5_share, 3) AS q1_if5_share, round(pa.large_team_share, 3) AS large_team_share
      FROM fa LEFT JOIN pa USING (institution, department) ORDER BY institution, papers DESC
    ) TO '{OUT / "departments.csv"}';

    COPY (
      SELECT institution, direction, category, from_ours, year, sum(n)::BIGINT AS n, round(sum(india_frac), 2) AS india_frac
      FROM citation_origin GROUP BY ALL ORDER BY ALL
    ) TO '{OUT / "origin.csv"}';

    COPY (SELECT * EXCLUDE (partner_id) FROM connections) TO '{OUT / "connections.csv"}';
    """)
    dl = ROOT / "dashboard" / "src" / "downloads"
    dl.mkdir(exist_ok=True)
    for f in ("group19_data", "citation_network", "authorship_network", "indian_connections", "citation_origin"):
        shutil.copy(ROOT / "data" / "out" / f"{f}.csv", dl / f"{f}.csv")
    print(con.sql("""SELECT institution, count(*) faculty, median(h_index) med_h, max(h_index) max_h,
                            median(h_index_lifetime) med_h_life FROM faculty_stats GROUP BY 1""").fetchall())


if __name__ == "__main__":
    main()
