// WebGL network view on sigma v4 + graphology. Layouts are precomputed in Python (igraph),
// so the browser only draws. Hover a node to isolate its neighbourhood; click to pin it.
// sigma 4 + graphology are vendored into one ESM file (npm run vendor) so the dashboard
// builds offline and graphology's Node "events" import is resolved to the browser polyfill.
import {Graph, Sigma, extremityArrow, layerPlain, pathLine, pathLoop} from "./vendor/graph-libs.js";

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const darkQuery = matchMedia("(prefers-color-scheme: dark)");

// Graph palette, read from the CSS tokens in style.css (light and dark are separate,
// validated steps, not an automatic flip). Re-read whenever the colour scheme changes.
export function graphTheme() {
  return {
    dark: darkQuery.matches,
    pune: css("--pune"), kolkata: css("--kolkata"), context: css("--context"),
    label: css("--graph-label"), labelStrong: css("--graph-label-strong"), labelBg: css("--graph-label-bg"),
    edge: css("--graph-edge"), edgeHi: css("--graph-edge-hi"),
    card: css("--graph-card"), cardShadow: css("--graph-card-shadow"),
    rampLo: css("--ramp-lo"), rampHi: css("--ramp-hi")
  };
}

// Scale an rgba() token's alpha: dense graphs need fainter edges, or overlapping strokes
// stack into a solid tangle (worst on dark surfaces, where additive light reads as white).
function withAlpha(c, f) {
  const m = c.match(/rgba?\(([^)]+)\)/);
  if (!m) return c;
  const [r, g, b, a = 1] = m[1].split(",").map((x) => parseFloat(x));
  return `rgba(${r}, ${g}, ${b}, ${(a * f).toFixed(3)})`;
}

// `color(node, theme)` may return a role ("pune" | "kolkata" | "context") or any CSS colour.
const resolve = (c, theme) => theme[c] ?? c;

export function graphView({
  nodes, edges, directed = false, height = 620,
  color, size, label = () => "", tooltip = () => "", edgeSize = () => 0.6,
  labelThreshold = 9, focus = null,
  // optional: emphasise(edge) -> true draws the edge in the strong edge colour; hideEdge(edge) drops it
  emphasise = null, hideEdge = null
}) {
  const wrap = document.createElement("div");
  wrap.className = "graph-wrap";
  wrap.style.height = `${height}px`;
  const tip = Object.assign(document.createElement("div"), {className: "graph-tip"});
  tip.style.display = "none";
  const hint = Object.assign(document.createElement("div"), {className: "graph-hint",
    textContent: "ctrl/⌘ + scroll to zoom · drag to pan · hover a node · click to pin"});
  wrap.append(tip, hint);

  let theme = graphTheme();
  // ~1 at <=1.5k edges, falling to 0.3 for very dense graphs
  const density = Math.max(0.3, Math.min(1, Math.sqrt(1500 / Math.max(edges.length, 1))));
  const edgeColor = (e) => (emphasise?.(e) ? withAlpha(theme.edgeHi, 0.7) : withAlpha(theme.edge, density));
  const g = new Graph({type: directed ? "directed" : "undirected", allowSelfLoops: false});
  nodes.forEach((n, i) => g.addNode(String(i), {
    x: n.x, y: -n.y, size: size(n), color: resolve(color(n, theme), theme), label: label(n), raw: n
  }));
  edges.forEach((e) => {
    const [s, t] = e;
    if (s !== t && !hideEdge?.(e)) {
      g.mergeEdge(String(s), String(t), {size: Math.min(edgeSize(e) * (emphasise?.(e) ? 1.6 : 1), 2.5),
                                         color: edgeColor(e), raw: e});
    }
  });

  let hovered = null, pinned = null, neighbours = new Set();
  const active = () => pinned ?? hovered;
  const setActive = () => {
    const a = active();
    neighbours = a == null ? new Set() : new Set(g.neighbors(a));
    renderer?.refresh({skipIndexation: true});
  };
  const focusSet = focus ? new Set(nodes.map((n, i) => (focus(n) ? String(i) : null)).filter((x) => x)) : null;

  // labels sit on a translucent surface pill so they stay readable over edges in both themes
  const labelBase = () => ({labelColor: theme.label, labelBackgroundColor: theme.labelBg, labelBackgroundPadding: 2});
  const faded = {opacity: 0.14, label: "", zIndex: 0};

  let renderer;
  const start = () => {
    if (renderer || !wrap.isConnected) return;
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
        if (a != null && key !== a && !neighbours.has(key)) return faded;
        if (focusSet && a == null && !focusSet.has(key)) return faded;
        const base = labelBase();
        if (key === a) {
          return {...base, zIndex: 2, labelColor: theme.labelStrong, labelVisibility: "visible",
                  label: data.label || label(g.getNodeAttribute(key, "raw")) || key,
                  backdropColor: theme.card, backdropShadowColor: theme.cardShadow};
        }
        // name every neighbour when the neighbourhood is small enough to read
        if (a != null) return {...base, zIndex: 1, labelColor: theme.labelStrong,
                               ...(neighbours.size <= 30 ? {labelVisibility: "visible"} : {})};
        return {...base, zIndex: 1, backdropColor: theme.card, backdropShadowColor: theme.cardShadow};
      },
      edgeReducer: (key) => {
        const a = active();
        if (a == null) {
          return focusSet && !(focusSet.has(g.source(key)) && focusSet.has(g.target(key))) ? {visibility: "hidden"} : {};
        }
        return g.hasExtremity(key, a) ? {color: theme.edgeHi, size: 1.4, zIndex: 1} : {visibility: "hidden"};
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
    tip.style.left = `${Math.max(4, Math.min(x + 14, r.width - 330))}px`;
    tip.style.top = `${Math.max(4, Math.min(y + 14, r.height - 120))}px`;
  };

  // follow OS light/dark changes without rebuilding the graph
  const onScheme = () => {
    theme = graphTheme();
    g.updateEachNodeAttributes((k, attr) => ({...attr, color: resolve(color(attr.raw, theme), theme)}));
    g.updateEachEdgeAttributes((k, attr) => ({...attr, color: edgeColor(attr.raw)}));
    renderer?.refresh();
  };
  darkQuery.addEventListener("change", onScheme);

  // sigma needs the container in the DOM with a size; start once Framework has inserted it
  const ro = new ResizeObserver(() => { start(); renderer?.resize(); });
  ro.observe(wrap);
  requestAnimationFrame(start);
  wrap.kill = () => { ro.disconnect(); darkQuery.removeEventListener("change", onScheme); renderer?.kill(); };
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
