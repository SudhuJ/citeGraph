"""Scrape the regular-faculty rosters of IISER Pune and IISER Kolkata.

Output: data/faculty_seed.csv  (institution, name, designation, department, joint_departments, profile_url)
Visiting / adjunct / emeritus / honorary faculty are deliberately excluded.
"""

import csv
import re

import httpx
from oa import ROOT
from selectolax.lexbor import LexborHTMLParser

UA = {"User-Agent": "Mozilla/5.0 (citeGraph course project)"}
PUNE = "https://www.iiserpune.ac.in/institute/people/faculty/regular-faculty"
KOL = "https://www.iiserkol.ac.in/web/faculty/{}"
KOL_DEPTS = {
    "biological-sciences": "Biological Sciences",
    "chemical-sciences": "Chemical Sciences",
    "computational-data-sciences": "Computational and Data Sciences",
    "earth-sciences": "Earth Sciences",
    "humanities-social-sciences": "Humanities and Social Sciences",
    "mathematics-and-statistics": "Mathematics and Statistics",
    "physical-sciences": "Physical Sciences",
}


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def pune(client: httpx.Client) -> list[dict]:
    html = LexborHTMLParser(client.get(PUNE).text)
    rows = []
    for card in html.css("article.person-card"):
        a = card.css_first("h4 a")
        depts = [clean(s.text()) for s in card.css("p.apply-department-seperator span")]
        depts = [d for d in depts if d]
        rows.append({
            "institution": "IISER Pune",
            "name": clean(a.text()),
            "designation": clean(card.css_first("p[itemprop=jobTitle]").text()),
            "department": depts[0].replace(" (Joint)", "") if depts else "",
            "joint_departments": ";".join(d.replace(" (Joint)", "") for d in depts[1:]),
            "profile_url": "https://www.iiserpune.ac.in" + a.attributes["href"],
        })
    return rows


def kolkata(client: httpx.Client) -> list[dict]:
    by_url: dict[str, dict] = {}
    for slug, dept in KOL_DEPTS.items():
        html = LexborHTMLParser(client.get(KOL.format(slug)).text)
        for card in html.css("div.card-body"):
            title, link = card.css_first("h6.card-title"), card.css_first("a[href*=faculty-details]")
            if not (title and link):
                continue
            url = link.attributes["href"]
            if url in by_url:  # listed under a second department
                j = by_url[url]["joint_departments"]
                by_url[url]["joint_departments"] = ";".join(filter(None, [j, dept]))
                continue
            desig = card.css_first("p.text-muted")
            by_url[url] = {
                "institution": "IISER Kolkata",
                "name": clean(title.text()),
                "designation": clean(desig.text()) if desig else "",
                "department": dept,
                "joint_departments": "",
                "profile_url": url,
            }
    return list(by_url.values())


def main() -> None:
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        rows = pune(c) + kolkata(c)
    out = ROOT / "data" / "faculty_seed.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for inst in ("IISER Pune", "IISER Kolkata"):
        print(f"{inst}: {sum(r['institution'] == inst for r in rows)} faculty")
    print(f"-> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
