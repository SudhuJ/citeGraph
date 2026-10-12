"""Run a .sql file with DuckDB from the repo root (no duckdb CLI needed)."""

import sys
import time
from pathlib import Path

import duckdb
from oa import ROOT

for path in sys.argv[1:]:
    t = time.time()
    con = duckdb.connect(str(ROOT / "data" / "citegraph.duckdb"))
    con.execute(Path(path).read_text())
    print(f"{path}: done in {time.time() - t:.1f}s")
