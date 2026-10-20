"""Build the four Week-2 deliverables (data/out/) plus analysis tables (data/stage/).

  group19_data.csv          faculty × paper rows, all columns of instruction note §5 (+ extras)
  citation_network.csv      directed paper→paper edges: internal + Indian in/out (§6a, §7c)
  authorship_network.csv    undirected co-author pairs, faculty + Indian co-authors (§6b, §7c)
  indian_connections.csv    your_inst × partner_inst aggregates (§7b, §7c)

  citation_origin           who cites our papers / whom we cite, in five categories (analysis)

Optional reference data, picked up when present:
  ref/scimago/*<year>*.csv         SCImago rankings (All types) -> quartile Q1–Q4, SJR, cites/doc (2y)
  ref/core.csv                     CORE conference ranks     -> A*/A/B/C
  data/stage/inst_subfields.parquet  topic profiles (topics.py) -> topic Jaccard
"""

import csv
import glob
import re
from pathlib import Path

import duckdb
from oa import ROOT

GROUP = 19
OURS = {"I181996519": "IISER Pune", "I127439422": "IISER Kolkata"}
HYPER = 100  # authorship lists are truncated at 100 -> treat as hyperauthored
LARGE_TEAM = 10  # course feedback: flag papers with more than 10 authors
KEEP_TYPES = ("article", "review", "letter", "conference-paper")
SCIMAGO_TYPES = ("journal", "conference and proceedings", "book series")
# venues OpenAlex labels as journals that only carry meeting abstracts / abstract digests
ABSTRACT_VENUES = (r"(?i)(bulletin of the american physical society|^APS$|^AGUFM$|^EGUGA$|^AGU fall meeting"
                   r"|EGU general assembly|japan geoscience union|^cheminform|goldschmidt abstracts|meeting abstracts)")


def scimago_clean(files: list[str]) -> Path:
    """SCImago exports contain unescaped quotes inside quoted fields (e.g. publisher names),
    which strict CSV readers reject. Python's csv reader tolerates them; rows whose field
    count still disagrees with the header are skipped.
    Writes (sc_year, sc_type, issn, quartile, sjr, cites2y); SCImago uses decimal commas."""
    out = ROOT / "data" / "stage" / "scimago_clean.csv"
    skipped = 0
    with out.open("w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["sc_year", "sc_type", "issn", "quartile", "sjr", "cites2y"])
        for f in files:
            year = re.search(r"((?:19|20)\d{2})", f.rsplit("/", 1)[-1]).group(1)
            with open(f, newline="", encoding="utf-8-sig", errors="replace") as fi:
                rd = csv.reader(fi, delimiter=";")
                hdr = next(rd)
                ti, ii, qi = hdr.index("Type") if "Type" in hdr else None, hdr.index("Issn"), hdr.index("SJR Best Quartile")
                # the 2-year column was "Cites / Doc. (2years)" in older exports
                si, ci = hdr.index("SJR"), next(i for i, h in enumerate(hdr) if h.endswith("/ Doc. (2years)"))
                num = lambda x: x.strip().replace(",", ".") or None
                for row in rd:
                    if len(row) != len(hdr):
                        skipped += row != []
                        continue
                    sc_type = row[ti].strip().lower() if ti is not None else "journal"
                    for issn in row[ii].replace(" ", "").split(","):
                        w.writerow([year, sc_type, issn, row[qi].strip(), num(row[si]), num(row[ci])])
    if skipped:
        print(f"SCImago: skipped {skipped} malformed row(s)")
    return out


def main() -> None:
    con = duckdb.connect(str(ROOT / "data" / "citegraph.duckdb"))
    sql = con.execute
    ours_vals = ", ".join(f"('{k}', '{v}')" for k, v in OURS.items())
    sql(f"CREATE OR REPLACE TABLE ours AS SELECT * FROM (VALUES {ours_vals}) t(inst_id, institution)")
    sql("CREATE OR REPLACE TABLE insts AS SELECT * FROM read_csv('ref/institutions.csv', all_varchar=true)")

    # ---- faculty ------------------------------------------------------------------------
    sql("""
    CREATE OR REPLACE TABLE faculty AS
    SELECT f.*, o.inst_id FROM read_csv('data/faculty.csv', all_varchar=true) f JOIN ours o USING (institution);
    CREATE OR REPLACE TABLE fac_profiles AS
    SELECT fac_id, unnest(string_split(openalex_ids, ';')) AS author_id FROM faculty WHERE openalex_ids <> '';
    """)

    # ---- quartiles (SCImago) & CORE ranks -----------------------------------------------
    # any CSV in ref/scimago/ with a 4-digit year in its name ("scimagojr 2024.csv", "scimago_2024.csv", …)
    sc_files = sorted(f for f in glob.glob(str(ROOT / "ref/scimago/*.csv"))
                      if re.search(r"(19|20)\d{2}", f.rsplit("/", 1)[-1]))
    if sc_files:
        sql(f"CREATE OR REPLACE TABLE scimago_raw AS SELECT * FROM read_csv('{scimago_clean(sc_files)}', all_varchar=true)")
        # files downloaded with "All types": keep the venue types our corpus contains
        # (journal / conference / book series sources); trade journals are not scholarly venues
        sql(f"""CREATE OR REPLACE TABLE scimago AS
                SELECT DISTINCT sc_year::INT AS sc_year, upper(issn) AS issn, quartile,
                       sjr::DOUBLE AS sjr, cites2y::DOUBLE AS cites2y FROM scimago_raw
                WHERE sc_type IN {SCIMAGO_TYPES}
                  AND quartile IN ('Q1','Q2','Q3','Q4') AND length(issn) = 8""")
        kept = con.execute(f"""SELECT sc_type, count(*), sc_type IN {SCIMAGO_TYPES} FROM scimago_raw
                               GROUP BY 1 ORDER BY 2 DESC""").fetchall()
        print(f"SCImago: {len(sc_files)} year file(s); rows by type: "
              + ", ".join(f"{t} {n:,}{'' if k else ' (dropped)'}" for t, n, k in kept))
    else:
        sql("CREATE OR REPLACE TABLE scimago (sc_year INT, issn VARCHAR, quartile VARCHAR, sjr DOUBLE, cites2y DOUBLE)")
        print("SCImago: no files in ref/scimago/ -> quartile column left empty")
    core_f = ROOT / "ref" / "core.csv"
    if core_f.exists():
        sql(f"""CREATE OR REPLACE TABLE core AS
                SELECT lower(trim(column1)) AS title, lower(trim(column2)) AS acronym, column4 AS rank
                FROM read_csv('{core_f}', header=false, all_varchar=true)
                WHERE column4 IN ('A*','A','B','C')""")
    else:
        sql("CREATE OR REPLACE TABLE core (title VARCHAR, acronym VARCHAR, rank VARCHAR)")

    # ---- corpus ---------------------------------------------------------------------------
    sql(f"""
    CREATE OR REPLACE TABLE works_all AS SELECT * FROM 'data/stage/works.parquet'
    WHERE year BETWEEN 2016 AND 2026 AND work_type IN {KEEP_TYPES}
      AND source_type IN ('journal', 'conference', 'book series')
      AND NOT regexp_matches(coalesce(source_name, ''), '{ABSTRACT_VENUES}');

    -- faculty × work, keeping only papers written while affiliated with the institute:
    -- drop if the profile is listed with institutions and none of them is the faculty's
    CREATE OR REPLACE TABLE fac_work_raw AS
    WITH fw AS (
      SELECT DISTINCT p.fac_id, aw.author_id, aw.work_id
      FROM 'data/stage/author_works.parquet' aw JOIN fac_profiles p USING (author_id)
      WHERE aw.work_id IN (SELECT work_id FROM works_all)
    ), aff AS (
      SELECT a.work_id, a.author_id, count(a.inst_id) AS n_inst,
             list(DISTINCT a.inst_id) FILTER (a.inst_id IS NOT NULL) AS insts
      FROM 'data/stage/authorships.parquet' a GROUP BY ALL
    )
    SELECT fw.fac_id, fw.work_id, f.institution, f.inst_id,
           CASE WHEN aff.work_id IS NULL THEN 'not listed (truncated)'
                WHEN aff.n_inst = 0 THEN 'no affiliation parsed'
                WHEN list_contains(aff.insts, f.inst_id) THEN 'affiliated'
                ELSE 'elsewhere' END AS affiliation_check
    FROM fw JOIN faculty f USING (fac_id)
    LEFT JOIN aff ON aff.work_id = fw.work_id AND aff.author_id = fw.author_id;

    -- dedupe: one row per (faculty, paper); duplicate records of the same paper
    -- (same DOI, or same normalised title + year) collapse onto the most-cited record
    CREATE OR REPLACE TABLE corpus AS
    WITH w AS (
      SELECT *, regexp_replace(lower(title), '[^a-z0-9]', '', 'g') AS tkey FROM works_all
      WHERE work_id IN (SELECT work_id FROM fac_work_raw WHERE affiliation_check <> 'elsewhere')
    )
    SELECT * EXCLUDE (tkey) FROM w
    QUALIFY row_number() OVER (PARTITION BY coalesce(doi, tkey || year) ORDER BY cited_by_count DESC, work_id) = 1
       AND row_number() OVER (PARTITION BY tkey, year ORDER BY cited_by_count DESC, work_id) = 1;

    CREATE OR REPLACE TABLE fac_work AS
    SELECT DISTINCT fac_id, work_id, institution, inst_id, affiliation_check FROM fac_work_raw
    WHERE affiliation_check <> 'elsewhere' AND work_id IN (SELECT work_id FROM corpus);

    -- which of our institutes each corpus paper belongs to
    CREATE OR REPLACE TABLE work_inst AS
    SELECT work_id, string_agg(DISTINCT institution, ';' ORDER BY institution) AS our_insts
    FROM fac_work GROUP BY 1;
    """)

    # ---- quartile / rank per corpus paper ---------------------------------------------------
    sql("""
    CREATE OR REPLACE TABLE work_quartile AS
    WITH iss AS (
      SELECT w.work_id, w.year, upper(replace(unnest(list_distinct(list_append(coalesce(w.issns, []), w.issn_l))), '-', '')) AS issn
      FROM corpus w WHERE w.issn_l IS NOT NULL
    ), m AS (
      SELECT iss.work_id, s.quartile, s.sjr, s.cites2y,
             -- prefer the SCImago year closest to (and not after) the publication year
             row_number() OVER (PARTITION BY iss.work_id ORDER BY (s.sc_year > iss.year), abs(s.sc_year - iss.year), s.quartile) AS rk
      FROM iss JOIN scimago s USING (issn)
    )
    SELECT work_id, quartile, sjr, cites2y FROM m WHERE rk = 1;

    CREATE OR REPLACE TABLE work_core AS
    SELECT w.work_id, max_by(c.rank, jaro_winkler_similarity(lower(w.source_name), c.title)) AS core_rank
    FROM corpus w JOIN core c
      ON jaro_winkler_similarity(lower(w.source_name), c.title) > 0.93
      OR regexp_matches(lower(w.source_name), '\\b' || c.acronym || '\\b')
    WHERE w.source_type = 'conference' OR w.work_type = 'conference-paper'
    GROUP BY 1;
    """)

    # ---- Indian institutions on link works and corpus works -------------------------------
    sql("""
    CREATE OR REPLACE TABLE link_inst AS
    SELECT DISTINCT li.link_id, li.inst_id, i.short_name, i.cluster
    FROM 'data/stage/link_insts.parquet' li JOIN insts i USING (inst_id) WHERE li.country = 'IN';

    CREATE OR REPLACE TABLE corpus_inst AS   -- Indian institutions on each corpus paper
    SELECT DISTINCT a.work_id, a.inst_id, i.short_name, i.cluster
    FROM 'data/stage/authorships.parquet' a JOIN insts i USING (inst_id)
    WHERE a.country = 'IN' AND a.work_id IN (SELECT work_id FROM corpus);

    -- in-flow: Indian work cites a corpus paper; out-flow: corpus paper cites an Indian work
    CREATE OR REPLACE TABLE in_edges AS
    SELECT e.source_id, e.target_id FROM 'data/stage/in_edges.parquet' e
    WHERE e.target_id IN (SELECT work_id FROM corpus) AND e.source_id NOT IN (SELECT work_id FROM corpus);
    CREATE OR REPLACE TABLE out_edges AS
    SELECT DISTINCT r.work_id AS source_id, r.ref_id AS target_id
    FROM 'data/stage/work_refs.parquet' r
    WHERE r.work_id IN (SELECT work_id FROM corpus)
      AND r.ref_id IN (SELECT link_id FROM 'data/stage/link_works.parquet' WHERE kind = 'cited')
      AND r.ref_id NOT IN (SELECT work_id FROM corpus);
    -- authors of every paper on a citation edge: corpus papers (listed authors plus every
    -- OpenAlex profile of their faculty, since OpenAlex splits people) and Indian link works
    CREATE OR REPLACE TABLE node_authors AS
    SELECT DISTINCT work_id AS id, author_id FROM 'data/stage/authorships.parquet'
    WHERE work_id IN (SELECT work_id FROM corpus) AND author_id IS NOT NULL
    UNION
    SELECT fw.work_id, p.author_id FROM fac_work_raw fw JOIN fac_profiles p USING (fac_id)
    WHERE fw.work_id IN (SELECT work_id FROM corpus)
    UNION
    SELECT link_id, author_id FROM 'data/stage/link_authors.parquet' WHERE author_id IS NOT NULL;

    CREATE OR REPLACE TABLE int_edges AS
    SELECT DISTINCT r.work_id AS source_id, r.ref_id AS target_id
    FROM 'data/stage/work_refs.parquet' r
    WHERE r.work_id IN (SELECT work_id FROM corpus) AND r.ref_id IN (SELECT work_id FROM corpus)
      AND r.work_id <> r.ref_id;
    """)

    # ---- deliverable 1: group19_data.csv ----------------------------------------------------
    sql(f"""
    CREATE OR REPLACE TABLE data_rows AS
    WITH co AS (   -- Indian co-author institutions other than the row's own institute
      SELECT fw.fac_id, fw.work_id, string_agg(DISTINCT ci.short_name, ';' ORDER BY ci.short_name) AS coauthor_institutes
      FROM fac_work fw JOIN corpus_inst ci ON ci.work_id = fw.work_id AND ci.inst_id <> fw.inst_id
      GROUP BY ALL
    ), cites AS (
      SELECT DISTINCT fw.fac_id, fw.work_id FROM fac_work fw
      JOIN out_edges e ON e.source_id = fw.work_id
      JOIN link_inst li ON li.link_id = e.target_id AND li.inst_id <> fw.inst_id
    ), citedby AS (
      SELECT DISTINCT fw.fac_id, fw.work_id FROM fac_work fw
      JOIN in_edges e ON e.target_id = fw.work_id
      JOIN link_inst li ON li.link_id = e.source_id AND li.inst_id <> fw.inst_id
    )
    SELECT {GROUP} AS "group", fw.institution, f.name AS author, w.title, w.year,
           CASE WHEN w.source_type = 'conference' OR w.work_type = 'conference-paper'
                THEN 'conference' ELSE 'journal' END AS type,
           w.source_name AS journal_name,
           CASE WHEN w.source_type <> 'conference' THEN w.issn_l END AS issn,
           CASE WHEN w.doi IS NOT NULL THEN 'https://doi.org/' || w.doi END AS doi,
           w.cited_by_count AS citations,
           -- journals: SCImago quartile; conferences: CORE rank if listed, else SCImago proceedings quartile
           CASE WHEN w.source_type = 'conference' OR w.work_type = 'conference-paper'
                THEN coalesce(wc.core_rank, q.quartile) ELSE q.quartile END AS quartile,
           co.coauthor_institutes,
           cites.work_id IS NOT NULL AS cites_indian_inst,
           citedby.work_id IS NOT NULL AS cited_by_indian_inst,
           -- extras beyond §5
           fw.fac_id, f.department, 'https://openalex.org/' || w.work_id AS openalex_id,
           w.field, w.subfield, w.n_authors, w.n_authors >= {HYPER} AS hyperauthored,
           fw.affiliation_check,
           w.n_authors > {LARGE_TEAM} AS large_team,
           -- SCImago venue indicators (same year match as the quartile); cites2y is the
           -- open stand-in for the journal impact factor
           q.sjr, q.cites2y AS if_proxy
    FROM fac_work fw JOIN faculty f USING (fac_id) JOIN corpus w USING (work_id)
    LEFT JOIN work_quartile q USING (work_id) LEFT JOIN work_core wc USING (work_id)
    LEFT JOIN co USING (fac_id, work_id) LEFT JOIN cites USING (fac_id, work_id)
    LEFT JOIN citedby USING (fac_id, work_id)
    ORDER BY fw.institution, f.name, w.year, w.title;
    COPY data_rows TO 'data/out/group{GROUP}_data.csv';
    """)

    # ---- deliverable 2: citation_network.csv ------------------------------------------------
    sql(f"""
    CREATE OR REPLACE TABLE node_meta AS   -- doi / inst / year for every paper on an edge
    SELECT w.work_id AS id, w.doi, wi.our_insts AS insts, w.year FROM corpus w JOIN work_inst wi USING (work_id)
    UNION ALL
    SELECT lw.link_id, any_value(lw.doi), string_agg(DISTINCT li.short_name, ';' ORDER BY li.short_name), any_value(lw.year)
    FROM 'data/stage/link_works.parquet' lw LEFT JOIN link_inst li ON li.link_id = lw.link_id
    WHERE lw.link_id NOT IN (SELECT work_id FROM corpus)
    GROUP BY lw.link_id;

    CREATE OR REPLACE TABLE cit_edges AS
    WITH e AS (
      SELECT source_id, target_id, 'internal' AS edge_kind FROM int_edges
      UNION ALL SELECT source_id, target_id, 'in' FROM in_edges
      UNION ALL SELECT source_id, target_id, 'out' FROM out_edges
    )
    SELECT coalesce('https://doi.org/' || s.doi, 'https://openalex.org/' || e.source_id) AS source_doi,
           coalesce('https://doi.org/' || t.doi, 'https://openalex.org/' || e.target_id) AS target_doi,
           s.insts AS source_inst, t.insts AS target_inst, s.year,
           e.source_id, e.target_id, e.edge_kind,
           -- author self-citation: the two papers share at least one author
           EXISTS (SELECT 1 FROM node_authors a JOIN node_authors b USING (author_id)
                   WHERE a.id = e.source_id AND b.id = e.target_id) AS self_citation,
           -- an endpoint is one of our >=100-author papers (excluded from the analysis)
           e.source_id IN (SELECT work_id FROM corpus WHERE n_authors >= {HYPER})
             OR e.target_id IN (SELECT work_id FROM corpus WHERE n_authors >= {HYPER}) AS involves_hyper
    FROM e JOIN node_meta s ON s.id = e.source_id JOIN node_meta t ON t.id = e.target_id;
    COPY cit_edges TO 'data/out/citation_network.csv';
    """)

    # ---- deliverable 3: authorship_network.csv ----------------------------------------------
    sql(f"""
    CREATE OR REPLACE TABLE paper_people AS   -- nodes per paper: our faculty + Indian co-authors
    WITH a AS (
      SELECT a.work_id, a.author_id, a.author_name, a.inst_id, i.short_name, a.country
      FROM 'data/stage/authorships.parquet' a LEFT JOIN insts i USING (inst_id)
      WHERE a.work_id IN (SELECT work_id FROM corpus WHERE n_authors < {HYPER})
    ), fac AS (
      SELECT DISTINCT a.work_id, p.fac_id AS node_id, f.name, f.institution AS inst, true AS is_faculty
      FROM a JOIN fac_profiles p USING (author_id) JOIN faculty f USING (fac_id)
      WHERE (a.work_id, p.fac_id) IN (SELECT (work_id, fac_id) FROM fac_work)
    ), ext AS (
      SELECT a.work_id, a.author_id AS node_id, any_value(a.author_name) AS name,
             -- an Indian co-author's institution: prefer a non-IISER-Pune/Kolkata one
             min(a.short_name ORDER BY a.inst_id IN (SELECT inst_id FROM ours), a.short_name) AS inst,
             false AS is_faculty
      FROM a
      WHERE a.author_id NOT IN (SELECT author_id FROM fac_profiles) AND a.country = 'IN'
      GROUP BY a.work_id, a.author_id
      -- students/postdocs of our own institutes are excluded (not faculty, not external)
      HAVING bool_or(a.inst_id NOT IN (SELECT inst_id FROM ours))
    )
    SELECT * FROM fac UNION ALL SELECT * FROM ext;

    CREATE OR REPLACE TABLE auth_edges AS
    SELECT a.name AS author_a, b.name AS author_b,
           coalesce('https://doi.org/' || w.doi, 'https://openalex.org/' || w.work_id) AS paper_doi,
           a.inst AS inst_a, b.inst AS inst_b, w.year,
           a.node_id AS node_a, b.node_id AS node_b, a.is_faculty AS a_faculty, b.is_faculty AS b_faculty,
           w.n_authors, w.work_id,
           a.inst IS DISTINCT FROM b.inst AS cross_institution,
           ia.cluster IS DISTINCT FROM ib.cluster AS cross_cluster
    FROM paper_people a JOIN paper_people b ON a.work_id = b.work_id AND a.node_id < b.node_id
    JOIN corpus w ON w.work_id = a.work_id
    -- a few generic short names ("Government Medical College and Hospital") belong to
    -- several institutions in different clusters; take one so edges are not duplicated
    LEFT JOIN (SELECT short_name, min(cluster) AS cluster FROM insts GROUP BY 1) ia ON ia.short_name = a.inst
    LEFT JOIN (SELECT short_name, min(cluster) AS cluster FROM insts GROUP BY 1) ib ON ib.short_name = b.inst;
    COPY auth_edges TO 'data/out/authorship_network.csv';
    """)

    # ---- deliverable 4: indian_connections.csv ----------------------------------------------
    # topic similarity: subfields carrying >= 0.5% of an institution's 2016–2026 output
    if not (ROOT / "data/stage/inst_subfields.parquet").exists():
        print("topics: data/stage/inst_subfields.parquet missing (run `make topics`) -> Jaccard left empty")
        sql("CREATE OR REPLACE TABLE inst_subfields (inst_id VARCHAR, subfield VARCHAR, subfield_id VARCHAR, n BIGINT)")
    else:
        sql("CREATE OR REPLACE TABLE inst_subfields AS SELECT * FROM 'data/stage/inst_subfields.parquet'")
    sql("""
    CREATE OR REPLACE TABLE jaccard AS
    WITH s AS (
      SELECT inst_id, subfield, n / sum(n) OVER (PARTITION BY inst_id) AS share
      FROM inst_subfields
    ), sets AS (SELECT * FROM s WHERE share >= 0.005),
    pairs AS (
      SELECT o.inst_id AS our_id, p.inst_id AS partner_id
      FROM (SELECT DISTINCT inst_id FROM sets WHERE inst_id IN (SELECT inst_id FROM ours)) o,
           (SELECT DISTINCT inst_id FROM sets WHERE inst_id NOT IN (SELECT inst_id FROM ours)) p
    ), u AS (
      SELECT pr.our_id, pr.partner_id, x.subfield,
             max(x.share) FILTER (x.inst_id = pr.our_id) AS so,
             max(x.share) FILTER (x.inst_id = pr.partner_id) AS sp
      FROM pairs pr JOIN sets x ON x.inst_id IN (pr.our_id, pr.partner_id)
      GROUP BY ALL
    )
    SELECT our_id, partner_id,
           count(*) FILTER (so IS NOT NULL AND sp IS NOT NULL) / count(*)::DOUBLE AS jaccard_topics,
           sum(least(coalesce(so,0), coalesce(sp,0))) / sum(greatest(coalesce(so,0), coalesce(sp,0))) AS weighted_jaccard
    FROM u GROUP BY ALL;
    """)
    # >=100-author papers are left out (they would make CMS institutes our top partners), and
    # citation counts leave out author self-citations
    sql(f"""
    CREATE OR REPLACE TABLE connections AS
    WITH fw_main AS (
      SELECT DISTINCT fw.work_id, fw.institution, fw.inst_id FROM fac_work fw JOIN corpus w USING (work_id)
      WHERE w.n_authors < {HYPER}
    ), shared AS (
      SELECT fw.institution AS your_inst, fw.inst_id AS our_id, ci.inst_id AS partner_id,
             count(DISTINCT fw.work_id) AS shared_papers
      FROM fw_main fw JOIN corpus_inst ci ON ci.work_id = fw.work_id AND ci.inst_id <> fw.inst_id
      GROUP BY ALL
    ), shared_all AS (
      SELECT fw.inst_id AS our_id, ci.inst_id AS partner_id, count(DISTINCT fw.work_id) AS shared_papers_incl_hyper
      FROM fac_work fw JOIN corpus_inst ci ON ci.work_id = fw.work_id AND ci.inst_id <> fw.inst_id
      GROUP BY ALL
    ), ce AS (SELECT source_id, target_id, edge_kind FROM cit_edges WHERE NOT self_citation),
    cin AS (   -- citations received from partner (citing works with a partner author)
      SELECT fw.inst_id AS our_id, li.inst_id AS partner_id, count(DISTINCT (e.source_id, e.target_id)) AS cites_in
      FROM ce e JOIN fw_main fw ON fw.work_id = e.target_id
      JOIN link_inst li ON li.link_id = e.source_id AND li.inst_id <> fw.inst_id
      WHERE e.edge_kind = 'in'
      GROUP BY ALL
    ), cout AS (  -- citations given to partner
      SELECT fw.inst_id AS our_id, li.inst_id AS partner_id, count(DISTINCT (e.source_id, e.target_id)) AS cites_out
      FROM ce e JOIN fw_main fw ON fw.work_id = e.source_id
      JOIN link_inst li ON li.link_id = e.target_id AND li.inst_id <> fw.inst_id
      WHERE e.edge_kind = 'out'
      GROUP BY ALL
    ), keys AS (
      SELECT our_id, partner_id FROM shared UNION SELECT our_id, partner_id FROM shared_all
      UNION SELECT our_id, partner_id FROM cin
      UNION SELECT our_id, partner_id FROM cout
    )
    SELECT o.institution AS your_inst, i.short_name AS partner_inst,
           coalesce(s.shared_papers, 0) AS shared_papers,
           coalesce(sa.shared_papers_incl_hyper, 0) AS shared_papers_incl_hyper,
           coalesce(cin.cites_in, 0) + coalesce(cout.cites_out, 0) AS total_citations,
           coalesce(cin.cites_in, 0) AS cites_in, coalesce(cout.cites_out, 0) AS cites_out,
           i.cluster AS partner_cluster, i.name AS partner_full_name, k.partner_id,
           i.cluster <> 'IISc · TIFR · IISER' AS cross_cluster,
           j.jaccard_topics, j.weighted_jaccard
    FROM keys k JOIN ours o ON o.inst_id = k.our_id JOIN insts i ON i.inst_id = k.partner_id
    LEFT JOIN shared s USING (our_id, partner_id) LEFT JOIN shared_all sa USING (our_id, partner_id)
    LEFT JOIN cin USING (our_id, partner_id)
    LEFT JOIN cout USING (our_id, partner_id) LEFT JOIN jaccard j USING (our_id, partner_id)
    ORDER BY your_inst, shared_papers DESC, total_citations DESC;
    COPY connections TO 'data/out/indian_connections.csv';
    """)

    # ---- citation origin: who cites our papers, whom do our papers cite ---------------------
    # Every citation link is put in the first category that fits:
    #   self               the two papers share an author
    #   own institute      the other paper has an author at the same IISER
    #   India + abroad     Indian and foreign authors (or a truncated >=100-author list)
    #   other Indian only  only Indian authors, none of the above
    #   abroad or unknown  no Indian affiliation; we only know their number:
    #                      cited_by_count (in) or the reference count (out) minus the Indian links
    # india_frac = share of the other paper's authors with an Indian address (fractional counting).
    sql(f"""
    CREATE OR REPLACE TABLE link_profile AS
    SELECT link_id, any_value(n_auth) AS n_auth,
           count(*) FILTER (len(countries) > 0) AS n_known,
           count(*) FILTER (list_contains(countries, 'IN')) AS n_in,
           bool_or(len(list_filter(countries, c -> c <> 'IN')) > 0) AS has_abroad
    FROM 'data/stage/link_authors.parquet' GROUP BY 1;

    CREATE OR REPLACE TABLE citation_origin AS
    WITH t AS (   -- our papers, per institute, without >=100-author papers
      SELECT DISTINCT fw.work_id, fw.institution, fw.inst_id, w.year, w.cited_by_count, w.n_refs
      FROM fac_work fw JOIN corpus w USING (work_id) WHERE w.n_authors < {HYPER}
    ), links AS (
      SELECT 'in' AS direction, e.target_id AS work_id, e.source_id AS other_id
      FROM 'data/stage/in_edges.parquet' e WHERE e.source_id <> e.target_id
      UNION
      SELECT 'out', r.work_id, r.ref_id FROM 'data/stage/work_refs.parquet' r
      WHERE r.ref_id IN (SELECT link_id FROM 'data/stage/link_works.parquet' WHERE kind = 'cited')
        AND r.ref_id <> r.work_id
      UNION   -- citations between two of our papers, from either side's lists (as in cit_edges)
      SELECT 'in', target_id, source_id FROM cit_edges WHERE edge_kind = 'internal'
      UNION
      SELECT 'out', source_id, target_id FROM cit_edges WHERE edge_kind = 'internal'
    ), cat AS (
      SELECT t.institution, t.work_id, t.year, l.direction,
             CASE WHEN EXISTS (SELECT 1 FROM node_authors a JOIN node_authors b USING (author_id)
                               WHERE a.id = l.other_id AND b.id = l.work_id) THEN 'self'
                  WHEN EXISTS (SELECT 1 FROM 'data/stage/link_insts.parquet' li
                               WHERE li.link_id = l.other_id AND li.inst_id = t.inst_id) THEN 'own institute'
                  WHEN p.has_abroad OR p.n_auth >= {HYPER} THEN 'India + abroad'
                  ELSE 'other Indian only' END AS category,
             coalesce(p.n_in / nullif(p.n_known, 0), 1.0) AS india_frac,
             -- the other paper is itself one of ours (any of our faculty on it)
             l.other_id IN (SELECT work_id FROM corpus) AS from_ours
      FROM links l JOIN t USING (work_id) LEFT JOIN link_profile p ON p.link_id = l.other_id
    ), indian AS (
      SELECT institution, work_id, year, direction, category, from_ours, count(*) AS n, sum(india_frac) AS india_frac
      FROM cat GROUP BY ALL
    ), indian_tot AS (
      SELECT institution, work_id, direction, sum(n) AS n FROM indian GROUP BY ALL
    ), rest AS (
      SELECT t.institution, t.work_id, t.year, d.direction, 'abroad or unknown' AS category, false AS from_ours,
             greatest(CASE d.direction WHEN 'in' THEN t.cited_by_count ELSE t.n_refs END
                      - coalesce(i.n, 0), 0) AS n,
             0.0 AS india_frac
      FROM t CROSS JOIN (VALUES ('in'), ('out')) d(direction)
      LEFT JOIN indian_tot i ON i.institution = t.institution AND i.work_id = t.work_id AND i.direction = d.direction
    )
    SELECT * FROM indian UNION ALL SELECT * FROM rest WHERE n > 0
    ORDER BY institution, work_id, direction, category, from_ours;
    COPY citation_origin TO 'data/out/citation_origin.csv';
    """)

    # ---- summary --------------------------------------------------------------------------
    for name, q in [
        ("faculty with papers", "SELECT institution, count(DISTINCT fac_id) FROM fac_work GROUP BY 1 ORDER BY 1"),
        ("papers (distinct)", "SELECT our_insts, count(*) FROM work_inst GROUP BY 1 ORDER BY 1"),
        ("data rows", "SELECT count(*) FROM data_rows"),
        ("quartile coverage", "SELECT type, quartile, count(*) FROM data_rows GROUP BY ALL ORDER BY ALL"),
        ("affiliation check", "SELECT affiliation_check, count(*) FROM fac_work GROUP BY 1"),
        ("citation edges", "SELECT edge_kind, count(*) FROM cit_edges GROUP BY 1"),
        ("authorship edges", "SELECT count(*), count(*) FILTER (a_faculty AND b_faculty), count(*) FILTER (cross_institution) FROM auth_edges"),
        ("connections", "SELECT your_inst, count(*), sum(shared_papers), sum(total_citations) FROM connections GROUP BY 1"),
        ("self-citation share of internal edges", "SELECT avg(self_citation::INT) FROM cit_edges WHERE edge_kind = 'internal' AND NOT involves_hyper"),
        ("citation origin", "SELECT institution, direction, category, sum(n)::BIGINT FROM citation_origin GROUP BY ALL ORDER BY ALL"),
    ]:
        print(f"-- {name}:", con.sql(q).fetchall())


if __name__ == "__main__":
    main()
