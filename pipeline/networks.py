"""Network analysis (igraph) → dashboard/src/data/*.json and data/out/network_*.csv

G_cit     directed citation graph on the corpus (internal edges only, §6a "within")
G_cit_ns  the same without author self-citations (the two papers share an author)
G_faccit  faculty -> faculty citations between different people (knowledge flow between groups)
G_fac     faculty-only co-authorship graph (strict §6b)
G_ind     faculty + Indian co-authors (connectivity, §7b)
Hyperauthored papers (>=100 authors, truncated lists) are excluded from every graph;
G_fac_hyper re-adds them to show how much they would distort the picture.
"""

import json
import math
import random
from collections import Counter, defaultdict

import duckdb
import igraph as ig
from oa import ROOT

OUT = ROOT / "dashboard" / "src" / "data"
random.seed(19)


def rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return cov / (va * vb) if va and vb else float("nan")


def ccdf(values):
    c = Counter(v for v in values if v > 0)
    n, acc, out = sum(c.values()), 0, []
    for k in sorted(c, reverse=True):
        acc += c[k]
        out.append({"k": k, "p": acc / n})
    return sorted(out, key=lambda d: d["k"])


def powerlaw(values):
    vals = [v for v in values if v > 0]
    if len(vals) < 50:
        return None
    f = ig.power_law_fit(vals, method="discrete")
    return {"alpha": round(f.alpha, 3), "xmin": f.xmin, "ks_D": round(f.D, 4),
            "n_tail": sum(v >= f.xmin for v in vals)}


def summary(g: ig.Graph, weights=None) -> dict:
    comps = g.connected_components(mode="weak") if g.is_directed() else g.connected_components()
    gcc = comps.giant()
    und = gcc.as_undirected() if g.is_directed() else gcc
    s = {
        "nodes": g.vcount(), "edges": g.ecount(), "density": round(g.density(), 6),
        "components": len(comps), "giant_share": round(gcc.vcount() / max(g.vcount(), 1), 3),
        "isolates": sum(d == 0 for d in g.degree()),
        "mean_degree": round(2 * g.ecount() / max(g.vcount(), 1), 2),
        "transitivity": round(und.transitivity_undirected(), 3),
        "avg_clustering": round(und.transitivity_avglocal_undirected(mode="zero"), 3),
        "assortativity_degree": round(g.assortativity_degree(directed=g.is_directed()), 3),
    }
    if und.vcount() <= 20000:
        s["avg_path_gcc"] = round(und.average_path_length(), 2)
        s["diameter_gcc"] = und.diameter()
    return s


def layout(g: ig.Graph, weights=None):
    und = g.as_undirected(combine_edges="sum") if g.is_directed() else g
    lay = und.layout_drl(weights=weights) if g.vcount() > 1500 else und.layout_fruchterman_reingold(weights=weights, niter=1500)
    xs, ys = zip(*lay.coords) if g.vcount() else ((), ())
    mx, my = (min(xs), max(xs)), (min(ys), max(ys))
    sx, sy = (mx[1] - mx[0]) or 1, (my[1] - my[0]) or 1
    return [((x - mx[0]) / sx * 1000, (y - my[0]) / sy * 1000) for x, y in lay.coords]


def coauthor_graph(rows, node_info):
    """rows: (node_a, node_b, n_authors, work_id) -> weighted undirected graph.
    weight = Newman's collaboration strength sum 1/(n-1); papers = co-authored count."""
    w, papers = defaultdict(float), defaultdict(int)
    for a, b, n, _ in rows:
        key = (a, b) if a < b else (b, a)
        w[key] += 1 / max(n - 1, 1)
        papers[key] += 1
    names = sorted(node_info)
    idx = {n: i for i, n in enumerate(names)}
    g = ig.Graph(n=len(names), edges=[(idx[a], idx[b]) for a, b in w])
    g.vs["name"] = names
    g.es["weight"] = list(w.values())
    g.es["papers"] = [papers[k] for k in w]
    for key in next(iter(node_info.values())):
        g.vs[key] = [node_info[n][key] for n in names]
    return g


def n_groups(membership, min_size=2):
    """Communities with at least min_size members (isolated nodes are singleton communities)."""
    return sum(n >= min_size for n in Counter(membership).values())


def communities(g: ig.Graph):
    leiden = g.community_leiden(objective_function="modularity", weights="weight", n_iterations=-1, resolution=1.0)
    louvain = g.community_multilevel(weights="weight")
    return leiden, louvain


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / "data" / "citegraph.duckdb"), read_only=True)
    q = lambda s: con.sql(s).fetchall()

    # =============================== citation network ===================================
    nodes = q("""SELECT w.work_id, wi.our_insts, w.year, w.title, w.doi, w.cited_by_count, w.field,
                        w.source_name, w.n_authors
                 FROM corpus w JOIN work_inst wi USING (work_id) WHERE w.n_authors < 100 ORDER BY 1""")
    idx = {r[0]: i for i, r in enumerate(nodes)}
    int_rows = q("""SELECT DISTINCT source_id, target_id, self_citation FROM cit_edges
                    WHERE edge_kind = 'internal' AND NOT involves_hyper""")
    edges = [(idx[s], idx[t]) for s, t, _ in int_rows]
    is_self = [bool(x) for _, _, x in int_rows]
    gc = ig.Graph(n=len(nodes), edges=edges, directed=True)
    gc.es["self"] = is_self
    indeg = gc.indegree()
    outdeg = gc.outdegree()
    pr_self = gc.pagerank(directed=True, damping=0.85)
    cit_sum = summary(gc)
    cit_sum["reciprocal_share"] = round(gc.reciprocity(), 4)
    cit_sum["self_share"] = round(sum(is_self) / max(len(is_self), 1), 3)
    # without self-citations: what is left is one group building on another group's work
    gc_ns = ig.Graph(n=len(nodes), edges=[e for e, x in zip(edges, is_self) if not x], directed=True)
    indeg_ns = gc_ns.indegree()
    pr = gc_ns.pagerank(directed=True, damping=0.85)
    cit_sum_ns = summary(gc_ns)

    # cross-institute flow (institution level), year-wise: Indian citations from / to other
    # institutes, author self-citations excluded (full breakdown: citation_origin in export.py)
    flow_year = [dict(zip(["institution", "year", "direction", "citations"], r)) for r in q("""
        SELECT fw.institution, lw.year, 'in', count(DISTINCT (e.source_id, e.target_id))
        FROM cit_edges e JOIN (SELECT DISTINCT work_id, institution, inst_id FROM fac_work) fw ON fw.work_id = e.target_id
        JOIN 'data/stage/link_works.parquet' lw ON lw.link_id = e.source_id AND lw.kind = 'citing'
        WHERE e.edge_kind = 'in' AND NOT e.self_citation AND NOT e.involves_hyper
          AND EXISTS (SELECT 1 FROM link_inst li WHERE li.link_id = e.source_id AND li.inst_id <> fw.inst_id)
          AND lw.year BETWEEN 2016 AND 2026
        GROUP BY ALL
        UNION ALL
        SELECT fw.institution, w.year, 'out', count(DISTINCT (e.source_id, e.target_id))
        FROM cit_edges e JOIN (SELECT DISTINCT work_id, institution, inst_id FROM fac_work) fw ON fw.work_id = e.source_id
        JOIN corpus w ON w.work_id = e.source_id
        WHERE e.edge_kind = 'out' AND NOT e.self_citation AND NOT e.involves_hyper AND EXISTS (SELECT 1 FROM link_inst li WHERE li.link_id = e.target_id AND li.inst_id <> fw.inst_id)
        GROUP BY ALL ORDER BY 1, 2, 3""")]
    flow_tot = {}
    for r in flow_year:
        d = flow_tot.setdefault(r["institution"], {"in": 0, "out": 0})
        d[r["direction"]] += r["citations"]
    for d in flow_tot.values():
        d["impact_ratio"] = round(d["in"] / d["out"], 3) if d["out"] else None
    top_citing = [dict(zip(["institution", "partner", "cluster", "citations"], r)) for r in q("""
        SELECT your_inst, partner_inst, partner_cluster, cites_in FROM connections
        QUALIFY row_number() OVER (PARTITION BY your_inst ORDER BY cites_in DESC) <= 10
        ORDER BY your_inst, cites_in DESC""")]
    # top-10 Indian papers citing each institute's work (by how many corpus papers they cite)
    top_citing_papers = [dict(zip(["institution", "title", "year", "doi", "corpus_papers_cited", "insts"], r)) for r in q("""
        SELECT fw.institution, any_value(lw.title), any_value(lw.year), any_value(lw.doi),
               count(DISTINCT e.target_id) AS n, any_value(nm.insts)
        FROM cit_edges e JOIN (SELECT DISTINCT work_id, institution FROM fac_work) fw ON fw.work_id = e.target_id
        JOIN 'data/stage/link_works.parquet' lw ON lw.link_id = e.source_id AND lw.kind = 'citing'
        LEFT JOIN node_meta nm ON nm.id = e.source_id
        WHERE e.edge_kind = 'in' AND NOT e.self_citation AND NOT e.involves_hyper
        GROUP BY fw.institution, e.source_id
        QUALIFY row_number() OVER (PARTITION BY fw.institution ORDER BY n DESC) <= 10
        ORDER BY 1, n DESC""")]

    # visual: largest weakly-connected component, sized by PageRank
    comp = gc.connected_components(mode="weak")
    giant = max(range(len(comp)), key=lambda c: len(comp[c]))
    keep = comp[giant]
    sub = gc.subgraph(keep)
    pos = layout(sub)
    cit_nodes = []
    for j, i in enumerate(keep):
        w = nodes[i]
        cit_nodes.append({"id": w[0], "x": round(pos[j][0], 1), "y": round(pos[j][1], 1), "inst": w[1],
                          "year": w[2], "title": w[3], "doi": w[4], "cites": w[5], "field": w[6],
                          "venue": w[7], "indeg": indeg[i], "indeg_ns": indeg_ns[i], "outdeg": outdeg[i], "pr": pr[i]})
    cit_graph = {"nodes": cit_nodes,
                 "edges": [[sub.vs[e.source].index, sub.vs[e.target].index, int(e["self"])] for e in sub.es]}
    def top10(scores, deg):
        return [{"title": nodes[i][3], "inst": nodes[i][1], "year": nodes[i][2], "doi": nodes[i][4],
                 "pagerank": round(scores[i], 6), "indeg": deg[i], "cites_total": nodes[i][5]}
                for i in sorted(range(len(nodes)), key=lambda i: -scores[i])[:10]]
    cit_top = top10(pr, indeg_ns)
    cit_top_self = top10(pr_self, indeg)
    # in-degree first: with so few non-self edges, a plain count is the clearest ranking;
    # PageRank is reported beside it, with how far the two agree
    pr_rank = {i: r + 1 for r, i in enumerate(sorted(range(len(nodes)), key=lambda i: -pr[i]))}
    top_in = sorted(range(len(nodes)), key=lambda i: (-indeg_ns[i], -pr[i]))[:10]
    cit_top_indeg = [{"title": nodes[i][3], "inst": nodes[i][1], "year": nodes[i][2], "doi": nodes[i][4],
                      "indeg": indeg_ns[i], "pagerank": round(pr[i], 6), "pr_rank": pr_rank[i], "cites_total": nodes[i][5]}
                     for i in top_in]
    cited_ns = [i for i in range(len(nodes)) if indeg_ns[i] > 0]
    pr_vs_indeg = {"cited_papers": len(cited_ns),
                   "spearman": round(spearman([indeg_ns[i] for i in cited_ns], [pr[i] for i in cited_ns]), 3),
                   "top10_overlap": len(set(top_in) & set(sorted(range(len(nodes)), key=lambda i: -pr[i])[:10]))}
    bins = [(0, 0, "0"), (1, 1, "1"), (2, 2, "2"), (3, 5, "3–5"), (6, 10, "6–10"), (11, 10**9, "11+")]
    hist = lambda deg: [{"bin": lab, "papers": sum(lo <= d <= hi for d in deg)} for lo, hi, lab in bins]
    with (ROOT / "data/out/network_citation_nodes.csv").open("w") as f:
        f.write("work_id,institution,year,in_degree,in_degree_excl_self,out_degree,pagerank_excl_self,pagerank\n")
        for i, w in enumerate(nodes):
            f.write(f"{w[0]},{w[1]},{w[2]},{indeg[i]},{indeg_ns[i]},{outdeg[i]},{pr[i]:.8f},{pr_self[i]:.8f}\n")

    # =============================== co-authorship networks =============================
    fac_info = {r[0]: {"label": r[1], "inst": r[2], "dept": r[3], "faculty": True} for r in q(
        "SELECT fac_id, name, institution, department FROM faculty WHERE fac_id IN (SELECT fac_id FROM fac_work)")}
    rows = q("SELECT node_a, node_b, n_authors, work_id, a_faculty, b_faculty FROM auth_edges")
    ext_info = {}
    for r in q("""SELECT node_id, any_value(name), mode(inst) FROM paper_people WHERE NOT is_faculty GROUP BY 1"""):
        ext_info[r[0]] = {"label": r[1], "inst": r[2] or "?", "dept": "", "faculty": False}
    # G_fac: faculty-only edges
    g_fac = coauthor_graph([r[:4] for r in rows if r[4] and r[5]], fac_info)
    # G_fac_hyper: + hyperauthored papers (all faculty pairs on them)
    hyper_rows = q("""SELECT a.fac_id, b.fac_id, w.n_authors, w.work_id FROM fac_work a
                      JOIN fac_work b ON a.work_id = b.work_id AND a.fac_id < b.fac_id
                      JOIN corpus w ON w.work_id = a.work_id WHERE w.n_authors >= 100""")
    g_fac_hyper = coauthor_graph([r[:4] for r in rows if r[4] and r[5]] + hyper_rows, fac_info)
    hyper_unweighted = coauthor_graph([r[:4] for r in rows if r[4] and r[5]] + [(a, b, 2, w) for a, b, _, w in hyper_rows], fac_info)
    # G_ind
    g_ind = coauthor_graph([r[:4] for r in rows], {**ext_info, **fac_info})

    results = {}
    for name, g in [("G_fac", g_fac), ("G_ind", g_ind)]:
        leiden, louvain = communities(g)
        g.vs["community"] = leiden.membership
        g.vs["degree"] = g.degree()
        g.vs["strength"] = g.strength(weights="weight")
        n = max(g.vcount() - 1, 1)
        g.vs["degree_centrality"] = [d / n for d in g.degree()]
        # betweenness on shortest paths with distance = 1/collaboration strength, normalised
        dist = [1 / w for w in g.es["weight"]]
        norm = (g.vcount() - 1) * (g.vcount() - 2) / 2 or 1
        g.vs["betweenness"] = [b / norm for b in g.betweenness(weights=dist)]
        g.vs["betweenness_hops"] = [b / norm for b in g.betweenness()]
        s = summary(g)
        s.update({"modularity_leiden": round(g.modularity(leiden, weights="weight"), 3),
                  "modularity_louvain": round(g.modularity(louvain, weights="weight"), 3),
                  "communities_leiden": n_groups(leiden.membership),
                  "communities_louvain": n_groups(louvain.membership),
                  "communities_leiden_3plus": n_groups(leiden.membership, 3),
                  "nmi_leiden_louvain": round(ig.compare_communities(leiden, louvain, method="nmi"), 3),
                  "powerlaw_degree": powerlaw(g.degree())})
        fac_idx = [v.index for v in g.vs if v["faculty"]]
        if fac_idx:
            depts = sorted({g.vs[i]["dept"] for i in fac_idx})
            # how well do Leiden communities recover departments / institutes (faculty nodes only)?
            s["nmi_community_department"] = round(ig.compare_communities(
                [g.vs[i]["community"] for i in fac_idx], [depts.index(g.vs[i]["dept"]) for i in fac_idx], method="nmi"), 3)
            s["nmi_community_institute"] = round(ig.compare_communities(
                [g.vs[i]["community"] for i in fac_idx], [int(g.vs[i]["inst"] == "IISER Pune") for i in fac_idx], method="nmi"), 3)
        results[name] = {"summary": s, "degree_ccdf": ccdf(g.degree())}

    # faculty rankings: G_fac vs G_ind
    fac_ids = sorted(fac_info)
    gf = {v["name"]: v for v in g_fac.vs}
    gi = {v["name"]: v for v in g_ind.vs}
    gh = {v["name"]: v for v in g_fac_hyper.vs}
    ghu = {v["name"]: v for v in hyper_unweighted.vs}
    comp_rows = []
    for f in fac_ids:
        a, b = gf[f], gi[f]
        # neighbouring institutions in G_ind -> bridging
        nb_insts = {g_ind.vs[n]["inst"] for n in g_ind.neighbors(b.index)} - {b["inst"]}
        comp_rows.append({"fac_id": f, "name": a["label"], "inst": a["inst"], "dept": a["dept"],
                          "deg_fac": a["degree"], "btw_fac": a["betweenness"], "comm_fac": a["community"],
                          "strength_fac": round(a["strength"], 3),
                          "deg_ind": b["degree"], "btw_ind": b["betweenness"], "comm_ind": b["community"],
                          "partner_insts_ind": len(nb_insts),
                          "deg_fac_hyper": gh[f].degree(), "deg_fac_hyper_unweighted": ghu[f].degree(),
                          "strength_fac_hyper_unweighted": round(sum(hyper_unweighted.es[e]["papers"] for e in hyper_unweighted.incident(ghu[f].index)), 1)})
    rho = {
        "degree": round(spearman([r["deg_fac"] for r in comp_rows], [r["deg_ind"] for r in comp_rows]), 3),
        "betweenness": round(spearman([r["btw_fac"] for r in comp_rows], [r["btw_ind"] for r in comp_rows]), 3),
    }
    # hyperauthorship sensitivity on G_fac (unweighted paper counts make the distortion visible)
    hyper = {
        "hyper_papers": q("SELECT count(*) FROM corpus WHERE n_authors >= 100")[0][0],
        "hyper_papers_multi_faculty": len({r[3] for r in hyper_rows}),
        "hyper_faculty_pairs": len({(r[0], r[1]) for r in hyper_rows}),
        "without": summary(g_fac), "with": summary(hyper_unweighted),
        "rho_strength_papers": round(spearman([r["strength_fac"] for r in comp_rows],
                                              [r["strength_fac_hyper_unweighted"] for r in comp_rows]), 3),
        "top_strength_with": sorted(({"name": r["name"], "papers": r["strength_fac_hyper_unweighted"]} for r in comp_rows),
                                    key=lambda d: -d["papers"])[:5],
    }

    # yearly cumulative snapshots of G_fac and G_ind
    years = {r[0]: r[1] for r in q("SELECT work_id, year FROM corpus")}
    snaps = []
    for y in range(2016, 2027):
        for name, sel in [("G_fac", lambda r: r[4] and r[5]), ("G_ind", lambda r: True)]:
            e = [r for r in rows if sel(r) and years[r[3]] <= y]
            g = ig.Graph.TupleList({(r[0], r[1]) for r in e}, directed=False)
            if g.vcount():
                cc = g.connected_components()
                snaps.append({"graph": name, "year": y, "nodes": g.vcount(), "edges": g.ecount(),
                              "giant_share": round(cc.giant().vcount() / g.vcount(), 3),
                              "mean_degree": round(2 * g.ecount() / g.vcount(), 2),
                              "transitivity": round(g.transitivity_undirected(), 3)})

    # hub authors bridging multiple institutes (G_ind; faculty and external)
    hubs = []
    for v in g_ind.vs:
        insts = {g_ind.vs[n]["inst"] for n in g_ind.neighbors(v.index)} | {v["inst"]}
        if len(insts) >= 3:
            hubs.append({"name": v["label"], "inst": v["inst"], "faculty": v["faculty"],
                         "institutes_bridged": len(insts), "degree": v["degree"],
                         "betweenness": round(v["betweenness"], 5)})
    hubs.sort(key=lambda d: (-d["betweenness"], -d["institutes_bridged"]))

    # =============================== faculty citation graph =============================
    # A -> B when a paper of faculty A cites a paper of faculty B and the two papers share no
    # author. Weight = number of such citation links.
    fc_rows = q("""SELECT a.fac_id, b.fac_id, count(DISTINCT (e.source_id, e.target_id))
                   FROM cit_edges e JOIN fac_work a ON a.work_id = e.source_id
                   JOIN fac_work b ON b.work_id = e.target_id
                   WHERE e.edge_kind = 'internal' AND NOT e.self_citation AND NOT e.involves_hyper
                     AND a.fac_id <> b.fac_id
                   GROUP BY 1, 2""")
    fac_names = sorted(fac_info)
    fidx = {f: i for i, f in enumerate(fac_names)}
    g_fc = ig.Graph(n=len(fac_names), edges=[(fidx[a], fidx[b]) for a, b, _ in fc_rows], directed=True)
    g_fc.es["weight"] = [n for _, _, n in fc_rows]
    g_fc.vs["name"] = fac_names
    for k in ("label", "inst", "dept"):
        g_fc.vs[k] = [fac_info[f][k] for f in fac_names]
    fc_pr = g_fc.pagerank(weights="weight", directed=True)
    fc_in, fc_out = g_fc.strength(mode="in", weights="weight"), g_fc.strength(mode="out", weights="weight")
    links = sum(g_fc.es["weight"])
    same = lambda key: sum(e["weight"] for e in g_fc.es if g_fc.vs[e.source][key] == g_fc.vs[e.target][key])
    fc_sum = {"faculty": g_fc.vcount(), "faculty_pairs": g_fc.ecount(), "citation_links": links,
              "faculty_citing_colleagues": sum(d > 0 for d in fc_out),
              "faculty_cited_by_colleagues": sum(d > 0 for d in fc_in),
              "same_department_share": round(same("dept") / max(links, 1), 3),
              "same_institute_share": round(same("inst") / max(links, 1), 3),
              "reciprocity": round(g_fc.reciprocity(), 3)}
    dept_flow = Counter()
    for e in g_fc.es:
        a, b = g_fc.vs[e.source], g_fc.vs[e.target]
        dept_flow[(a["inst"], a["dept"], b["inst"], b["dept"])] += e["weight"]
    fc_keep = [v.index for v in g_fc.vs if g_fc.degree(v.index) > 0]
    fc_sub = g_fc.subgraph(fc_keep)
    fc_pos = layout(fc_sub, weights="weight")
    fac_cit_graph = {
        "nodes": [{"id": v["name"], "label": v["label"], "inst": v["inst"], "dept": v["dept"],
                   "cited_by_colleagues": fc_in[i], "cites_colleagues": fc_out[i], "pagerank": round(fc_pr[i], 5),
                   "x": round(fc_pos[j][0], 1), "y": round(fc_pos[j][1], 1)}
                  for j, (i, v) in enumerate((i, g_fc.vs[i]) for i in fc_keep)],
        "edges": [[e.source, e.target, e["weight"]] for e in fc_sub.es],
        "summary": fc_sum,
        "dept_flow": [{"from_inst": k[0], "from_dept": k[1], "to_inst": k[2], "to_dept": k[3], "links": n}
                      for k, n in dept_flow.most_common()],
    }

    def export_graph(g: ig.Graph, min_degree=0):
        keep = [v.index for v in g.vs if v.degree() >= min_degree]
        sub = g.subgraph(keep)
        pos = layout(sub, weights="weight")
        return {
            "nodes": [{"id": v["name"], "label": v["label"], "inst": v["inst"], "dept": v["dept"],
                       "faculty": v["faculty"], "community": v["community"], "degree": v["degree"],
                       "betweenness": round(v["betweenness"], 6), "x": round(pos[v.index][0], 1),
                       "y": round(pos[v.index][1], 1)} for v in sub.vs],
            "edges": [[e.source, e.target, round(e["weight"], 3), e["papers"]] for e in sub.es],
        }

    (OUT / "cit_graph.json").write_text(json.dumps(cit_graph, separators=(",", ":")))
    (OUT / "fac_graph.json").write_text(json.dumps(export_graph(g_fac), separators=(",", ":")))
    (OUT / "ind_graph.json").write_text(json.dumps(export_graph(g_ind), separators=(",", ":")))
    (OUT / "faccit_graph.json").write_text(json.dumps(fac_cit_graph, separators=(",", ":")))
    metrics = {
        "citation": {"summary": cit_sum, "summary_excl_self": cit_sum_ns,
                     "indegree_ccdf": ccdf(indeg), "indegree_ccdf_excl_self": ccdf(indeg_ns),
                     "powerlaw_indegree": powerlaw(indeg),
                     "indegree_hist": hist(indeg), "indegree_hist_excl_self": hist(indeg_ns),
                     "top_pagerank": cit_top, "top_pagerank_with_self": cit_top_self,
                     "top_indegree": cit_top_indeg, "pagerank_vs_indegree": pr_vs_indeg,
                     "flow_year": flow_year, "flow_total": flow_tot,
                     "top_citing_institutes": top_citing, "top_citing_papers": top_citing_papers,
                     "visual_component_share": round(len(keep) / len(nodes), 3)},
        "coauthorship": results, "faculty_comparison": comp_rows, "spearman_fac_vs_ind": rho,
        "hyperauthorship": hyper, "snapshots": snaps, "hubs": hubs[:25],
    }
    (OUT / "network_metrics.json").write_text(json.dumps(metrics, separators=(",", ":"), default=str))
    with (ROOT / "data/out/network_faculty_centrality.csv").open("w") as f:
        cols = list(comp_rows[0])
        f.write(",".join(cols) + "\n")
        for r in comp_rows:
            f.write(",".join(f'"{r[c]}"' if isinstance(r[c], str) else f"{r[c]}" for c in cols) + "\n")

    print("G_cit", cit_sum)
    print("G_cit without self-citations", cit_sum_ns)
    print("faculty citation graph", fc_sum)
    for k, v in results.items():
        print(k, v["summary"])
    print("spearman", rho, "| hyper", {k: hyper[k] for k in ("hyper_papers", "hyper_faculty_pairs", "rho_strength_papers")})
    print("flow", flow_tot)


if __name__ == "__main__":
    main()
