"""Network analysis (igraph) → dashboard/src/data/*.json and data/out/network_*.csv

G_cit  directed citation graph on the corpus (internal edges only, §6a "within")
G_fac  faculty-only co-authorship graph (strict §6b)
G_ind  faculty + Indian co-authors (connectivity, §7b)
Hyperauthored papers (>=100 authors, truncated lists) are excluded from the co-authorship
graphs; G_fac_hyper re-adds them to show how much they would distort the picture.
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
    und = g.as_undirected() if g.is_directed() else g
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
                 FROM corpus w JOIN work_inst wi USING (work_id) ORDER BY 1""")
    idx = {r[0]: i for i, r in enumerate(nodes)}
    edges = [(idx[s], idx[t]) for s, t in q("SELECT source_id, target_id FROM int_edges")]
    gc = ig.Graph(n=len(nodes), edges=edges, directed=True)
    gc.simplify()
    indeg = gc.indegree()
    outdeg = gc.outdegree()
    pr = gc.pagerank(directed=True, damping=0.85)
    cit_sum = summary(gc)
    cit_sum["reciprocal_share"] = round(gc.reciprocity(), 4)

    # cross-institute flow (institution level), year-wise
    flow_year = [dict(zip(["institution", "year", "direction", "citations"], r)) for r in q("""
        SELECT fw.institution, lw.year, 'in', count(DISTINCT (e.source_id, e.target_id))
        FROM in_edges e JOIN (SELECT DISTINCT work_id, institution, inst_id FROM fac_work) fw ON fw.work_id = e.target_id
        JOIN 'data/stage/link_works.parquet' lw ON lw.link_id = e.source_id AND lw.kind = 'citing'
        WHERE EXISTS (SELECT 1 FROM link_inst li WHERE li.link_id = e.source_id AND li.inst_id <> fw.inst_id)
          AND lw.year BETWEEN 2016 AND 2026
        GROUP BY ALL
        UNION ALL
        SELECT fw.institution, w.year, 'out', count(DISTINCT (e.source_id, e.target_id))
        FROM out_edges e JOIN (SELECT DISTINCT work_id, institution, inst_id FROM fac_work) fw ON fw.work_id = e.source_id
        JOIN corpus w ON w.work_id = e.source_id
        WHERE EXISTS (SELECT 1 FROM link_inst li WHERE li.link_id = e.target_id AND li.inst_id <> fw.inst_id)
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
        FROM in_edges e JOIN (SELECT DISTINCT work_id, institution FROM fac_work) fw ON fw.work_id = e.target_id
        JOIN 'data/stage/link_works.parquet' lw ON lw.link_id = e.source_id AND lw.kind = 'citing'
        LEFT JOIN node_meta nm ON nm.id = e.source_id
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
                          "venue": w[7], "indeg": indeg[i], "outdeg": outdeg[i], "pr": pr[i]})
    cit_graph = {"nodes": cit_nodes, "edges": [[sub.vs[e.source].index, sub.vs[e.target].index] for e in sub.es]}
    def top10(scores, pool):
        return [{"title": nodes[i][3], "inst": nodes[i][1], "year": nodes[i][2], "doi": nodes[i][4],
                 "pagerank": round(scores[i], 6), "indeg": indeg[i], "cites_total": nodes[i][5],
                 "hyperauthored": nodes[i][8] >= 100}
                for i in sorted(pool, key=lambda i: -scores[i])[:10]]
    cit_top = top10(pr, range(len(nodes)))
    # big-collaboration papers cite each other densely and dominate PageRank; recompute without them
    small = [i for i in range(len(nodes)) if nodes[i][8] < 100]
    g_small = gc.subgraph(small)
    pr_small_sub = g_small.pagerank(directed=True, damping=0.85)
    pr_small = [0.0] * len(nodes)
    for j, i in enumerate(small):
        pr_small[i] = pr_small_sub[j]
    cit_top_small = top10(pr_small, small)
    with (ROOT / "data/out/network_citation_nodes.csv").open("w") as f:
        f.write("work_id,institution,year,in_degree,out_degree,pagerank\n")
        for i, w in enumerate(nodes):
            f.write(f"{w[0]},{w[1]},{w[2]},{indeg[i]},{outdeg[i]},{pr[i]:.8f}\n")

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
                  "communities_leiden": len(set(leiden.membership)),
                  "communities_louvain": len(set(louvain.membership)),
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
        "hyper_papers": len({r[3] for r in hyper_rows}),
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
    metrics = {
        "citation": {"summary": cit_sum, "indegree_ccdf": ccdf(indeg), "powerlaw_indegree": powerlaw(indeg),
                     "top_pagerank": cit_top, "top_pagerank_excl_hyper": cit_top_small, "flow_year": flow_year, "flow_total": flow_tot,
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
    for k, v in results.items():
        print(k, v["summary"])
    print("spearman", rho, "| hyper", {k: hyper[k] for k in ("hyper_papers", "hyper_faculty_pairs", "rho_strength_papers")})
    print("flow", flow_tot)


if __name__ == "__main__":
    main()
