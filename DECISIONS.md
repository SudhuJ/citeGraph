# DECISIONS — Group 19 (IISER Pune & IISER Kolkata, 2016–2026)

How we went from the institute websites to the four deliverable CSVs, and the choices we made on the way.
The code for each step is in `pipeline/`. `make data` runs the whole thing, and every OpenAlex response is
cached so the run can be repeated exactly. Sources are listed in `SOURCES.md`.

---

## 1. Data processing pipeline

```
 Institute websites ──► faculty.py ──► data/faculty_seed.csv          (276 regular faculty)
                                            │
 OpenAlex /authors ──► match_authors.py ───►  data/faculty.csv         (roster ↔ OpenAlex author IDs)
                         + ref/author_overrides.csv (manual fixes)     data/faculty_review.csv (flagged)
                                            │
 OpenAlex /works ────► fetch.py ───────────► data/raw/*.jsonl          (papers, Indian citing/cited works)
                                            │
                       stage.sql (DuckDB) ─► data/stage/*.parquet      (flattened: works, authorships, refs, links)
                                            │
 OpenAlex /institutions ► institutions.py ─► ref/institutions.csv      (Indian institutes → course clusters)
                       topics.py ──────────► subfield profiles         (topic Jaccard)
                                            │
 SCImago + CORE ─────► build.py (DuckDB) ──► data/out/group19_data.csv
                                             data/out/citation_network.csv
                                             data/out/authorship_network.csv
                                             data/out/indian_connections.csv
                                            │
                       check.py ───────────► checks every required column, the year range, the type values and duplicates
                       networks.py / export.py / report.py ► dashboard + report
```

### Step by step

1. **Roster (`faculty.py`).** We scraped the regular-faculty pages of both institutes: 146 at IISER Pune and 130
   at IISER Kolkata. Visiting, adjunct, emeritus and honorary faculty are not on these pages, so they are not in
   the data. A person listed under more than one department on the Kolkata site appears once, with the extra
   departments recorded as joint.
2. **Author matching (`match_authors.py`).** Each roster name was matched to one or more OpenAlex author profiles
   (Section 2). 270 of the 276 faculty were matched.
3. **Fetching (`fetch.py`).** For the matched profiles we downloaded all works from 2016–2026 (author IDs sent in
   batches of 100). We also downloaded a separate list of works for each profile, because OpenAlex cuts author
   lists off at 100 names, so on big-collaboration papers our faculty can be missing from the author list. For
   every journal or conference paper, we then fetched the papers with an Indian affiliation that cite it
   (`cites:` filter) and that it cites (`cited_by:` filter). This gives the Indian in-flow and out-flow without
   downloading about 400k reference records.
4. **Staging (`stage.sql`).** The JSON was flattened into Parquet tables: works, one row per
   (work, author, institution), references, and the citing/cited link works with their institutions.
5. **Institutions (`institutions.py`).** We fetched the OpenAlex record (with its parent organisations) for each of
   the 2,121 Indian institutions in the data, and sorted them into the course clusters (IIT, IIIT, NIT, Central
   University, IISc · TIFR · IISER, Premier Science, CSIR, DAE) using the course slides. Anything else became
   University/College, Other research institute, Healthcare or Industry.
6. **Filtering and deduplication (`build.py`):**
   - **Kept:** articles, reviews, letters and conference papers published in journals, conferences or book series.
     **Dropped:** preprints, datasets, errata, peer reviews, and meeting-abstract venues that OpenAlex lists as
     journals (APS/AGU/EGU/JpGU/Goldschmidt abstracts, ChemInform).
   - **Affiliation at the time:** a paper counts for a faculty member only if that paper lists them with their IISER
     affiliation (Section 2.3).
   - **Duplicate records** of the same paper (same DOI, or same title and year after normalising the title) are
     merged into the most-cited record. Each row of `group19_data.csv` is one faculty member × one paper.
7. **Enrichment (`build.py`):**
   - SCImago quartile, SJR and `if_proxy`, matched by ISSN and the SCImago year closest to the publication year
     without going past it.
   - CORE rank for conference papers.
   - Indian co-author institutes and the `cites_indian_inst` / `cited_by_indian_inst` flags. These count only Indian
     institutions *other than the row's own institute*, so IISER Pune ↔ IISER Kolkata counts as cross-institute.
8. **Outputs (`build.py`):**
   - `group19_data.csv`: 8,574 faculty × paper rows (7,538 distinct papers), with all required columns plus extras
     (`fac_id`, `department`, `openalex_id`, `n_authors`, `hyperauthored`, `large_team`, `affiliation_check`, `sjr`, `if_proxy`).
   - `citation_network.csv`: 91,974 directed paper → paper edges. `edge_kind` says whether both papers are ours
     (internal), an Indian paper cites ours (in), or ours cites an Indian paper (out). Each edge has a `self_citation` flag.
   - `authorship_network.csv`: 21,900 undirected co-author pairs. The nodes are our faculty plus their co-authors at
     other Indian institutions.
   - `indian_connections.csv`: 2,883 rows, one per (our institute, Indian partner institute), with `shared_papers`,
     `total_citations` (= `cites_in` + `cites_out`) and topic Jaccard.
9. **Validation (`check.py`).** Checks that every column the instruction note requires is present, the years are 2016–2026,
   both institutes appear, `type` is only journal or conference, the flag columns are booleans, and no
   faculty × paper row is repeated.

### Other choices

- **Papers with 100+ authors** (1,121 papers, almost all from the CMS collaboration): OpenAlex lists at most 100
  authors, so we cannot see who all the co-authors are. These papers stay in `group19_data.csv` with
  `hyperauthored = true`, but are left out of the networks and all statistics. Papers with 11–99 authors stay in
  and are flagged `large_team`.
- **Self-citation** means the citing and cited papers share at least one author. All OpenAlex profiles of one faculty
  member count as the same person. Self-citations are left out of the citation counts in `indian_connections.csv`.
- **Quartile** is SCImago's best quartile. Conference papers use the CORE rank when one exists. The Clarivate Impact
  Factor is not open data, so `if_proxy` uses SCImago's 2-year citations per document instead.

---

## 2. How we verified the authors on each paper

Three checks run one after another. A faculty member is attached to a paper only if the paper passes all three.

### 2.1 Roster → OpenAlex profile (are these the right people?)

- **Candidate pool:** we did not search OpenAlex for names across the whole world. Instead we took every OpenAlex author
  profile that has *ever* been affiliated with the institute (`affiliations.institution.id` = IISER Pune or IISER
  Kolkata), and only kept profiles that were active there in 2016–2026.
- **Name matching, token by token.** Names are normalised first: accents removed, lower case, punctuation removed,
  titles such as Dr/Prof dropped. Then:
  - one full token is treated as the surname and must match a full token in the candidate's name. We try every token,
    because Indian names put the family name or initials in different places;
  - the first given name must appear in the candidate's name, either in full or as its initial;
  - full tokens may differ slightly (similarity ≥ 0.86 when both are at least 5 letters), so spelling variants still match;
  - the candidate's name may have at most one extra spelled-out given name.
- **Profile's own name must fit.** OpenAlex keeps a list of alternative names for each profile. A profile matched only
  through one of those alternatives, while its main display name belongs to someone else, is rejected. This guards
  against profiles that OpenAlex has wrongly merged.
- **ORCID check.** If one of the kept profiles has an ORCID and another kept profile has a *different* ORCID, the
  second one belongs to someone else and is dropped. 251 of the 270 matched faculty have an ORCID.
- **Flagged for review.** 18 faculty were written to `data/faculty_review.csv` for a manual look: 6 with no match,
  8 with a weak name match (mostly people listed by initials, e.g. "T. S. Mahesh"), and 4 with many profiles. Manual
  fixes are kept in `ref/author_overrides.csv`, for example:
  - *R. Boomi Shankar*: OpenAlex spells the name "Boomishankar", so the automatic match picked namesakes. We swapped
    in the correct profiles by hand.
  - *Bheemalingam Chittari*: OpenAlex splits the name as "Bheema Lingam". We added that profile by hand.

### 2.2 Profile → papers

All 2016–2026 works of every accepted profile are fetched. Which works belong to which profile comes from OpenAlex's
list of works per author, not from the author list printed on each work, which is cut off at 100 names.

### 2.3 Paper → affiliation check (was the person at the IISER when the paper was written?)

For each faculty × paper pair we look up that author's institutions **on that paper**. The result is in the
`affiliation_check` column:

| Value | Meaning | Rows | Decision |
|---|---|---|---|
| `affiliated` | IISER Pune/Kolkata listed for this author on the paper | 6,567 | kept |
| `not listed (truncated)` | the author is beyond the first 100 names on the paper | 1,567 | kept, flagged |
| `no affiliation parsed` | OpenAlex has no institution for this author on the paper | 440 | kept, flagged |
| `elsewhere` | the author's institutions on the paper are all non-IISER (e.g. before they joined) | — | **dropped** |

This step removes papers written before the person joined the IISER, and also papers that OpenAlex wrongly
assigned to a namesake at another institute.

---

## 3. How we handled authors with identical names

We identify people by **ID, never by name**. Every join in the pipeline uses an OpenAlex author ID (`A…`) or our
own faculty ID (`PUN###` / `KOL###`). The display names in the CSVs are labels only.

1. **Namesakes in OpenAlex.** Common names such as Sachin Jain, Surjeet Singh, Ayan Banerjee and Dwaipayan Roy each
   have many OpenAlex profiles. These are separated by:
   - the **institution filter**: only profiles that were affiliated with the IISER in 2016–2026 are considered;
   - the **ORCID check**: a profile with a different ORCID is someone else;
   - the **per-paper affiliation check**: a paper where the person is listed at another institute is dropped;
   - **manual overrides** where the automatic match was wrong (R. Boomi Shankar).
2. **One person split over several profiles.** OpenAlex often splits one researcher into several profiles. 64
   faculty have more than one. All profiles that pass the checks above are merged under one faculty ID, so the
   person is one node in the networks and one author in the self-citation test.
3. **Same name, different co-authors.** In `authorship_network.csv` the external Indian co-authors are nodes keyed by
   their OpenAlex author ID (`node_a`, `node_b`). 70 display names belong to more than one ID, and we keep those as
   separate people instead of merging them by name. The cost is that a real person split over two OpenAlex
   profiles may show up as two co-author nodes. We think that is safer than merging two different people with the
   same name.
4. **Same paper, two records.** Duplicate records of one paper are merged (same DOI, or same title and year after
   normalising), so a paper is not counted twice.

### Known issue

- **Ramana Athreya (IISER Pune)** is listed on the institute website under both Physics and Biology. The Pune
  scraper reads each listing separately, so he has two faculty IDs, `PUN101` (Physics) and `PUN102` (Biology),
  with the same OpenAlex profiles. As a result his 14 papers appear twice in `group19_data.csv`, and
  `authorship_network.csv` has 14 edges between PUN101 and PUN102 (he is effectively linked to himself). This is
  the only repeated name on the roster, and paper-level counts (distinct papers) are not affected.
  The fix is to merge listings by name + OpenAlex profile and record the second department as a joint department,
  as the Kolkata scraper already does.
- **6 faculty** (3 at each institute) could not be matched to any OpenAlex profile. Most are recent hires whose
  earlier papers carry other affiliations. They have no rows in the data.
