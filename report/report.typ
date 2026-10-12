// DPCN 2026 · Group 19 statistics report (≤ 5 pages). Built by `make report`:
// pipeline/report.py writes data.json, then typst compiles this file.
#import "@preview/lilaq:0.6.0" as lq

#let d = json("data.json")
#let pune = rgb("#2a78d6")
#let kol = rgb("#eb6834")
#let grey = rgb("#898781")
#let ic(i) = if i == "IISER Pune" { pune } else { kol }
#let pct(x) = if x == none { "—" } else { str(calc.round(x * 100, digits: 1)) + "%" }
#let num(x) = {
  let s = str(x)
  let out = ""
  let n = s.len()
  for (i, c) in s.clusters().enumerate() {
    if i > 0 and calc.rem(n - i, 3) == 0 { out += "," }
    out += c
  }
  out
}
#let r3(x) = if x == none { "—" } else { str(calc.round(float(x), digits: 3)) }
#let trunc(s, n) = if s.clusters().len() > n { s.clusters().slice(0, n).join() + "…" } else { s }

#set document(title: "citeGraph — Group 19 statistics report", author: "DPCN Group 19")
#set page(paper: "a4", margin: (x: 1.6cm, y: 1.5cm), numbering: "1 / 1",
  header: context if counter(page).get().first() > 1 [#set text(8pt, fill: grey); DPCN 2026 · Group 19 · IISER Pune & IISER Kolkata #h(1fr) statistics report])
#set text(font: ("Libertinus Serif", "New Computer Modern"), size: 9.5pt)
#set par(justify: true, leading: 0.55em)
#show heading.where(level: 1): it => block(above: 1em, below: 0.5em, text(12pt, weight: "bold", it.body))
#show heading.where(level: 2): it => block(above: 0.8em, below: 0.4em, text(10pt, weight: "bold", it.body))
#set table(stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { (bottom: 0.2pt + luma(220)) }, inset: (x: 4pt, y: 2.6pt))
#show table: set text(8pt)
#show table.cell.where(y: 0): set text(weight: "bold")

#align(center)[
  #text(16pt, weight: "bold")[Research mapping: IISER Pune & IISER Kolkata, 2016–2026] \
  #v(2pt)
  #text(10pt)[DPCN course project · Group 19 · statistics report] \
  #text(8.5pt, fill: grey)[Data: OpenAlex (snapshot Oct 2026), SCImago journal ranks. Interactive dashboard and all CSVs accompany this report.]
]

= 1 · Dataset and headline numbers

The dataset covers every paper by a *current regular faculty member* written while affiliated with the institute (regular-faculty rosters scraped from both websites, matched to OpenAlex author profiles). Rows are faculty × paper; all statistics below count distinct papers. Papers with ≥100 authors (big-collaboration physics, mainly CMS) are kept but flagged, because OpenAlex truncates their author lists.

#let kp = d.kpi
#let fa = d.faculty
#table(columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr), align: (left, right, right, right, right, right, right, right),
  table.header[Institute][Faculty (with papers)][Papers][Citations][≥100-author papers][Q1 share][median h (2016–26)][median h (lifetime)],
  ..kp.enumerate().map(((i, k)) => {
    let f = fa.at(i)
    (k.institution, [#f.n (#f.active)], num(k.papers), num(k.citations), num(k.hyper),
     if k.q1_share == none [n/a#super[†]] else { pct(k.q1_share) }, str(f.med_h), str(f.med_h_life))
  }).flatten()
)
#if kp.at(0).q1_share == none [#text(8pt, fill: grey)[† SCImago quartile files not yet added to `ref/scimago/`; the quartile column is filled automatically on the next `make data`.]]

#grid(columns: (1fr, 1fr), gutter: 12pt,
  [
    == Publication trend
    #let years = range(2016, 2027)
    #let ser(i) = years.map(y => { let r = d.trend.filter(t => t.institution == i and t.year == y); if r.len() > 0 { r.at(0).n } else { 0 } })
    #lq.diagram(width: 100%, height: 4.6cm, xlabel: none, ylabel: [papers per year],
      xaxis: (ticks: years.map(y => (y, text(7pt, str(y)))), subticks: none),
      legend: (position: top + left),
      lq.plot(years, ser("IISER Pune"), color: pune, label: [IISER Pune], mark-size: 4pt),
      lq.plot(years, ser("IISER Kolkata"), color: kol, label: [IISER Kolkata], mark-size: 4pt))
    #text(7.5pt, fill: grey)[2026 is partial (data collected October 2026).]
  ],
  [
    == h-index distribution of faculty (2016–26 window)
    #let bins = range(0, 44, step: 4)
    #let hs(i) = bins.map(b => { let r = d.hist.filter(t => t.institution == i and t.bin == b); if r.len() > 0 { r.at(0).n } else { 0 } })
    #lq.diagram(width: 100%, height: 4.6cm, xlabel: [h-index (bins of 4; last bin ≥ 40)], ylabel: [faculty],
      legend: (position: top + right),
      lq.bar(bins, hs("IISER Pune"), offset: -0.9, width: 1.7, fill: pune, label: [IISER Pune]),
      lq.bar(bins, hs("IISER Kolkata"), offset: 0.9, width: 1.7, fill: kol, label: [IISER Kolkata]))
  ]
)

#grid(columns: (1fr, 1fr), gutter: 12pt,
  [
    == Top 5 journals per institute
    #table(columns: (auto, 1fr, auto), align: (left, left, right),
      table.header[Institute][Journal][Papers],
      ..d.journals.map(j => (j.institution.replace("IISER ", ""), trunc(j.journal_name, 48), str(j.n))).flatten())
  ],
  [
    == Research area breakdown (top 8 OpenAlex fields)
    #table(columns: (1fr, auto, auto), align: (left, right, right),
      table.header[Field][Pune][Kolkata],
      ..{
        let fields = d.fields.map(f => f.field).dedup()
        fields.map(fl => {
          let g(i) = { let r = d.fields.filter(f => f.institution == i and f.field == fl); if r.len() > 0 { pct(r.at(0).share) } else { "—" } }
          (trunc(fl, 42), g("IISER Pune"), g("IISER Kolkata"))
        }).flatten()
      })
  ]
)

#let qs = d.quartiles
#if qs.any(q => q.q != "unranked") [
  == Journal quartile distribution
  #table(columns: 6, table.header[Institute][Q1][Q2][Q3][Q4][unranked],
    ..("IISER Pune", "IISER Kolkata").map(i => {
      let tot = qs.filter(q => q.institution == i).map(q => q.n).sum()
      (i, ..("Q1", "Q2", "Q3", "Q4", "unranked").map(k => { let r = qs.filter(q => q.institution == i and q.q == k); pct(if r.len() > 0 { r.at(0).n / tot } else { 0 }) }))
    }).flatten())
]

== Most-cited papers (top 10, excluding ≥100-author collaboration papers)
#table(columns: (1fr, auto, auto, auto, auto), align: (left, left, right, right, left),
  table.header[Title][Journal][Year][Citations][Institute],
  ..d.top_cited.map(p => (
    if p.doi != none { link(p.doi, trunc(p.title, 85)) } else { trunc(p.title, 85) },
    trunc(p.journal, 30), str(p.year), num(p.citations), p.inst.replace("IISER ", ""))).flatten())
#text(7.5pt, fill: grey)[Including collaboration papers, the most-cited paper has #num(d.top_cited_hyper.at(0).c) citations (CMS); such papers would occupy the whole list.]

= 2 · Citation network (within the two institutes)

#let C = d.net.citation
#let S = C.summary
Directed graph: node = corpus paper, edge A→B = A cites B, both endpoints in the corpus. *#num(S.nodes) nodes, #num(S.edges) edges*, density #S.density, mean degree #S.mean_degree. The largest weakly-connected component holds #pct(S.giant_share) of the papers; #num(S.isolates) papers cite and are cited by no other corpus paper. Transitivity #S.transitivity, average shortest path in the giant component #S.avg_path_gcc (diameter #S.diameter_gcc), degree assortativity #S.assortativity_degree. A discrete power-law fit to the in-degree tail gives α = #C.powerlaw_indegree.alpha for $k >= #C.powerlaw_indegree.xmin$ (n#sub[tail] = #C.powerlaw_indegree.n_tail, KS D = #C.powerlaw_indegree.ks_D), a heavy tail typical of citation networks (note the tail is short).

#grid(columns: (1.45fr, 1fr), gutter: 12pt,
  [
    == PageRank top 10 (damping 0.85, ≥100-author papers removed)
    #table(columns: (1fr, auto, auto, auto), align: (left, left, right, right),
      table.header[Paper][Inst.][Year][In-deg.],
      ..C.top_pagerank_excl_hyper.map(p => (trunc(p.title, 62), p.inst.replace("IISER ", ""), str(p.year), str(p.indeg))).flatten())
    #text(7.5pt, fill: grey)[With collaboration papers included, #C.top_pagerank.filter(p => p.hyperauthored).len() of the top 10 are CMS papers: they cite each other densely and absorb PageRank.]
  ],
  [
    == Cross-institute citation flow (India)
    #table(columns: (1fr, auto, auto, auto), align: (left, right, right, right),
      table.header[Institute][In-cites][Out-cites][In/Out],
      ..("IISER Pune", "IISER Kolkata").map(i => (i, num(C.flow_total.at(i).in), num(C.flow_total.at(i).out), str(C.flow_total.at(i).impact_ratio))).flatten())
    #let yrs = range(2016, 2027)
    #let fl(i, dir) = yrs.map(y => { let r = C.flow_year.filter(t => t.institution == i and t.year == y and t.direction == dir); if r.len() > 0 { r.at(0).citations } else { 0 } })
    #lq.diagram(width: 100%, height: 3.6cm, ylabel: [citations / year], legend: (position: top + left),
      xaxis: (ticks: yrs.filter(y => calc.rem(y, 2) == 0).map(y => (y, text(7pt, str(y)))), subticks: none),
      lq.plot(yrs, fl("IISER Pune", "in"), color: pune, label: [Pune in], mark-size: 3pt),
      lq.plot(yrs, fl("IISER Pune", "out"), color: pune, stroke: (dash: "dashed"), label: [Pune out], mark-size: 3pt),
      lq.plot(yrs, fl("IISER Kolkata", "in"), color: kol, label: [Kolkata in], mark-size: 3pt),
      lq.plot(yrs, fl("IISER Kolkata", "out"), color: kol, stroke: (dash: "dashed"), label: [Kolkata out], mark-size: 3pt))
    #text(7.5pt, fill: grey)[In = Indian papers (other institutes) citing ours, by citing year; out = ours citing Indian papers.]
    #v(4pt)
    *Top citing institutes:* #C.top_citing_institutes.filter(t => t.institution == "IISER Pune").slice(0, 4).map(t => t.partner).join(", ") (Pune); #C.top_citing_institutes.filter(t => t.institution == "IISER Kolkata").slice(0, 4).map(t => t.partner).join(", ") (Kolkata).
  ]
)

= 3 · Authorship network

#let F = d.net.coauthorship.G_fac.summary
#let I = d.net.coauthorship.G_ind.summary
The brief defines nodes as "faculty members" (instruction note §6b) but the slides say "authors", so we build both graphs. *G#sub[fac]*: only our faculty, linked when two of them co-author. *G#sub[ind]*: faculty plus their Indian co-authors at other institutions (students and postdocs at our own institutes are excluded). Edge weight is Newman's collaboration strength $sum 1/(n-1)$; papers with ≥100 authors are excluded from both graphs. Betweenness uses distance $1 slash w$. Communities: Leiden (modularity), cross-checked with Louvain.

#grid(columns: (1fr, 1.25fr), gutter: 12pt,
  [
    #table(columns: (1fr, auto, auto), align: (left, right, right),
      table.header[Metric][G#sub[fac]][G#sub[ind]],
      [Nodes / edges], [#F.nodes / #F.edges], [#num(I.nodes) / #num(I.edges)],
      [Isolated nodes], str(F.isolates), str(I.isolates),
      [Giant component], pct(F.giant_share), pct(I.giant_share),
      [Mean degree], str(F.mean_degree), str(I.mean_degree),
      [Transitivity], str(F.transitivity), str(I.transitivity),
      [Avg path (giant) / diameter], [#F.avg_path_gcc / #F.diameter_gcc], [#I.avg_path_gcc / #I.diameter_gcc],
      [Degree assortativity], str(F.assortativity_degree), str(I.assortativity_degree),
      [Leiden communities / Q], [#F.communities_leiden / #F.modularity_leiden], [#I.communities_leiden / #I.modularity_leiden],
      [NMI Leiden ↔ Louvain], str(F.nmi_leiden_louvain), str(I.nmi_leiden_louvain),
      [NMI communities ↔ department], str(F.nmi_community_department), str(I.nmi_community_department),
      [NMI communities ↔ institute], str(F.nmi_community_institute), str(I.nmi_community_institute),
    )
    Faculty rankings agree only moderately across the two graphs (Spearman ρ: degree #d.net.spearman_fac_vs_ind.degree, betweenness #d.net.spearman_fac_vs_ind.betweenness).
  ],
  [
    #table(columns: (1fr, auto, auto, auto), align: (left, left, right, right),
      table.header[Most collaborative (G#sub[fac] degree)][Dept.][Deg.][Comm.],
      ..d.top_deg.map(r => (r.name + " (" + r.inst.replace("IISER ", "") + ")", trunc(r.dept, 18), str(r.deg_fac), str(r.comm_fac))).flatten())
    #table(columns: (1fr, auto, auto, auto), align: (left, left, right, right),
      table.header[Top brokers (G#sub[ind] betweenness)][Dept.][Betw.][Partners],
      ..d.top_btw.map(r => (r.name + " (" + r.inst.replace("IISER ", "") + ")", trunc(r.dept, 18), r3(r.btw_ind), str(r.partner_insts_ind))).flatten())
  ]
)

*Reading.* Within-institute collaboration is sparse: #F.isolates of #F.nodes faculty have no co-authored paper with another IISER Pune/Kolkata faculty member, and G#sub[fac] fragments into #F.components components. Communities follow departments (NMI #F.nmi_community_department) far more than institutes. Adding the Indian co-authors joins #pct(I.giant_share) of nodes into one component and gives very high modularity (#I.modularity_leiden): collaboration is organised in lab-centred clusters that connect through a few brokers. *Hyperauthorship sensitivity:* #d.net.hyperauthorship.hyper_papers papers with ≥100 authors connect only #d.net.hyperauthorship.hyper_faculty_pairs faculty pairs, but with hundreds of shared papers each. Counted naively, they would dominate collaboration strength, which is why they are down-weighted, and here excluded.

= 4 · Indian connectivity

#table(columns: (auto, 1fr, auto, auto, auto, auto, auto), align: (left, left, left, right, right, right, right),
  table.header[Institute][Top co-author partners][Cluster][Joint papers][Cites in][Cites out][Topic Jaccard],
  ..d.partners.map(p => (p.your_inst.replace("IISER ", ""), p.partner_inst, p.partner_cluster, str(p.shared_papers), str(p.cites_in), str(p.cites_out), r3(p.jaccard_topics))).flatten())

Strongest partners are other premier science institutions (TIFR, IISc, other IISERs). The leading cross-cluster links are IISER ↔ CSIR (CSIR-NCL, adjacent to IISER Pune), IISER ↔ IIT (IIT Bombay, IIT Kharagpur, IIT Madras) and IISER ↔ DAE (HBNI). Topic Jaccard is computed over the OpenAlex subfields that each make up ≥ 0.5% of an institution's 2016–26 output.

#v(4pt)
#text(7.5pt, fill: grey)[*Method notes.* Kept work types: article, review, letter, conference paper (preprints, datasets, errata dropped). Duplicate records (same DOI or normalised title + year) merged. Quartile = SCImago best quartile, nearest year not after publication. h-index (2016–26) is computed from this corpus; lifetime h-index is OpenAlex's. Indian links come from OpenAlex `cites:`/`cited_by:` queries restricted to works with an Indian affiliation; "other institute" excludes the paper's own institute. Full pipeline and decisions: dashboard → Methods & data.]
