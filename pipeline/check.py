"""Validate the Week-2 deliverables against the instruction note (§5, §7c, checklist §11)."""

import sys

import duckdb
from oa import ROOT

OUT = ROOT / "data" / "out"
REQUIRED = {
    "group19_data.csv": ["group", "institution", "author", "title", "year", "type", "journal_name", "issn", "doi",
                         "citations", "quartile", "coauthor_institutes", "cites_indian_inst", "cited_by_indian_inst"],
    "citation_network.csv": ["source_doi", "target_doi", "source_inst", "target_inst", "year"],
    "authorship_network.csv": ["author_a", "author_b", "paper_doi", "inst_a", "inst_b", "year"],
    "indian_connections.csv": ["your_inst", "partner_inst", "shared_papers", "total_citations"],
}


def src(path) -> str:
    """CSV reader with explicit RFC-4180 quoting (the sniffer can miss quotes that appear late)."""
    return f"read_csv('{path}', quote='\"', escape='\"', sample_size=-1)"


def main() -> int:
    con = duckdb.connect()
    failures = []

    def check(ok: bool, msg: str):
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            failures.append(msg)

    for name, cols in REQUIRED.items():
        f = OUT / name
        check(f.exists(), f"{name} exists")
        if not f.exists():
            continue
        have = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {src(f)}").fetchall()]
        missing = [c for c in cols if c not in have]
        check(not missing, f"{name}: required columns present{'' if not missing else ' — missing ' + ', '.join(missing)}")
        n = con.execute(f"SELECT count(*) FROM {src(f)}").fetchone()[0]
        check(n > 0, f"{name}: {n:,} rows")

    d = src(OUT / "group19_data.csv")
    yr = con.execute(f"SELECT min(year), max(year) FROM {d}").fetchone()
    check(yr[0] >= 2016 and yr[1] <= 2026, f"years within 2016–2026 (found {yr[0]}–{yr[1]})")
    insts = {r[0] for r in con.execute(f"SELECT DISTINCT institution FROM {d}").fetchall()}
    check(insts == {"IISER Pune", "IISER Kolkata"}, f"both assigned institutions present: {sorted(insts)}")
    check(con.execute(f"SELECT bool_and(\"group\" = 19) FROM {d}").fetchone()[0], "group column = 19")
    types = {r[0] for r in con.execute(f"SELECT DISTINCT type FROM {d}").fetchall()}
    check(types <= {"journal", "conference"}, f"type ∈ {{journal, conference}}: {sorted(types)}")
    bools = con.execute(f"SELECT typeof(any_value(cites_indian_inst)), typeof(any_value(cited_by_indian_inst)) FROM {d}").fetchone()
    check(all(b == "BOOLEAN" for b in bools), "Indian flag columns are TRUE/FALSE")
    dup = con.execute(f"SELECT count(*) - count(DISTINCT (fac_id, openalex_id)) FROM {d}").fetchone()[0]
    check(dup == 0, f"no duplicate faculty × paper rows ({dup})")
    q = con.execute(f"SELECT count(*) FILTER (quartile IS NOT NULL) / count(*) FILTER (type = 'journal')::DOUBLE FROM {d}").fetchone()[0]
    print(f"  info quartile coverage of journal rows: {q:.0%}" + ("  (add SCImago CSVs to ref/scimago/)" if q == 0 else ""))
    print("all checks passed" if not failures else f"{len(failures)} check(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
