# SOURCES — Group 19 (IISER Pune & IISER Kolkata, 2016–2026)

All the sources behind `group19_data.csv`, `citation_network.csv`, `authorship_network.csv`
and `indian_connections.csv`. Data was collected in October 2026 (faculty rosters on 12–13 Oct,
OpenAlex on 12 Oct).

## 1. Faculty rosters (institute websites)

Only **regular faculty** were scraped. Visiting, adjunct, emeritus and honorary faculty were left out.

| Institute | Page(s) | Faculty |
|---|---|---|
| IISER Pune | https://www.iiserpune.ac.in/institute/people/faculty/regular-faculty | 146 |
| IISER Kolkata | https://www.iiserkol.ac.in/web/faculty/biological-sciences | 130 (all departments) |
| | https://www.iiserkol.ac.in/web/faculty/chemical-sciences | |
| | https://www.iiserkol.ac.in/web/faculty/computational-data-sciences | |
| | https://www.iiserkol.ac.in/web/faculty/earth-sciences | |
| | https://www.iiserkol.ac.in/web/faculty/humanities-social-sciences | |
| | https://www.iiserkol.ac.in/web/faculty/mathematics-and-statistics | |
| | https://www.iiserkol.ac.in/web/faculty/physical-sciences | |

From each page we took the name, designation, department(s) and profile URL, saved in `data/faculty_seed.csv`.
Every faculty member's own profile page link is kept in the `profile_url` column of `data/faculty.csv`.

## 2. OpenAlex — papers, authors, citations, institutions

- **Website:** https://openalex.org · **API:** https://api.openalex.org · **Docs:** https://docs.openalex.org
- **Licence:** CC0 (public domain). OpenAlex was the only source for bibliographic data.
- All API responses are cached on disk, so the dataset can be rebuilt exactly.

| What | Endpoint and filter | Used for |
|---|---|---|
| Candidate author profiles | `/authors?filter=affiliations.institution.id:I181996519` (IISER Pune), `…:I127439422` (IISER Kolkata) | Matching roster names to OpenAlex author IDs |
| Matched faculty profiles | `/authors?filter=openalex_id:…` | ORCID, lifetime h-index, works count |
| Faculty papers | `/works?filter=author.id:…,publication_year:2016-2026` | Title, year, venue, ISSN, DOI, citation count, authors and their affiliations, references, topics |
| Indian papers citing ours | `/works?filter=cites:…,institutions.country_code:IN` | In-flow edges, `cited_by_indian_inst` |
| Indian papers we cite | `/works?filter=cited_by:…,institutions.country_code:IN` | Out-flow edges, `cites_indian_inst` |
| Institution records | `/institutions?filter=openalex_id:…` (with parent lineage) | Names, ROR IDs and types of the 2,121 Indian institutions in the data |
| Topic profiles | `/works?filter=institutions.id:…,publication_year:2016-2026&group_by=primary_topic.subfield.id` | `jaccard_topics` in `indian_connections.csv` |

Through OpenAlex we also used:
- **ORCID** (https://orcid.org) iDs on author profiles, to tell namesakes apart.
- **ROR** (https://ror.org) IDs on institution records.
- **Crossref / DOI** (https://doi.org) DOIs, which identify papers in the network files.

## 3. Journal rankings — SCImago Journal & Country Rank

- **Website:** https://www.scimagojr.com/journalrank.php
- Yearly ranking CSVs for **2016–2025**, downloaded by hand with type set to "All types".
- Used for the `quartile` column (SJR best quartile), `sjr` and `if_proxy` (citations per document over 2 years,
  an open substitute for the Clarivate Impact Factor, which is not freely available).
- Matched on ISSN, using the SCImago year closest to the publication year without going past it. SCImago entries
  for journals, conferences and proceedings, and book series were used. Trade journals were dropped.

## 4. Conference rankings — CORE

- **Website:** https://portal.core.edu.au/conf-ranks/ (ICORE2026 export, saved as `ref/core.csv`)
- Gives an A*/A/B/C rank for conference papers. It changes little here: only 209 of 8,574 rows are conference
  papers, and 20 of them have a CORE rank.

## 5. Course materials

- *DPCN Instruction Note* (Monsoon 2026): the required columns and definitions for each deliverable.
- *DPCN Research Mapping Project* slides: the list of Indian institutions and the clusters they belong to (IIT, IIIT, NIT,
  Central University, IISc · TIFR · IISER, Premier Science, CSIR, DAE). These were used to classify partner institutes.

## 6. Journals and conferences in the dataset

Venue names and ISSNs come from OpenAlex (`primary_location.source`). The dataset covers **1,368 journals**
and **66 conference/proceedings venues**. The full list is in the `journal_name` and `issn` columns of `group19_data.csv`.
These are the most frequent venues (counting distinct papers, without the 100+ author papers):

| Journal | Papers | Conference / proceedings | Papers |
|---|---|---|---|
| Physical Review B | 162 | Lecture Notes in Computer Science | 25 |
| Chemical Communications | 146 | Abstracts with Programs – GSA | 24 |
| Angewandte Chemie Int. Ed. | 113 | AIP Conference Proceedings | 14 |
| Chemical Science | 102 | International Cosmic Ray Conference | 10 |
| J. Phys. Chem. C | 99 | Journal of Physics: Conference Series | 7 |
| Physical Review A | 98 | Proceedings of SPIE | 7 |
| Chemistry – A European Journal | 96 | Springer Proceedings in Physics | 6 |
| Organic Letters | 93 | ACM/IEEE JCDL | 6 |
| Chemistry – An Asian Journal | 92 | Frontiers in Optics + Laser Science | 6 |
| J. Organic Chemistry | 83 | ACM SIGIR | 5 |

## 7. Software (open source)

Python 3.14 with uv, httpx, selectolax, DuckDB and python-igraph. Dashboard: Observable Framework with sigma.js.
Code: https://github.com/SudhuJ/citeGraph · Dashboard: https://sudhuj.github.io/citeGraph/
