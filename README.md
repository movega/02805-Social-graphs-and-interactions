# Varmel · Marvel Universe Network Atlas

Group site for **02805 Social Graphs and Interactions** (DTU, autumn 2026) — the
"Go nuts with your LLM" posts, one per week, on the shared Marvel Wikipedia
network (303 characters, 1,784 directed links).

Live site: <https://movega.github.io/02805-Social-graphs-and-interactions/>

## Layout

```
index.html            Home: hero, the 8 weeks, the team, the post index
posts/
  week1.html          Week 1 post (placeholder, ready to fill in)
  _template.html      Copy this to weekNN.html for every new week
assets/
  css/site.css        All styling — one file, every page
  js/site.js          SITE config (team name, members, repo) + week-state logic
  img/                Exported figures go here
Data/                 Frozen week-1 release: node roster + edge list
```

## Publishing on GitHub Pages

1. Push this folder to the repo.
2. **Settings → Pages → Build and deployment → Deploy from a branch**, branch
   `main`, folder `/ (root)`.
3. The site appears at `https://<user-or-org>.github.io/<repo>/` within a minute.

`.nojekyll` is present so GitHub serves the files as-is (no Jekyll build, and
nothing starting with `_` gets dropped — which matters for `posts/_template.html`).

All paths are relative, so the site works both at a project URL
(`/<repo>/`) and opened straight from disk.

## Making it ours

Open `assets/js/site.js` and edit the `SITE` block at the top — team name,
repo URL, the three members. Every page picks it up:

```js
var SITE = {
  teamName: 'Varmel',
  repoUrl: 'https://github.com/movega/02805-Social-graphs-and-interactions',
  repoLabel: 'movega/02805-Social-graphs-and-interactions',
  members: [
    { name: 'Alvaro Vega', role: 'Network analysis', link: 'https://github.com/...' },
    ...
  ],
  courseStart: new Date(2026, 8, 2),   // Wednesday 2 September 2026 = week 1
  weekOverride: null                   // set to 1..13 to preview another week
};
```

The spider on the home page lights up one leg per week, computed from
`courseStart`. Set `weekOverride` to see how a later week will look, then put it
back to `null`.

Colours live in one place too: the `:root` block at the top of `assets/css/site.css`.

## Adding a weekly post

1. `cp posts/_template.html posts/week2.html`
2. Replace every `[bracket]` and every `todo` chip.
3. Export figures to `assets/img/` and swap the `figure-placeholder` divs for
   `<img src="../assets/img/....png" alt="...">`.
4. On `index.html`: turn the matching `post-card--empty` into a link
   (copy the week-1 card), and point `#footer-w2-title` at the new page.
5. Post the site link in the Teams channel by Monday evening, and leave
   constructive criticism on at least one other group's post.

## Post structure

The course asks each post to answer, in order: **what we asked → what we did →
one figure or table → what surprised us**. The template keeps that spine, plus a
caveats section and a "reproduce it" pointer.

## Data

`Data/week1_*.tsv` is the frozen week-1 release. Load the node roster *before*
the edges, or the 17 isolated characters disappear:

```python
import pandas as pd, networkx as nx

nodes = pd.read_csv("Data/week1_nodes.tsv", sep="\t", comment="#")
edges = pd.read_csv("Data/week1_edges.tsv", sep="\t", comment="#",
                    names=["source", "target"])

G = nx.DiGraph()
G.add_nodes_from(nodes.node_id)
G.add_edges_from(edges.itertuples(index=False, name=None))
```

---

Course page: <https://sunelehmann.com/socialgraphs2026-web/>
