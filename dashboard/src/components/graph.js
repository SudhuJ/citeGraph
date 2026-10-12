// WebGL network view on sigma v4 + graphology. Layouts are precomputed in Python (igraph),
// so the browser only draws. Hover a node to isolate its neighbourhood; click to pin it.
// sigma 4 + graphology are vendored into one ESM file (npm run vendor) so the dashboard
// builds offline and graphology's Node "events" import is resolved to the browser polyfill.
import {Graph, Sigma, extremityArrow, layerPlain, pathLine, pathLoop} from "./vendor/graph-libs.js";

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export function graphView({
  nodes, edges, directed = false, height = 620,
  color, size, label = () => "", tooltip = () => "", edgeSize = () => 0.6,
  labelThreshold = 9, focus = null
}) {
  const wrap = document.createElement("div");
  wrap.className = "graph-wrap";
  wrap.style.height = `${height}px`;
  const tip = Object.assign(document.createElement("div"), {className: "graph-tip"});
  tip.style.display = "none";
  const hint = Object.assign(document.createElement("div"), {className: "graph-hint",
    textContent: "ctrl/⌘ + scroll to zoom · drag to pan · hover a node · click to pin"});
  wrap.append(tip, hint);

  const g = new Graph({type: directed ? "directed" : "undirected", allowSelfLoops: false});
  nodes.forEach((n, i) => g.addNode(String(i), {
    x: n.x, y: -n.y, size: size(n), color: color(n), label: label(n), raw: n
  }));
  const edgeColor = css("--edge") || "rgba(128,128,128,0.2)";
  edges.forEach((e, i) => {
    const [s, t] = e;
    if (s === t) return;
    g.mergeEdge(String(s), String(t), {size: edgeSize(e), color: edgeColor});
  });

  let hovered = null, pinned = null, neighbours = new Set();
  const active = () => pinned ?? hovered;
  const setActive = () => {
    const a = active();
    neighbours = a == null ? new Set() : new Set(g.neighbors(a));
    renderer?.refresh({skipIndexation: true});
  };
  const focusSet = focus ? new Set(nodes.map((n, i) => (focus(n) ? String(i) : null)).filter((x) => x)) : null;

  let renderer;
  const start = () => {
    if (renderer || !wrap.isConnected) return;
    const dim = css("--theme-foreground-faintest") || "#ddd";
    renderer = new Sigma(g, wrap, {
      settings: {
        allowInvalidContainer: true, labelRenderedSizeThreshold: labelThreshold, labelDensity: 0.6,
        renderEdgeLabels: false, hideEdgesOnMove: g.size > 8000, zIndex: true, minCameraRatio: 0.03,
        maxCameraRatio: 4, gestureTarget: "shared"
      },
      ...(directed ? {primitives: {edges: {paths: [pathLine(), pathLoop()], extremities: [extremityArrow()],
                                           layers: [layerPlain()], defaultHead: "arrow"}}} : {}),
      nodeReducer: (key, data) => {
        const a = active();
        if (a != null && key !== a && !neighbours.has(key)) return {color: dim, label: "", zIndex: 0};
        if (focusSet && a == null && !focusSet.has(key)) return {color: dim, label: "", zIndex: 0};
        if (key === a) return {zIndex: 2, label: data.label || label(g.getNodeAttribute(key, "raw")) || key};
        return {zIndex: 1};
      },
      edgeReducer: (key) => {
        const a = active();
        if (a == null) return focusSet && !(focusSet.has(g.source(key)) && focusSet.has(g.target(key))) ? {visibility: "hidden"} : {};
        return g.hasExtremity(key, a) ? {color: css("--theme-foreground-muted"), size: 1.2} : {visibility: "hidden"};
      }
    });
    wrap.renderer = renderer;
    renderer.on("enterNode", ({node, event}) => {
      hovered = node;
      setActive();
      tip.innerHTML = tooltip(g.getNodeAttribute(node, "raw"), g.degree(node));
      tip.style.display = "block";
      place(event);
    });
    renderer.on("leaveNode", () => { hovered = null; setActive(); tip.style.display = "none"; });
    renderer.on("clickNode", ({node}) => { pinned = pinned === node ? null : node; setActive(); });
    renderer.on("clickStage", () => { pinned = null; setActive(); });
    renderer.getMouseCaptor().on("mousemovebody", (e) => tip.style.display === "block" && place(e));
  };
  const place = (e) => {
    const r = wrap.getBoundingClientRect();
    const x = (e?.original?.clientX ?? e?.clientX ?? 0) - r.left, y = (e?.original?.clientY ?? e?.clientY ?? 0) - r.top;
    tip.style.left = `${Math.min(x + 14, r.width - 330)}px`;
    tip.style.top = `${Math.min(y + 14, r.height - 120)}px`;
  };
  // sigma needs the container in the DOM with a size; start once Framework has inserted it
  const ro = new ResizeObserver(() => { start(); renderer?.resize(); });
  ro.observe(wrap);
  requestAnimationFrame(start);
  wrap.kill = () => { ro.disconnect(); renderer?.kill(); };
  wrap.graph = g;
  return wrap;
}

export function legend(items) {
  const d = document.createElement("div");
  d.className = "legend-row";
  for (const [lab, col] of items) {
    const s = document.createElement("span");
    s.innerHTML = `<span class="swatch" style="background:${col}"></span>${lab}`;
    d.append(s);
  }
  return d;
}
