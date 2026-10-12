"""Match the scraped faculty roster to OpenAlex author IDs.

Candidate pool = every OpenAlex author ever affiliated with the institute (cheap filter
queries). Names are matched token-by-token (full tokens fuzzily, initials against first
letters) over all of a candidate's name variants. OpenAlex often splits one person
across several author profiles, so *all* compatible candidates active at the institute
in 2016–2026 are kept and merged under one faculty ID.

Outputs
  data/faculty.csv         one row per faculty: fac_id, …, openalex_ids (';'), h_index_lifetime
  data/faculty_review.csv  rows needing a manual look (no match / many profiles / weak match)
Manual fixes go in ref/author_overrides.csv (fac_name, institution, add_ids, remove_ids).
"""

import csv
import re
import unicodedata
from difflib import SequenceMatcher

from oa import ROOT, paginate, short

INSTITUTES = {"IISER Pune": "I181996519", "IISER Kolkata": "I127439422"}
TITLES = {"dr", "prof", "professor", "mr", "ms", "mrs", "sri", "smt"}
YEARS = range(2016, 2027)


def tokens(name: str) -> list[str]:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.,\-'’()]", " ", s)
    return [t for t in s.split() if t not in TITLES]


def tok_eq(a: str, b: str) -> bool:
    if len(a) == 1 or len(b) == 1:
        return a[0] == b[0]
    return a == b or (min(len(a), len(b)) >= 5 and SequenceMatcher(None, a, b).ratio() >= 0.86)


def name_score(fac: list[str], cand: list[str]) -> float:
    """0 = incompatible, else the share of tokens matched in full.

    One full faculty token acts as the surname and must match a full candidate token
    (the last token is tried first; Indian names often put the family name or initials
    anywhere). The rest are given names: the first must be represented (full or initial);
    candidate tokens must be explained by faculty given names, except stray initials and
    at most one extra spelled-out middle name."""
    if not fac or not cand:
        return 0.0
    best = 0.0
    for sur in [t for t in reversed(fac) if len(t) > 1]:
        idx = next((i for i, c in enumerate(cand) if len(c) > 1 and tok_eq(sur, c)), None)
        if idx is None:
            continue
        given_f = list(fac)
        given_f.remove(sur)
        given_c = cand[:idx] + cand[idx + 1:]
        if not given_c or not given_f:
            continue
        used, full, extra_full = set(), 1, 0
        for c in given_c:
            j = next((j for j, f in enumerate(given_f) if j not in used and tok_eq(c, f)), None)
            if j is None:
                extra_full += len(c) > 1
                continue
            used.add(j)
            full += len(c) > 1 and len(given_f[j]) > 1
        if 0 not in used or extra_full > (1 if len(given_f[0]) > 1 and full > 1 else 0):
            continue
        best = max(best, (full - 0.5 * extra_full) / max(len(fac), len(cand)))
    return best


def pool(inst_id: str) -> list[dict]:
    sel = "id,display_name,display_name_alternatives,works_count,cited_by_count,summary_stats,affiliations,orcid"
    return list(paginate("/authors", {"filter": f"affiliations.institution.id:{inst_id}", "select": sel}))


def active_years(author: dict, inst_id: str) -> set[int]:
    for a in author.get("affiliations") or []:
        if short(a["institution"]["id"]) == inst_id:
            return set(a["years"])
    return set()


def load_overrides() -> dict:
    f = ROOT / "ref" / "author_overrides.csv"
    if not f.exists():
        return {}
    with f.open() as fh:
        return {(r["fac_name"], r["institution"]): r for r in csv.DictReader(fh)}


def main() -> None:
    with (ROOT / "data" / "faculty_seed.csv").open() as f:
        roster = list(csv.DictReader(f))
    overrides = load_overrides()
    out, review = [], []
    for inst, inst_id in INSTITUTES.items():
        cands = pool(inst_id)
        print(f"{inst}: {len(cands)} candidate authors")
        for c in cands:
            # display name always counts; variants only when spelled out in full (initial-only
            # variants such as "S K Ghosh" are ambiguous and come from noisy raw strings)
            alts = [tokens(n) for n in c.get("display_name_alternatives") or []]
            c["_primary"] = tuple(tokens(c["display_name"]))
            c["_names"] = {c["_primary"]} | {tuple(t) for t in alts if t and all(len(x) > 1 for x in t)}
            c["_years"] = active_years(c, inst_id)
        for i, fac in enumerate(r for r in roster if r["institution"] == inst):
            ft = tokens(fac["name"])
            scored = []
            for c in cands:
                # the profile's own display name must be compatible (guards against mis-merged
                # profiles whose variants include someone else's name)
                if not name_score(ft, list(c["_primary"])):
                    continue
                s = max(name_score(ft, list(n)) for n in c["_names"])
                if c["_years"] & set(YEARS):
                    scored.append((s, c))
            # keep candidates within reach of the best name score
            best = max((s for s, _ in scored), default=0)
            keep = sorted([c for s, c in scored if s >= best - 0.2], key=lambda c: -c["works_count"])
            # namesakes: a profile carrying a different ORCID than the main one is someone else
            main_orcid = next((c["orcid"] for c in keep if c.get("orcid")), None)
            keep = [c for c in keep if not c.get("orcid") or c["orcid"] == main_orcid]

            ov = overrides.get((fac["name"], inst))
            ids = [short(c["id"]) for c in keep]
            if ov:
                ids = [x for x in ids if x not in ov["remove_ids"].split(";")]
                ids += [x for x in ov["add_ids"].split(";") if x and x not in ids]
            kept = [c for c in keep if short(c["id"]) in ids]
            fac_id = f"{'PUN' if inst == 'IISER Pune' else 'KOL'}{i + 1:03d}"
            row = dict(fac, fac_id=fac_id, openalex_ids=";".join(ids),
                       oa_names=" | ".join(c["display_name"] for c in kept),
                       oa_works=";".join(str(c["works_count"]) for c in kept),
                       h_index_lifetime=max((c["summary_stats"]["h_index"] for c in kept), default=""),
                       orcid=next((c["orcid"] for c in kept if c.get("orcid")), "") or "",
                       match_score=round(best, 2))
            out.append(row)
            reason = ("no match" if not ids else
                      "weak name match" if best < 0.5 else
                      "many profiles" if len(ids) > 3 else "")
            if reason and not ov:
                review.append(dict(row, reason=reason))

    cols = ["fac_id", "institution", "name", "designation", "department", "joint_departments",
            "openalex_ids", "oa_names", "oa_works", "h_index_lifetime", "orcid", "match_score", "profile_url"]
    with (ROOT / "data" / "faculty.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    with (ROOT / "data" / "faculty_review.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["reason", *cols], extrasaction="ignore")
        w.writeheader()
        w.writerows(review)
    matched = sum(bool(r["openalex_ids"]) for r in out)
    print(f"matched {matched}/{len(out)} faculty; {len(review)} rows flagged in data/faculty_review.csv")


if __name__ == "__main__":
    main()
