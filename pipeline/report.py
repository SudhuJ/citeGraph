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
    data = {
        "kpi": rows(con, """
            SELECT institution, count(*) AS papers, sum(citations)::BIGINT AS citations,
                   coalesce(any_value(h.hyper), 0) AS hyper,
                   count(*) FILTER (quartile = 'Q1') / nullif(count(*) FILTER (quartile LIKE 'Q_'), 0) AS q1_share,
                   count(*) FILTER (quartile = 'Q1' AND if_proxy > 5) / nullif(count(*) FILTER (quartile LIKE 'Q_'), 0) AS q1_if5_share,
                   count(*) FILTER (quartile LIKE 'Q_') / count(*) FILTER (type = 'journal')::DOUBLE AS q_coverage
            FROM p LEFT JOIN h USING (institution) GROUP BY 1 ORDER BY 1 DESC"""),
        "depts": rows(con, f"SELECT * FROM read_csv('{ROOT / 'dashboard/src/data/departments.csv'}') WHERE papers > 0 ORDER BY institution DESC, papers DESC"),
        "origin": rows(con, f"""SELECT institution, direction, category, sum(n)::BIGINT AS n
                                FROM read_csv('{ROOT / 'dashboard/src/data/origin.csv'}') GROUP BY ALL ORDER BY ALL"""),
        "faccit": json.loads((ROOT / "dashboard/src/data/faccit_graph.json").read_text())["summary"],
        "faculty": rows(con, """SELECT institution, count(*) AS n, count(*) FILTER (papers > 0) AS active,
                                       median(h_index) AS med_h, max(h_index) AS max_h, median(h_index_lifetime) AS med_h_life
                                FROM f GROUP BY 1 ORDER BY 1 DESC"""),
        "trend": rows(con, "SELECT institution, year, count(*) AS n FROM p GROUP BY ALL ORDER BY 1, 2"),
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
