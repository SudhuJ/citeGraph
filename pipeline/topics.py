"""Research-topic profiles for the Jaccard similarity of §7b.

For our two institutes and every Indian partner that shares at least MIN_SHARED corpus
papers with them, fetch the institution-wide 2016–2026 paper counts per OpenAlex subfield
(one group_by call each). Output: data/stage/inst_subfields.parquet (inst_id, subfield, n).
"""

import duckdb
from oa import ROOT, get, short

OURS = ["I181996519", "I127439422"]
MIN_SHARED = 3


def main() -> None:
    con = duckdb.connect()
    partners = [r[0] for r in con.sql(f"""
        SELECT a.inst_id
        FROM 'data/stage/authorships.parquet' a
        WHERE a.country = 'IN' AND a.inst_id NOT IN ({",".join(f"'{i}'" for i in OURS)})
          AND a.work_id IN (SELECT work_id FROM 'data/stage/author_works.parquet')
        GROUP BY 1 HAVING count(DISTINCT a.work_id) >= {MIN_SHARED}
        ORDER BY count(DISTINCT a.work_id) DESC""").fetchall()]
    print(f"topic profiles for {len(OURS)} + {len(partners)} partner institutions")
    rows = []
    for inst in OURS + partners:
        d = get("/works", {"filter": f"institutions.id:{inst},publication_year:2016-2026",
                           "group_by": "primary_topic.subfield.id", "per-page": 200})
        rows += [(inst, g["key_display_name"], short(g["key"]), g["count"]) for g in d["group_by"]]
    con.execute("CREATE TABLE t (inst_id VARCHAR, subfield VARCHAR, subfield_id VARCHAR, n BIGINT)")
    con.executemany("INSERT INTO t VALUES (?, ?, ?, ?)", rows)
    con.execute(f"COPY t TO '{ROOT / 'data/stage/inst_subfields.parquet'}'")
    print(f"{len(rows)} (institution, subfield) rows")


if __name__ == "__main__":
    main()
