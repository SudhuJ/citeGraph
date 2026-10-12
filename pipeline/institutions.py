"""Classify every Indian institution seen in the data into the course clusters.

Fetches OpenAlex institution records (with parent lineage) for all Indian institution IDs
in the staged tables and writes ref/institutions.csv:
  inst_id, name, ror, type, cluster, short_name, course_inst
`cluster` follows the course PPT (IIT, IIIT, NIT, Central University, IISc/TIFR/IISER,
Premier Science, CSIR, DAE) plus University / Other for everything else.
"""

import csv
import re

import duckdb
from oa import ROOT, chunks, get, short

# course institutions (PPT) -> (cluster, short name); matched on OpenAlex display name
COURSE = [
    (r"Indian Institute of Science Education and Research,? (\w+)", "IISc · TIFR · IISER", "IISER {}"),
    (r"^Indian Institute of Science$|Indian Institute of Science Bangalore", "IISc · TIFR · IISER", "IISc"),
    (r"Tata Institute of Fundamental Research", "IISc · TIFR · IISER", "TIFR"),
    (r"Indian Institute of Technology \(BHU\)|Indian Institute of Technology BHU", "IIT", "IIT BHU"),
    (r"Indian Institute of Technology,? (\w+)", "IIT", "IIT {}"),
    (r"Indraprastha Institute of Information Technology", "IIIT", "IIIT Delhi"),
    (r"International Institute of Information Technology,? (\w+)", "IIIT", "IIIT {}"),
    (r"Atal Bihari Vajpayee Indian Institute of Information Technology", "IIIT", "ABV-IIITM Gwalior"),
    (r"Indian Institute of Information Technology.*?(\w+)$", "IIIT", "IIIT {}"),
    (r"PDPM", "IIIT", "IIITDM Jabalpur"),
    (r"Maulana Azad National Institute of Technology", "NIT", "MANIT Bhopal"),
    (r"National Institute of Technology,? (\w+)", "NIT", "NIT {}"),
    (r"Jawaharlal Nehru University", "Central University", "JNU"),
    (r"University of Hyderabad", "Central University", "HCU"),
    (r"^University of Delhi", "Central University", "DU"),
    (r"^Banaras Hindu University", "Central University", "BHU"),
    (r"Jadavpur University", "Central University", "Jadavpur"),
    (r"Jamia Millia Islamia", "Central University", "JMI"),
    (r"Indian Statistical Institute", "Premier Science", "ISI"),
    (r"Institute of Mathematical Sciences", "Premier Science", "IMSc"),
    (r"Chennai Mathematical Institute", "Premier Science", "CMI"),
    (r"Harish-Chandra Research Institute", "Premier Science", "HRI"),
    (r"National Centre for Biological Sciences", "Premier Science", "NCBS"),
    (r"S\. ?N\. Bose National Centre", "Premier Science", "SNBose"),
    (r"^Bose Institute", "Premier Science", "Bose Inst."),
    (r"Saha Institute of Nuclear Physics", "Premier Science", "SINP"),
    (r"Bhabha Atomic Research Centre", "DAE", "BARC"),
    (r"Indira Gandhi Centre for Atomic Research", "DAE", "IGCAR"),
    (r"Raja Ramanna Centre for Advanced Technology", "DAE", "RRCAT"),
    (r"National Institute of Science Education and Research", "DAE", "NISER"),
]
CSIR_LABS = {
    "National Chemical Laboratory": "CSIR-NCL", "Indian Institute of Chemical Technology": "CSIR-IICT",
    "Central Electrochemical Research": "CSIR-CECRI", "Central Food Technological": "CSIR-CFTRI",
    "National Institute for Interdisciplinary Science": "CSIR-NIIST", "National Metallurgical": "CSIR-NML",
    "National Physical Laboratory": "CSIR-NPL", "Central Scientific Instruments": "CSIR-CSIO",
    "Central Glass and Ceramic": "CSIR-CGCRI", "Central Mechanical Engineering": "CSIR-CMERI",
    "Central Road Research": "CSIR-CRRI", "Central Institute of Mining": "CSIR-CIMFR",
    "Central Building Research": "CSIR-CBRI", "Central Electronics Engineering": "CSIR-CEERI",
    "Structural Engineering Research": "CSIR-SERC", "Advanced Materials and Processes": "CSIR-AMPRI",
    "Centre for Cellular and Molecular Biology": "CSIR-CCMB", "Institute of Genomics and Integrative": "CSIR-IGIB",
    "Institute of Microbial Technology": "CSIR-IMTECH", "Central Drug Research": "CSIR-CDRI",
}


COURSE_SHORT = {
    "IIT Bombay", "IIT Madras", "IIT Delhi", "IIT Kanpur", "IIT Kharagpur", "IIT Roorkee", "IIT Guwahati",
    "IIT Hyderabad", "IIT Gandhinagar", "IIT Jodhpur", "IIT Patna", "IIT BHU", "IIT Indore", "IIT Mandi",
    "IIT Bhubaneswar", "IIT Tirupati", "IIT Jammu", "IIT Goa", "IIT Palakkad", "IIT Dharwad", "IIT Bhilai",
    "IIIT Hyderabad", "IIIT Delhi", "IIIT Allahabad", "IIIT Bangalore", "ABV-IIITM Gwalior", "IIIT Jabalpur",
    "IIIT Pune", "IIIT Kancheepuram", "NIT Tiruchirappalli", "NIT Karnataka", "NIT Warangal", "NIT Rourkela",
    "NIT Calicut", "NIT Kurukshetra", "NIT Durgapur", "MANIT Bhopal", "NIT Jamshedpur", "NIT Silchar",
    "JNU", "HCU", "DU", "BHU", "Jadavpur", "JMI", "IISc", "TIFR", "IISER Pune", "IISER Kolkata", "IISER Bhopal",
    "IISER Mohali", "IISER Thiruvananthapuram", "ISI", "IMSc", "CMI", "HRI", "NCBS", "SNBose", "Bose Inst.",
    "SINP", "BARC", "IGCAR", "RRCAT", "NISER", *CSIR_LABS.values(),
}


def classify(rec: dict, parents: list[str]) -> tuple[str, str, bool]:
    name = rec["display_name"]
    for pat, cluster, short_tpl in COURSE:
        if m := re.search(pat, name):
            return cluster, short_tpl.format(*m.groups()), True
    for key, s in CSIR_LABS.items():
        if key in name:
            return "CSIR", s, True
    lineage = " ".join(parents)
    if "Council of Scientific and Industrial Research" in lineage + name or "Academy of Scientific and Innovative Research" in name:
        return "CSIR", name, False
    if "Department of Atomic Energy" in lineage + name or "Homi Bhabha National Institute" in name:
        return "DAE", name, False
    if re.search(r"Indian Institute of Technology", name):
        return "IIT", name, False
    if re.search(r"National Institute of Technology", name):
        return "NIT", name, False
    t = rec.get("type")
    if t == "education":
        return "University / College", name, False
    if t in ("facility", "government", "nonprofit", "archive"):
        return "Other research institute", name, False
    if t == "healthcare":
        return "Healthcare", name, False
    if t == "company":
        return "Industry", name, False
    return "Other", name, False


def main() -> None:
    con = duckdb.connect()
    ids = [r[0] for r in con.sql("""
        SELECT DISTINCT inst_id FROM (
          SELECT inst_id, country FROM 'data/stage/authorships.parquet'
          UNION ALL SELECT inst_id, country FROM 'data/stage/link_insts.parquet')
        WHERE country = 'IN' AND inst_id IS NOT NULL""").fetchall()]
    print(f"{len(ids)} Indian institutions")
    recs = {}
    for b in chunks(ids, 100):
        for r in get("/institutions", {"filter": f"openalex_id:{'|'.join(b)}", "per-page": 100,
                                       "select": "id,display_name,ror,type,lineage"})["results"]:
            recs[short(r["id"])] = r
    parent_ids = {short(p) for r in recs.values() for p in r.get("lineage") or []} - recs.keys()
    names = {k: r["display_name"] for k, r in recs.items()}
    for b in chunks(sorted(parent_ids), 100):
        for r in get("/institutions", {"filter": f"openalex_id:{'|'.join(b)}", "per-page": 100,
                                       "select": "id,display_name"})["results"]:
            names[short(r["id"])] = r["display_name"]

    rows = []
    for k, r in recs.items():
        parents = [names.get(short(p), "") for p in r.get("lineage") or [] if short(p) != k]
        cluster, sname, _ = classify(r, parents)
        course = sname in COURSE_SHORT
        rows.append({"inst_id": k, "name": r["display_name"], "ror": r.get("ror") or "",
                     "type": r.get("type") or "", "cluster": cluster, "short_name": sname,
                     "course_inst": course})
    rows.sort(key=lambda r: (r["cluster"], r["name"]))
    with (ROOT / "ref" / "institutions.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter(r["cluster"] for r in rows).most_common())


if __name__ == "__main__":
    main()
