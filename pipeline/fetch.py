"""Fetch everything the build step needs from OpenAlex into data/raw/*.jsonl.

  authors.jsonl  matched faculty profiles (lifetime h-index etc.)
  works.jsonl    all works 2016–2026 of the matched faculty profiles
  citing.jsonl   Indian-authored works that cite a corpus work      (in-flow)
  cited.jsonl    Indian-authored works that a corpus work cites     (out-flow)

Batches of 100 IDs per OR-filter; every page is cached, so re-runs are free.
"""

import csv
import json
import sys

from oa import ROOT, chunks, get, paginate, short

RAW = ROOT / "data" / "raw"
WORK_FIELDS = ("id,doi,display_name,publication_year,type,primary_location,authorships,"
               "cited_by_count,referenced_works,primary_topic,topics")
LINK_FIELDS = "id,doi,display_name,publication_year,authorships,referenced_works,primary_topic"


def write(name: str, rows: dict) -> None:
    with (RAW / name).open("w") as f:
        for r in rows.values():
            f.write(json.dumps(r) + "\n")
    print(f"  {name}: {len(rows)} records")


def collect(filter_tpl: str, ids: list[str], select: str, label: str) -> dict:
    out: dict = {}
    batches = list(chunks(ids, 100))
    for i, b in enumerate(batches, 1):
        for w in paginate("/works", {"filter": filter_tpl.format("|".join(b)), "select": select}):
            out[short(w["id"])] = w
        print(f"\r  {label}: batch {i}/{len(batches)}, {len(out)} records", end="", file=sys.stderr)
    print(file=sys.stderr)
    return out


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with (ROOT / "data" / "faculty.csv").open() as f:
        author_ids = sorted({a for r in csv.DictReader(f) for a in r["openalex_ids"].split(";") if a})
    print(f"{len(author_ids)} OpenAlex author profiles")

    authors = {}
    for b in chunks(author_ids, 100):
        for a in get("/authors", {"filter": f"openalex_id:{'|'.join(b)}", "per-page": 100,
                                  "select": "id,display_name,orcid,works_count,cited_by_count,summary_stats"})["results"]:
            authors[short(a["id"])] = a
    write("authors.jsonl", authors)

    works = collect("author.id:{},publication_year:2016-2026", author_ids, WORK_FIELDS, "works")
    write("works.jsonl", works)

    # list responses truncate authorships at 100, so big-collaboration papers may not show
    # our faculty in `authorships`; keep an authoritative profile -> works map instead
    with (RAW / "author_works.jsonl").open("w") as f:
        for i, a in enumerate(author_ids, 1):
            ids = [short(w["id"]) for w in paginate(
                "/works", {"filter": f"author.id:{a},publication_year:2016-2026", "select": "id"})]
            f.write(json.dumps({"author_id": a, "work_ids": ids}) + "\n")
            print(f"\r  author_works: {i}/{len(author_ids)}", end="", file=sys.stderr)
    print(file=sys.stderr)

    # only works that will survive the build filter (journal/conference, not preprints) need links
    keep = sorted(k for k, w in works.items()
                  if ((w.get("primary_location") or {}).get("source") or {}).get("type") in ("journal", "conference"))
    print(f"{len(keep)} journal/conference works -> fetching Indian citation links")
    write("citing.jsonl", collect("cites:{},institutions.country_code:IN", keep, LINK_FIELDS, "citing"))
    write("cited.jsonl", collect("cited_by:{},institutions.country_code:IN", keep, LINK_FIELDS, "cited"))


if __name__ == "__main__":
    main()
