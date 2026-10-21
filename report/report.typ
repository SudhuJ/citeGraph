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

The dataset covers every paper by a *current regular faculty member* written while affiliated with the institute (regular-faculty rosters scraped from both websites, matched to OpenAlex author profiles). Rows are faculty × paper; all statistics below count distinct papers. Papers with ≥100 authors (big-collaboration physics, almost all from two CMS members at IISER Pune) are counted in the table below but left out of every other statistic: OpenAlex truncates their author lists, and they would make up 27% of Pune's output.

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
#text(7.5pt, fill: grey)[Coverage: #d.coverage.at(0).matched of #d.coverage.at(0).faculty roster faculty matched to OpenAlex; #d.coverage.at(0).publishing have papers in the window.]

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
#let trendval(i, y, key) = {
  let r = d.trend.filter(t => t.institution == i and t.year == y)
  if r.len() > 0 { r.at(0).at(key) } else { 0 }
}
#text(7.5pt, fill: grey)[From 2016 to 2025, output grew #pct(trendval("IISER Pune", 2025, "n") / trendval("IISER Pune", 2016, "n") - 1) at Pune and #pct(trendval("IISER Kolkata", 2025, "n") / trendval("IISER Kolkata", 2016, "n") - 1) at Kolkata. Per active faculty, it changed #pct(trendval("IISER Pune", 2025, "per_faculty") / trendval("IISER Pune", 2016, "per_faculty") - 1) and #pct(trendval("IISER Kolkata", 2025, "per_faculty") / trendval("IISER Kolkata", 2016, "per_faculty") - 1), respectively: growth is not simply an increase in individual output. Active faculty are counted from their first paper in this current-faculty corpus; 2026 is partial.]

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

== Departments
#table(columns: (auto, 1fr, auto, auto, auto, auto), align: (left, left, right, right, right, right),
  table.header[Institute][Department][Faculty][Papers][Q1][Q1 & IF>5],
  ..d.depts.map(r => (r.institution.replace("IISER ", ""), trunc(r.department, 40), str(r.faculty), num(r.papers), pct(r.q1_share), pct(r.q1_if5_share))).flatten())
#text(7.5pt, fill: grey)[Shares of journal papers in SCImago-ranked venues. IF = SCImago citations per document over two years, an open stand-in for the impact factor.]

== Most-cited papers (top 10, excluding ≥100-author collaboration papers)
#table(columns: (1fr, auto, auto, auto, auto), align: (left, left, right, right, left),
  table.header[Title][Journal][Year][Citations][Institute],
  ..d.top_cited.map(p => (
    if p.doi != none { link(p.doi, trunc(p.title, 85)) } else { trunc(p.title, 85) },
    trunc(p.journal, 30), str(p.year), num(p.citations), p.inst.replace("IISER ", ""))).flatten())
#text(7.5pt, fill: grey)[Including collaboration papers, the most-cited paper has #num(d.top_cited_hyper.at(0).c) citations (CMS); such papers would occupy the whole list.]
#text(7.5pt, fill: grey)[Citation counts favour older work: #pct(d.top_cited_age.at(0).share_2016_2019) of the 30 most-cited non-hyperauthored papers were published in 2016–2019. Counts are OpenAlex totals at collection time (October 2026).]

= 2 · Citation network (within the two institutes)

#let C = d.net.citation
#let S = C.summary
Directed graph: node = corpus paper, edge A→B = A cites B, both endpoints in the corpus. *#num(S.nodes) nodes, #num(S.edges) edges*, density #S.density, mean degree #S.mean_degree. The largest weakly-connected component holds #pct(S.giant_share) of the papers; #num(S.isolates) papers cite and are cited by no other corpus paper. Transitivity #S.transitivity, average shortest path in the giant component #S.avg_path_gcc (diameter #S.diameter_gcc), degree assortativity #S.assortativity_degree. In-degree is heavy-tailed (a discrete power-law fit gives α = #C.powerlaw_indegree.alpha for $k >= #C.powerlaw_indegree.xmin$; without a goodness-of-fit test we do not claim a power law).

#let oin = d.origin.filter(o => o.direction == "in")
#let recv = oin.map(o => o.n).sum()
#let ours = oin.filter(o => o.from_ours).map(o => o.n).sum()
*Most citations within this network are self-citations.* Here, a self-citation means the citing and cited papers share an author. This differs from a citation by one of our papers, which only requires a faculty author from either institute.

Citations from our own papers account for #pct(ours / recv) of all citations our papers receive. Within the network, #pct(S.self_share) of citation links are self-citations; only #num(C.summary_excl_self.edges) connect papers by different people.

Of #d.faccit.faculty publishing faculty, #d.faccit.faculty_citing_colleagues cite a colleague's paper they did not author. #pct(1 - d.faccit.same_institute_share) of these colleague-citation links go between Pune and Kolkata. Only #pct(1 - d.facpairs.same_inst) of faculty coauthor links do. Faculty cite across institutes more often than they coauthor across them.
#let cited_by_others = C.indegree_hist_excl_self.filter(h => h.bin == "3–5" or h.bin == "6–10" or h.bin == "11+").map(h => h.papers).sum()
#text(7.5pt, fill: grey)[Non-self in-degree is sparse: only #num(cited_by_others) papers receive at least three citations from other people in this corpus.]
#text(7.5pt, fill: grey)[PageRank and in-degree rankings are only moderately aligned (Spearman ρ = #d.net.citation.pagerank_vs_indegree.spearman; #d.net.citation.pagerank_vs_indegree.top10_overlap papers appear in both top tens). With so few links, a handful of citations can change individual ranks.]

#let R = C.pagerank_vs_indegree
#grid(columns: (1.45fr, 1fr), gutter: 12pt,
  [
    #block(breakable: false)[
      == Top 10 by in-degree
      #table(columns: (1fr, auto, auto, auto), align: (left, left, right, right),
        table.header[Paper][Inst.][Year][In-deg.],
        ..C.top_indegree.enumerate().map(((rank, p)) => (str(rank + 1) + ". " + trunc(p.title, 64), p.inst.replace("IISER ", ""), str(p.year), str(p.indeg))).flatten())
      #v(4pt)
      == Top 10 by PageRank
      #table(columns: (1fr, auto, auto, auto), align: (left, left, right, right),
        table.header[Paper][Inst.][Year][PR score],
        ..C.top_pagerank.enumerate().map(((rank, p)) => (str(rank + 1) + ". " + trunc(p.title, 64), p.inst.replace("IISER ", ""), str(p.year), str(calc.round(p.pagerank, digits: 6)))).flatten())
    ]
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
    #text(7.5pt, fill: grey)[In = Indian papers (other institutes) citing ours, by citing year; out = ours citing Indian papers. Self-citations excluded. The ratio is biased below 1: references reach work of any year, citations only our 2016–26 papers.]
    #v(4pt)
    *Top citing institutes:* #C.top_citing_institutes.filter(t => t.institution == "IISER Pune").slice(0, 4).map(t => t.partner).join(", ") (Pune); #C.top_citing_institutes.filter(t => t.institution == "IISER Kolkata").slice(0, 4).map(t => t.partner).join(", ") (Kolkata).
  ]
)
#text(7.5pt, fill: grey)[In-degree counts citations from our papers by other people. PageRank uses damping 0.85 on the same graph. Among the #R.cited_papers papers cited at least once, rank correlation is ρ = #R.spearman and #R.top10_overlap papers appear in both top tens: with so few links, PageRank mostly reshuffles small counts.]

= 3 · Authorship network

#let F = d.net.coauthorship.G_fac.summary
#let I = d.net.coauthorship.G_ind.summary
The brief defines nodes as "faculty members" (instruction note §6b) but the slides say "authors", so we build both graphs. *G#sub[fac]* contains only our faculty, linked when two co-author a paper. *G#sub[ind]* adds their Indian co-authors at other institutions; students and postdocs at our own institutes are excluded. The network measures are defined as follows:
+ *Collaboration strength:* an edge has weight $w = sum_p 1/(n_p - 1)$ over papers shared by the pair, where $n_p$ is the paper's author count. Thus each co-author pair gets a smaller contribution from larger teams.
+ *Hyperauthorship exclusion:* papers with ≥100 authors are excluded from both graphs because OpenAlex truncates these author lists and they can dominate collaboration counts.
+ *Betweenness:* shortest paths use distance $1/w$, so stronger collaborations are shorter. A faculty member's betweenness is the share of shortest paths between other members that pass through them.
+ *Communities:* Leiden and Louvain both seek groups with more within-group edge weight than expected under a random graph (modularity). Leiden adds a refinement step and returns connected communities; Louvain alternates local node moves with graph aggregation and can produce less well-connected groups. Leiden is the primary result; Louvain is a cross-check.
+ *NMI:* normalized mutual information compares two community assignments. It ranges from 0 (little agreement) to 1 (identical assignments).

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
      [Leiden communities (2+) / Q], [#F.communities_leiden / #F.modularity_leiden], [#I.communities_leiden / #I.modularity_leiden],
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

*Reading.* Within-institute collaboration is sparse: #F.isolates of #F.nodes faculty have no co-authored paper with another IISER Pune/Kolkata faculty member, and G#sub[fac] fragments into #F.components components. Co-authorship stays inside each institute: #pct(d.facpairs.same_inst) of the #d.facpairs.links faculty–faculty links join two people at the same institute, while only #pct(d.facpairs.same_dept) join two people in the same department, so the communities are institute-bound but often span departments. (NMI ranks departments above institutes, #F.nmi_community_department vs #F.nmi_community_institute, largely because institute has just two values.) Adding the Indian co-authors joins #pct(I.giant_share) of nodes into one component and gives very high modularity (#I.modularity_leiden): collaboration is organised in lab-centred clusters that connect through a few brokers. *Hyperauthorship sensitivity:* #d.net.hyperauthorship.hyper_papers papers with ≥100 authors connect only #d.net.hyperauthorship.hyper_faculty_pairs faculty pairs, but with hundreds of shared papers each. Counted naively, they would dominate collaboration strength, which is why they are excluded.
#let s0 = d.net.snapshots.filter(s => s.graph == "G_fac").at(0)
#let s1 = d.net.snapshots.filter(s => s.graph == "G_fac").at(d.net.snapshots.filter(s => s.graph == "G_fac").len() - 1)
#text(7.5pt, fill: grey)[The faculty graph has grown more connected over time: its largest component rose from #pct(s0.giant_share) of faculty with papers through #s0.year to #pct(s1.giant_share) through #s1.year, as co-author links accumulated.]

= 4 · Indian connectivity

#table(columns: (auto, 1fr, auto, auto, auto, auto, auto), align: (left, left, left, right, right, right, right),
  table.header[Institute][Top co-author partners][Cluster][Joint papers][Cites in][Cites out][Topic Jaccard],
  ..d.partners.map(p => (p.your_inst.replace("IISER ", ""), p.partner_inst, p.partner_cluster, str(p.shared_papers), str(p.cites_in), str(p.cites_out), r3(p.jaccard_topics))).flatten())

#let cats = ("self", "own institute", "other Indian only", "India + abroad", "abroad or unknown")
#let osh(i, dir, c) = {
  let r = d.origin.filter(o => o.institution == i and o.direction == dir)
  let tot = r.map(o => o.n).sum()
  pct(r.filter(o => o.category == c).map(o => o.n).sum(default: 0) / tot)
}
*Who cites us, and whom we cite* (share of citation links; first matching category):
#table(columns: (auto, auto, 1fr, 1fr, 1fr, 1fr, 1fr), align: (left, left, right, right, right, right, right),
  table.header[Institute][Direction][Self][Same IISER][Other Indian][India + abroad][No Indian author / unknown],
  ..("IISER Pune", "IISER Kolkata").map(i => ("in", "out").map(dir => (i.replace("IISER ", ""), if dir == "in" [cited by] else [citing], ..cats.map(c => osh(i, dir, c)))).flatten()).flatten())

Nearby institutions rank high: CSIR-NCL and Savitribai Phule Pune University for Pune, IIT Kharagpur for Kolkata. The other strong partners are premier science institutes (TIFR, IISc, IISER Bhopal). HBNI and AcSIR are umbrella bodies that overlap with the DAE and CSIR labs they cover. #pct(d.partner_summary.at(0).cross_cluster_share) of joint papers are with partners outside the IISc · TIFR · IISER cluster. Two-thirds or more of our citations come from papers with no Indian author or unknown affiliations. Self-citations here count any citing paper that shares an author with ours, from inside our corpus or outside it, which is why their share of all citations (#osh("IISER Pune", "in", "self") for Pune, #osh("IISER Kolkata", "in", "self") for Kolkata) is far below the 96% inside the citation network. Topic Jaccard is computed over the OpenAlex subfields that each make up ≥ 0.5% of an institution's 2016–26 output.
#let tc = d.topic_collaboration.at(0)
#text(7.5pt, fill: grey)[Among #tc.n institute–partner pairs with at least three joint papers and available topic profiles, topic similarity and collaboration volume have Spearman ρ = #r3(tc.spearman): overlap explains only part of who writes with whom.]

#v(4pt)
#text(7.5pt, fill: grey)[*Method notes.* Kept work types: article, review, letter, conference paper (preprints, datasets, errata dropped). Duplicate records (same DOI or normalised title + year) merged. Quartile = SCImago best quartile, nearest year not after publication. h-index (2016–26) is computed from this corpus; lifetime h-index is OpenAlex's. Indian links come from OpenAlex `cites:`/`cited_by:` queries restricted to works with an Indian affiliation; "other institute" excludes the paper's own institute. Full pipeline and decisions: dashboard → Methods & data.]
