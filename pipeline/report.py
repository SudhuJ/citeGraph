"""Statistics report (≤5 pages): collect numbers into report/data.json, compile report/report.typ."""

import json

import duckdb
import typst
from oa import ROOT

REP = ROOT / "report"


def rows(con, q):
    cur = con.execute(q)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def main() -> None:
    con = duckdb.connect(str(ROOT / "data" / "citegraph.duckdb"), read_only=True)
    con.execute("CREATE TEMP TABLE pall AS SELECT DISTINCT institution, openalex_id, title, year, journal_name, doi, citations, quartile, if_proxy, type, field, hyperauthored FROM data_rows")
    # papers with >=100 authors are reported separately and left out of every statistic
    con.execute("CREATE TEMP TABLE p AS SELECT * FROM pall WHERE NOT hyperauthored")
    con.execute("CREATE TEMP TABLE h AS SELECT institution, count(*) AS hyper FROM pall WHERE hyperauthored GROUP BY 1")
    con.execute(f"CREATE TEMP TABLE f AS SELECT * FROM read_csv('{ROOT / 'data/out/faculty_stats.csv'}')")
    net = json.loads((ROOT / "dashboard/src/data/network_metrics.json").read_text())

    def fac_pairs() -> dict:
        """Share of faculty co-author links (G_fac edges) within one institute / one department."""
        g = json.loads((ROOT / "dashboard/src/data/fac_graph.json").read_text())
        nd, ed = g["nodes"], g["edges"]
        inst = sum(nd[s]["inst"] == nd[t]["inst"] for s, t, *_ in ed)
        dept = sum(nd[s]["inst"] == nd[t]["inst"] and nd[s]["dept"] == nd[t]["dept"] for s, t, *_ in ed)
        return {"links": len(ed), "same_inst": inst / len(ed), "same_dept": dept / len(ed)}

    data = {
        "kpi": rows(con, """
            SELECT institution, count(*) AS papers, sum(citations)::BIGINT AS citations,
                   coalesce(any_value(h.hyper), 0) AS hyper,
                   count(*) FILTER (quartile = 'Q1') / nullif(count(*) FILTER (quartile LIKE 'Q_'), 0) AS q1_share,
                   count(*) FILTER (quartile = 'Q1' AND if_proxy > 5) / nullif(count(*) FILTER (quartile LIKE 'Q_'), 0) AS q1_if5_share,
                   count(*) FILTER (quartile LIKE 'Q_') / count(*) FILTER (type = 'journal')::DOUBLE AS q_coverage
            FROM p LEFT JOIN h USING (institution) GROUP BY 1 ORDER BY 1 DESC"""),
        "depts": rows(con, f"SELECT * FROM read_csv('{ROOT / 'dashboard/src/data/departments.csv'}') WHERE papers > 0 ORDER BY institution DESC, papers DESC"),
        "origin": rows(con, f"""SELECT institution, direction, category, from_ours, sum(n)::BIGINT AS n
                                FROM read_csv('{ROOT / 'dashboard/src/data/origin.csv'}') GROUP BY ALL ORDER BY ALL"""),
        "faccit": json.loads((ROOT / "dashboard/src/data/faccit_graph.json").read_text())["summary"],
        "facpairs": fac_pairs(),
        "faculty": rows(con, """SELECT institution, count(*) AS n, count(*) FILTER (papers > 0) AS active,
                                       median(h_index) AS med_h, max(h_index) AS max_h, median(h_index_lifetime) AS med_h_life
                                FROM f GROUP BY 1 ORDER BY 1 DESC"""),
         "coverage": rows(con, """SELECT count(*) AS faculty, count(*) FILTER (matched) AS matched,
                            count(*) FILTER (papers > 0) AS publishing
                        FROM f"""),
                "trend": rows(con, """WITH faculty_first AS (
                                                                    SELECT institution, fac_id, min(year) AS first_year FROM data_rows
                                                                    WHERE NOT hyperauthored GROUP BY 1, 2
                                                                ), yearly AS (
                                                                    SELECT institution, year, count(*) AS n FROM p GROUP BY ALL
                                                                ), active AS (
                                                                    SELECT y.institution, y.year, y.n,
                                                                                 count(f.fac_id) FILTER (f.first_year <= y.year) AS active
                                                                    FROM yearly y LEFT JOIN faculty_first f USING (institution)
                                                                    GROUP BY y.institution, y.year, y.n
                                                                )
                                                                SELECT *, n::DOUBLE / nullif(active, 0) AS per_faculty
                                                                FROM active ORDER BY 1, 2"""),
        "quartiles": rows(con, """SELECT institution, coalesce(quartile, 'unranked') AS q, count(*) AS n FROM p
                                  WHERE type = 'journal' GROUP BY ALL ORDER BY 1, 2"""),
        "hist": rows(con, """SELECT institution, least(h_index, 40) // 4 * 4 AS bin, count(*) AS n FROM f
                             GROUP BY ALL ORDER BY 1, 2"""),
        "journals": rows(con, """SELECT institution, journal_name, count(*) AS n FROM p WHERE journal_name IS NOT NULL
                                 GROUP BY institution, journal_name QUALIFY row_number() OVER (PARTITION BY institution ORDER BY count(*) DESC) <= 5
                                 ORDER BY 1 DESC, 3 DESC"""),
        "top_cited": rows(con, """SELECT any_value(title) AS title, any_value(journal_name) AS journal, any_value(year) AS year,
                                         max(citations) AS citations, string_agg(DISTINCT institution, ' & ') AS inst, any_value(doi) AS doi
                                  FROM p GROUP BY openalex_id ORDER BY citations DESC LIMIT 10"""),
                "top_cited_age": rows(con, """WITH distinct_papers AS (
                                                                                         SELECT openalex_id, any_value(year) AS year, max(citations) AS citations
                                                                                         FROM p GROUP BY 1
                                                                                     ), top30 AS (
                                                                                         SELECT * FROM distinct_papers ORDER BY citations DESC LIMIT 30
                                                                                     )
                                                                                     SELECT count(*) FILTER (year <= 2019)::DOUBLE / count(*) AS share_2016_2019,
                                                                                                    count(*) AS n FROM top30"""),
        "top_cited_hyper": rows(con, "SELECT max(citations) AS c FROM pall WHERE hyperauthored"),
        "fields": rows(con, """SELECT institution, coalesce(field, 'Unclassified') AS field, count(*) AS n,
                                      count(*) / sum(count(*)) OVER (PARTITION BY institution) AS share
                               FROM p GROUP BY institution, field QUALIFY row_number() OVER (PARTITION BY institution ORDER BY count(*) DESC) <= 8
                               ORDER BY 1 DESC, 3 DESC"""),
        "top_deg": sorted(net["faculty_comparison"], key=lambda r: -r["deg_fac"])[:8],
        "top_btw": sorted(net["faculty_comparison"], key=lambda r: -r["btw_ind"])[:8],
        "partners": rows(con, """SELECT your_inst, partner_inst, partner_cluster, shared_papers, cites_in, cites_out, jaccard_topics
                                 FROM connections QUALIFY row_number() OVER (PARTITION BY your_inst ORDER BY shared_papers DESC) <= 6
                                 ORDER BY 1 DESC, 4 DESC"""),
                "topic_collaboration": rows(con, """WITH partner_values AS (
                                                                                                SELECT jaccard_topics, shared_papers FROM connections
                                                                                                WHERE jaccard_topics IS NOT NULL AND shared_papers >= 3
                                                                                            ), partner_ranks AS (
                                                                                                SELECT rank() OVER (ORDER BY jaccard_topics)
                                                                                                                 + (count(*) OVER (PARTITION BY jaccard_topics) - 1) / 2.0 AS topic_rank,
                                                                                                             rank() OVER (ORDER BY shared_papers)
                                                                                                                 + (count(*) OVER (PARTITION BY shared_papers) - 1) / 2.0 AS paper_rank
                                                                                                FROM partner_values
                                                                                            )
                                SELECT count(*) AS n, corr(topic_rank, paper_rank) AS spearman
                                FROM partner_ranks"""),
         "partner_summary": rows(con, """SELECT sum(shared_papers) FILTER (cross_cluster)::DOUBLE
                                / nullif(sum(shared_papers), 0) AS cross_cluster_share
                            FROM connections WHERE shared_papers > 0"""),
        "net": {k: net[k] for k in ("citation", "coauthorship", "spearman_fac_vs_ind", "hyperauthorship", "snapshots")},
    }
    for k in ("degree_ccdf",):
        for g in data["net"]["coauthorship"].values():
            g.pop(k, None)
    data["net"]["citation"].pop("top_citing_papers", None)
    REP.mkdir(exist_ok=True)
    (REP / "data.json").write_text(json.dumps(data, default=str))
    typst.compile(str(REP / "report.typ"), output=str(REP / "report.pdf"), root=str(ROOT))
    print(f"-> {(REP / 'report.pdf').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
