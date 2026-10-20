// Observable Framework config — https://observablehq.com/framework/config
export default {
  title: "citeGraph · Group 19",
  root: "src",
  style: "style.css",
  pages: [
    {name: "Overview", path: "/"},
    {name: "Output & venues", path: "/output"},
    {name: "Faculty & departments", path: "/faculty"},
    {name: "Collaboration", path: "/authorship-network"},
    {name: "Knowledge flow", path: "/citation-network"},
    {name: "India & the world", path: "/connectivity"},
    {name: "Big collaborations", path: "/collaborations"},
    {name: "Methods & data", path: "/methods"}
  ],
  head: '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><circle cx=%2230%22 cy=%2270%22 r=%2216%22 fill=%22%232a78d6%22/><circle cx=%2272%22 cy=%2232%22 r=%2216%22 fill=%22%23eb6834%22/><line x1=%2230%22 y1=%2270%22 x2=%2272%22 y2=%2232%22 stroke=%22%23898781%22 stroke-width=%226%22/></svg>">',
  footer: "DPCN 2026 · Group 19 · IISER Pune & IISER Kolkata · data: OpenAlex (CC0), SCImago",
  sidebar: true,
  toc: true,
  search: true
};
