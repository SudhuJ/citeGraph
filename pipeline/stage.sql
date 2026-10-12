-- Flatten raw OpenAlex JSONL into compact Parquet tables (data/stage/*.parquet).
-- Run: duckdb < pipeline/stage.sql   (via `make stage`)
SET preserve_insertion_order = false;
CREATE OR REPLACE MACRO sid(x) AS regexp_extract(x, '[^/]+$');
CREATE OR REPLACE MACRO raw(f) AS TABLE
  SELECT * FROM read_ndjson('data/raw/' || f || '.jsonl', maximum_object_size = 500000000);

-- corpus works --------------------------------------------------------------
COPY (
  SELECT sid(id) AS work_id,
         lower(regexp_replace(doi, '^https?://(dx\.)?doi\.org/', '')) AS doi,
         display_name AS title,
         publication_year AS year,
         type AS work_type,
         sid(primary_location.source.id) AS source_id,
         primary_location.source.display_name AS source_name,
         primary_location.source.type AS source_type,
         primary_location.source.issn_l AS issn_l,
         primary_location.source.issn AS issns,
         cited_by_count,
         len(authorships) AS n_authors,
         primary_topic.display_name AS topic,
         primary_topic.subfield.display_name AS subfield,
         primary_topic.field.display_name AS field,
         primary_topic.domain.display_name AS domain,
         list_distinct([t.field.display_name FOR t IN topics]) AS fields_all,
         len(referenced_works) AS n_refs
  FROM raw('works')
) TO 'data/stage/works.parquet';

COPY (
  SELECT sid(id) AS work_id, sid(unnest(referenced_works)) AS ref_id FROM raw('works')
) TO 'data/stage/work_refs.parquet';

-- one row per (work, author, institution); authors without institution keep a NULL row
COPY (
  WITH a AS (SELECT sid(id) AS work_id, unnest(authorships) AS au FROM raw('works'))
  SELECT work_id, sid(au.author.id) AS author_id, au.author.display_name AS author_name,
         au.author_position AS position, sid(i.id) AS inst_id, i.display_name AS inst_name,
         i.ror AS inst_ror, i.country_code AS country
  FROM a LEFT JOIN LATERAL (SELECT unnest(au.institutions) AS i) ON true
) TO 'data/stage/authorships.parquet';

-- Indian link works (citing = cite a corpus work, cited = cited by a corpus work) ---
COPY (
  SELECT 'citing' AS kind, sid(id) AS link_id, publication_year AS year,
         lower(regexp_replace(doi, '^https?://(dx\.)?doi\.org/', '')) AS doi,
         display_name AS title, primary_topic.field.display_name AS field
  FROM raw('citing')
  UNION ALL
  SELECT 'cited', sid(id), publication_year,
         lower(regexp_replace(doi, '^https?://(dx\.)?doi\.org/', '')), display_name,
         primary_topic.field.display_name
  FROM raw('cited')
) TO 'data/stage/link_works.parquet';

-- institutions of link works (distinct per work; only what flow analysis needs)
COPY (
  WITH a AS (
    SELECT sid(id) AS link_id, unnest(authorships) AS au FROM raw('citing')
    UNION ALL
    SELECT sid(id), unnest(authorships) FROM raw('cited')
  )
  SELECT DISTINCT link_id, sid(i.id) AS inst_id, i.display_name AS inst_name, i.country_code AS country
  FROM a, LATERAL (SELECT unnest(au.institutions) AS i)
) TO 'data/stage/link_insts.parquet';

-- citing works' references into the corpus -> in-flow edges (citing -> corpus)
COPY (
  WITH corpus AS (SELECT sid(id) AS work_id FROM raw('works'))
  SELECT DISTINCT sid(c.id) AS source_id, r.ref AS target_id
  FROM raw('citing') c, LATERAL (SELECT sid(unnest(c.referenced_works)) AS ref) r
  WHERE r.ref IN (SELECT work_id FROM corpus)
) TO 'data/stage/in_edges.parquet';

-- authoritative profile -> work map (authorships are truncated at 100 in list responses)
COPY (
  SELECT author_id, unnest(work_ids) AS work_id FROM raw('author_works')
) TO 'data/stage/author_works.parquet';
