"""Week 3 - who holds the Marvel universe together?

Every number the post claims is computed here. Figures go to the site's assets/img/,
the interactive charts' data to assets/data/week3_charts.json, numbers to stdout.
Both paths are found by walking up from this file, so it does not matter which
directory you run it from.

    python analysis_week3.py            # 100 shuffled universes per attack (~5 min on 12 cores)
    python analysis_week3.py --fast     # 20, for iterating
    python analysis_week3.py --json     # also dump every number to week3_numbers.json

The question: which characters is the network actually relying on? Three passes.

  1. Take characters out one at a time and see who falls off with them.
  2. Take them out in sequence, ordered by four different measures of importance,
     and watch the main connected group shrink.
  3. Run the same attacks on degree-preserving shuffles (week 2's null), to separate
     what the fame counts force from what the real wiring adds.

Everything runs on the undirected giant component, n=277 m=1421, except PageRank,
which needs the arrows and is computed on the directed links among the same 277.
"""

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20260916


def _find(*candidates):
    """Walk up from this file looking for one of these relative paths."""
    here = HERE
    for _ in range(5):
        for rel in candidates:
            path = os.path.join(here, *rel.split("/"))
            if os.path.isdir(path):
                return path
        here = os.path.dirname(here)
    raise SystemExit("could not locate " + " or ".join(candidates))


DATA = _find("Data")
IMG = _find("assets/img")

# --- Palette (the site's tokens; the same four hues as weeks 1 and 2) -------
INK      = "#fcf3f0"     # --text
MUTED    = "#b09893"     # --muted
GRID     = "#5a4441"
PANEL    = "#1d0c0b"     # --bg-panel
PAGE     = "#0c0403"     # --bg: baked in so the PNG is never transparent
C_BET    = "#e0523f"     # betweenness - the attack the post is about  (red)
C_DEG    = "#3d92d6"     # degree                                      (blue)
C_CLOSE  = "#b78a1c"     # closeness                                   (gold)
C_PR     = "#8f7ad6"     # PageRank                                    (violet)

plt.rcParams.update({
    "figure.facecolor": PAGE, "axes.facecolor": PAGE, "savefig.facecolor": PAGE,
    "font.family": "DejaVu Sans", "font.size": 10,
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "axes.linewidth": 0.8,
    "grid.color": GRID, "grid.alpha": 0.35, "grid.linewidth": 0.6,
    "legend.frameon": False, "figure.dpi": 160,
})
HALO = [pe.withStroke(linewidth=2.6, foreground=PANEL)]


def despine(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def save(fig, name):
    path = os.path.join(IMG, name)
    fig.savefig(path, bbox_inches="tight", facecolor=PAGE)
    plt.close(fig)
    print("  wrote " + os.path.relpath(path, os.path.dirname(IMG)))


# --- 1. The graphs ---------------------------------------------------------

def load():
    """Roster first, edges second - week 1's lesson: build from the edge list
    alone and the 17 characters with no links vanish silently."""
    names = {}
    with open(os.path.join(DATA, "week1_nodes.tsv"), encoding="utf-8") as f:
        header = None
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\r\n").split("\t")
            if header is None:
                header = parts
                continue
            row = dict(zip(header, parts))
            names[row["node_id"]] = row["name"]

    D = nx.DiGraph()
    D.add_nodes_from(names)
    with open(os.path.join(DATA, "week1_edges.tsv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) >= 2:
                D.add_edge(parts[0], parts[1])

    FULL = nx.Graph(D)
    FULL.remove_edges_from(nx.selfloop_edges(FULL))
    GIANT = FULL.subgraph(max(nx.connected_components(FULL), key=len)).copy()
    DGIANT = D.subgraph(GIANT.nodes()).copy()
    return names, D, GIANT, DGIANT


GENERIC = {"character", "characters", "comics", "Marvel Comics"}
_BASES = {}


def plain(names, n):
    """A short label: 'Hercules (Marvel Comics)' -> 'Hercules'.

    The bracket only goes when it carries no information. Three different
    Spider-Women, two Human Torches and two Wolverines share this roster, so
    'Spider-Woman (Jessica Drew)' keeps its bracket; the generic ones do not.
    """
    if id(names) not in _BASES:
        counts = {}
        for full in names.values():
            b = full.split(" (")[0]
            counts[b] = counts.get(b, 0) + 1
        _BASES[id(names)] = counts
    full = names[n]
    if " (" not in full:
        return full
    base, bracket = full.split(" (", 1)
    bracket = bracket.rstrip(")")
    if bracket in GENERIC or _BASES[id(names)][base] == 1:
        return base
    return full


def giant_size(G):
    return max((len(c) for c in nx.connected_components(G)), default=0)


# --- 2. One character at a time --------------------------------------------

def single_removals(G, names):
    """Remove each articulation point on its own and list who falls off with it.

    Any other character's removal costs exactly one character - itself - so the
    articulation points are the only ones worth looking at.
    """
    n = G.number_of_nodes()
    bet = nx.betweenness_centrality(G)
    deg = dict(G.degree())
    bet_rank = {v: i + 1 for i, v in enumerate(sorted(G, key=lambda x: (-bet[x], x)))}
    deg_rank = {v: i + 1 for i, v in enumerate(sorted(G, key=lambda x: (-deg[x], x)))}

    rows = []
    for v in nx.articulation_points(G):
        H = G.copy()
        H.remove_node(v)
        comps = sorted(nx.connected_components(H), key=len, reverse=True)
        lost = sorted((u for c in comps[1:] for u in c), key=lambda u: names[u])
        rows.append({
            "id": v, "name": plain(names, v), "lost": [plain(names, u) for u in lost],
            "lost_ids": lost, "degree": deg[v], "deg_rank": deg_rank[v],
            "betweenness": bet[v], "bet_rank": bet_rank[v],
        })
    rows.sort(key=lambda r: (-len(r["lost"]), r["bet_rank"]))

    top_bet = sorted(G, key=lambda x: (-bet[x], x))[:10]
    art = {r["id"] for r in rows}
    pendants = sorted(u for u in G if G.degree(u) == 1)
    union = sorted({u for r in rows for u in r["lost_ids"]})
    return {
        "rows": rows, "n": n, "bet": bet, "deg": deg,
        "top_bet_not_cut": [plain(names, v) for v in top_bet if v not in art],
        "pendants": pendants, "cut_off_total": union,
        "cut_off_not_pendant": [plain(names, u) for u in union if u not in set(pendants)],
    }


# --- 3. Attacks ------------------------------------------------------------
# Every attack is adaptive: after each removal the measure is recomputed on what
# is left, so it always takes out the currently most important character. Ties
# break on the node id, so the order is reproducible.

def _pick(scores):
    return max(scores, key=lambda v: (scores[v], v))


def next_degree(H, DH=None):
    return _pick(dict(H.degree()))


def next_betweenness(H, DH=None):
    return _pick(nx.betweenness_centrality(H))


def next_closeness(H, DH=None):
    return _pick(nx.closeness_centrality(H))


def next_pagerank(H, DH):
    return _pick(nx.pagerank(DH.subgraph(H.nodes()), alpha=0.85))


ATTACKS = [
    # key, label, picker, colour
    ("betweenness", "Betweenness", next_betweenness, C_BET),
    ("degree", "Degree", next_degree, C_DEG),
    ("pagerank", "PageRank", next_pagerank, C_PR),
    ("closeness", "Closeness", next_closeness, C_CLOSE),
]


def attack(G, picker, n0, DG=None, stop_at=2):
    """Remove characters one by one; return the removal order and, after each step,
    the size of the largest remaining piece as a fraction of n0.

    Stops once the largest piece is down to `stop_at` characters - past that point
    there is nothing left to measure, and it is where betweenness is slowest.
    """
    H = G.copy()
    order = []
    sizes = [giant_size(H) / n0]
    while H.number_of_nodes() and giant_size(H) > stop_at:
        v = picker(H, DG)
        H.remove_node(v)
        order.append(v)
        sizes.append(giant_size(H) / n0)
    return order, np.array(sizes)


def pad(curve, length):
    """Extend a stopped curve with its last value, so curves can be averaged."""
    if len(curve) >= length:
        return curve[:length]
    return np.concatenate([curve, np.full(length - len(curve), curve[-1])])


def halving_step(curve):
    """Removals needed before the main group is below half its original size."""
    below = np.nonzero(curve < 0.5)[0]
    return int(below[0]) if len(below) else len(curve)


def random_attacks(G, n0, nrep, rng):
    nodes = sorted(G)
    curves = []
    for _ in range(nrep):
        order = list(rng.permutation(nodes))
        H = G.copy()
        sizes = [giant_size(H) / n0]
        for v in order:
            H.remove_node(v)
            sizes.append(giant_size(H) / n0)
        curves.append(np.array(sizes))
    return np.array(curves)


# --- 4. Compared to what ---------------------------------------------------

def _null_worker(args):
    """One degree-preserving shuffle, attacked by degree and by betweenness.
    Module-level so it can run in a worker process."""
    edges, n0, seed = args
    G = nx.Graph(edges)
    m = G.number_of_edges()
    try:
        nx.double_edge_swap(G, nswap=10 * m, max_tries=200 * m, seed=seed)
    except nx.NetworkXAlgorithmError:
        pass
    out = {"giant": giant_size(G)}
    for key, picker in (("degree", next_degree), ("betweenness", next_betweenness)):
        _, curve = attack(G, picker, n0)
        out[key] = {"halving": halving_step(curve), "curve": pad(curve, n0 + 1).tolist()}
    return out


def null_attacks(G, nrep, seed):
    n0 = G.number_of_nodes()
    rng = np.random.default_rng(seed)
    jobs = [(list(G.edges()), n0, int(rng.integers(1 << 31))) for _ in range(nrep)]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1)) as pool:
        return list(pool.map(_null_worker, jobs))


def compare(real, draws):
    """z-score and two-sided empirical p with the +1/+1 correction (as in week 2)."""
    draws = np.asarray(draws, dtype=float)
    mean, sd = float(draws.mean()), float(draws.std())
    z = (real - mean) / sd if sd > 1e-12 * max(1.0, abs(mean)) else None
    extreme = int(np.sum(np.abs(draws - mean) >= abs(real - mean)))
    as_low = int(np.sum(draws <= real))
    return {"real": real, "mean": mean, "sd": sd, "z": z,
            "p": (extreme + 1) / (len(draws) + 1), "as_low": as_low, "nrep": len(draws)}


# --- 5. The seams ----------------------------------------------------------

def seams(G, names, order, curve):
    """Replay the betweenness attack and record, for every character, the step at
    which it is removed or at which it drops out of the main group. The 'break' is
    the step where the second-largest piece is biggest; the pockets are the pieces
    of five or more characters at that step."""
    n0 = G.number_of_nodes()
    H = G.copy()
    removed_at, left_at = {}, {}
    main = set(G)
    second = [0]
    for step, v in enumerate(order, start=1):
        H.remove_node(v)
        removed_at[v] = step
        main.discard(v)
        comps = sorted(nx.connected_components(H), key=len, reverse=True)
        new_main = set(comps[0]) if comps else set()
        for u in main - new_main:
            left_at.setdefault(u, step)
        main = new_main
        second.append(len(comps[1]) if len(comps) > 1 else 0)

    brk = int(np.argmax(second))
    H = G.copy()
    H.remove_nodes_from(order[:brk])
    comps = sorted(nx.connected_components(H), key=len, reverse=True)
    pockets = [sorted(c, key=lambda u: names[u]) for c in comps[1:] if len(c) >= 5]

    # When did each pocket come loose? The first step at which all its members were
    # outside the main group.
    pocket_info = []
    for p in pockets:
        split = max(left_at[u] for u in p)
        bridges = {}
        for u in p:
            for w in G.neighbors(u):
                if w in removed_at and removed_at[w] <= brk:
                    bridges[w] = bridges.get(w, 0) + 1
        top = sorted(bridges, key=lambda w: (-bridges[w], removed_at[w]))[:6]
        pocket_info.append({
            "size": len(p), "members": [names[u] for u in p], "ids": p,
            "split_step": split,
            "internal_links": G.subgraph(p).number_of_edges(),
            "bridges": [(plain(names, w), bridges[w]) for w in top],
        })
    first_big = next((i for i, s in enumerate(second) if s >= 10), None)
    return {
        "break_step": brk, "main_at_break": len(comps[0]),
        "second_at_break": second[brk], "first_piece_10": first_big,
        "dust_at_break": sum(len(c) for c in comps[1:] if len(c) < 5),
        "removed_at": removed_at, "left_at": left_at, "pockets": pocket_info,
    }


# --- 6. Figures ------------------------------------------------------------

def fig_cutpoints(single):
    rows = single["rows"]
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    ys = np.arange(len(rows))[::-1]
    for y, r in zip(ys, rows):
        ax.barh(y, len(r["lost"]), height=0.62, color=C_BET if r["bet_rank"] <= 10 else C_DEG,
                alpha=0.9, zorder=3)
        ax.text(len(r["lost"]) + 0.12, y, ", ".join(r["lost"]), va="center", ha="left",
                fontsize=8.2, color=MUTED, zorder=4)
    ax.set_yticks(ys)
    ax.set_yticklabels(["%s  ·  #%d" % (r["name"], r["bet_rank"]) for r in rows],
                       color=INK, fontsize=9)
    ax.set_xlim(0, 9.6)
    ax.set_xlabel("characters cut off from everyone else when this one is removed")
    ax.set_title("Thirteen single points of failure, and none of them matters much",
                 color=INK, loc="left", fontsize=12, pad=12)
    ax.grid(axis="x", zorder=0)
    ax.bar(0, 0, color=C_BET, label="in the betweenness top 10")
    ax.bar(0, 0, color=C_DEG, label="outside it  (#n = betweenness rank)")
    ax.legend(labelcolor=INK, loc="lower right", fontsize=8.5)
    despine(ax)
    fig.tight_layout()
    save(fig, "week3_cutpoints.png")


def fig_attacks(curves, rand, names, orders):
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    steps = np.arange(len(rand[0]))
    lo, hi = np.percentile(rand, [5, 95], axis=0)
    ax.axhline(0.5, color=GRID, lw=1, ls=":", zorder=1)
    ax.text(236, 0.515, "half the main group gone", color=MUTED, fontsize=8.5, ha="right")
    band = ax.fill_between(steps, lo, hi, color=MUTED, alpha=0.18, lw=0, zorder=1)
    (rline,) = ax.plot(steps, rand.mean(0), color=MUTED, lw=1.6, ls="--", zorder=2)
    handles, labels = [], []
    for key, label, _, colour in ATTACKS:
        c = curves[key]
        (ln,) = ax.plot(np.arange(len(c)), c, color=colour, lw=2.2,
                        zorder=6 if key == "betweenness" else 4)
        h = halving_step(c)
        ax.scatter([h], [c[h]], s=34, color=colour, edgecolor=PAGE, lw=1.2, zorder=7)
        handles.append(ln)
        labels.append("%s  ·  %d" % (label, h))
    handles.append((band, rline))
    labels.append("Random order  ·  %d  (%d runs, 5–95%% band)" % (halving_step(rand.mean(0)), len(rand)))
    h = halving_step(curves["betweenness"])
    ax.annotate("betweenness halves it\nafter %d removals" % h, xy=(h, 0.5), xytext=(h - 52, 0.2),
                color=INK, fontsize=9, path_effects=HALO,
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8))
    ax.set_xlim(0, 240)
    ax.set_ylim(0, 1.03)
    ax.set_xlabel("characters removed")
    ax.set_ylabel("size of the main connected group\n(fraction of the original 277)")
    ax.set_title("Take out the most important character, recompute, repeat",
                 color=INK, loc="left", fontsize=12, pad=12)
    ax.grid(axis="y")
    leg = ax.legend(handles, labels, labelcolor=INK, loc="upper right", fontsize=8.5,
                    title="order of removal  ·  removals to halve it", title_fontsize=8.5)
    leg.get_title().set_color(MUTED)
    despine(ax)
    fig.tight_layout()
    save(fig, "week3_attack_curves.png")


def fig_nulls(tests, nulls):
    from matplotlib.ticker import MaxNLocator
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.9), sharey=True)
    ymax = 0
    for ax, key, title, colour in ((axes[0], "degree", "Removing by degree", C_DEG),
                                   (axes[1], "betweenness", "Removing by betweenness", C_BET)):
        draws = np.array([d[key]["halving"] for d in nulls])
        t = tests[key]
        lo = min(draws.min(), t["real"]) - 2
        hi = max(draws.max(), t["real"]) + 2
        # Same convention as week 2: blue piles are the shuffled universes, the red
        # line is ours - whichever attack it is.
        counts, _, _ = ax.hist(draws, bins=np.arange(lo, hi + 2) - 0.5, color=C_DEG, alpha=0.8,
                               zorder=3, rwidth=0.86, label="%d shuffled universes" % len(draws))
        ymax = max(ymax, counts.max())
        ax.axvline(t["real"], color=C_BET, lw=2.4, zorder=4)
        ax.set_title(title, color=INK, loc="left", fontsize=11, pad=8)
        ax.set_xlabel("removals until half the main group is gone")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="y", zorder=0)
        despine(ax)
        ax.legend(labelcolor=INK, loc="upper right", fontsize=8.5)
    for ax, key in ((axes[0], "degree"), (axes[1], "betweenness")):
        t = tests[key]
        left = t["real"] < t["mean"]
        ax.set_ylim(0, ymax * 1.28)
        ax.text(t["real"] + (-0.4 if left else 0.4), ymax * 1.02,
                "ours: %d\n%d of %d as low" % (t["real"], t["as_low"], t["nrep"]),
                color=INK, fontsize=8.5, va="bottom", ha="right" if left else "left",
                path_effects=HALO, zorder=6)
    axes[0].set_ylabel("shuffled universes")
    fig.tight_layout()
    save(fig, "week3_attack_nulls.png")


# The pockets get names only when their members say so. Each name is tied to two
# characters that belong to it; if a different attack order produced different
# pockets, they would stay unnamed rather than be mislabelled.
POCKET_NAMES = [
    ({"Doom_2099", "Nightmask"}, "Other futures, other universes",
     "Marvel 2099, the New Universe, Killraven", C_CLOSE),
    ({"Northstar_(character)", "Hulkling"}, "Canada and the teen teams",
     "mostly Alpha Flight, Young Avengers, Runaways and the X-Men's students", C_DEG),
    ({"Star-Lord", "Ikaris"}, "The cosmic block",
     "mostly Eternals, Shi'ar, Starjammers, Guardians of the Galaxy and Kree", C_PR),
]


def name_pockets(seam):
    for p in seam["pockets"]:
        ids = set(p["ids"])
        match = next((n for n in POCKET_NAMES if n[0] <= ids), None)
        if match:
            p["label"], p["sub"], p["colour"] = match[1], match[2], match[3]
        else:
            p["label"], p["sub"], p["colour"] = "A pocket of %d" % p["size"], "", MUTED


def exploded_layout(G, seam):
    """One layout per piece, laid out side by side: the main group on the left, the
    pockets stacked on the right, the dust in a grid underneath. A single layout of
    the whole network scatters the pockets across the hairball."""
    brk = seam["break_step"]
    H = G.copy()
    H.remove_nodes_from([v for v, s in seam["removed_at"].items() if s <= brk])
    comps = sorted(nx.connected_components(H), key=len, reverse=True)
    main = comps[0]
    dust = sorted((u for c in comps[1:] if len(c) < 5 for u in c),
                  key=lambda u: (-G.degree(u), u))

    def place(nodes, cx, cy, r, seed):
        nodes = sorted(nodes)
        if len(nodes) == 1:
            raw = {nodes[0]: np.zeros(2)}
        else:
            raw = nx.spring_layout(H.subgraph(nodes), seed=seed, iterations=400)
        xy = np.array(list(raw.values()))
        span = max((xy.max(0) - xy.min(0)).max(), 1e-9)
        mid = (xy.max(0) + xy.min(0)) / 2
        return {v: (q - mid) / span * 2 * r + np.array([cx, cy]) for v, q in raw.items()}

    pos, group = {}, {}
    pos.update(place(main, -0.42, 0.04, 0.62, 11))
    group.update({v: "main" for v in main})
    anchors = [(0.98, 0.56, 0.24), (0.98, -0.07, 0.21), (0.98, -0.66, 0.13)]
    for i, p in enumerate(seam["pockets"]):
        cx, cy, r = anchors[min(i, len(anchors) - 1)]
        pos.update(place(p["ids"], cx, cy, r, 3 + i))
        group.update({v: i for v in p["ids"]})
    cols = 13
    for j, u in enumerate(dust):
        pos[u] = np.array([-1.0 + (j % cols) * 0.095, -0.86 - (j // cols) * 0.085])
        group[u] = "dust"
    return H, pos, group, dust


def fig_seams(G, names, seam):
    brk = seam["break_step"]
    H, pos, group, dust = exploded_layout(G, seam)
    fig, ax = plt.subplots(figsize=(9.8, 7.4))

    for u, v in H.edges():
        if group[u] == group[v] and group[u] != "dust":
            ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]], color="#e09a8e",
                    alpha=0.2, lw=0.55, zorder=1)

    def colour(v):
        g = group[v]
        if g == "main":
            return C_BET
        if g == "dust":
            return MUTED
        return seam["pockets"][g]["colour"]

    nodes = sorted(H)
    ax.scatter([pos[v][0] for v in nodes], [pos[v][1] for v in nodes],
               s=[10 + 1.6 * G.degree(v) for v in nodes], c=[colour(v) for v in nodes],
               edgecolors=PAGE, linewidths=0.6, alpha=0.95, zorder=3)

    ax.text(-1.04, 0.80, "Still holding together", color=C_BET, fontsize=10, fontweight="bold")
    ax.text(-1.04, 0.765, "%d characters" % seam["main_at_break"], color=MUTED, fontsize=8.5, va="top")
    for p in seam["pockets"]:
        xs = [pos[u][0] for u in p["ids"]]
        ys = [pos[u][1] for u in p["ids"]]
        ax.text(min(xs) - 0.03, max(ys) + 0.085, p["label"], color=p["colour"], fontsize=10,
                fontweight="bold", va="bottom")
        ax.text(min(xs) - 0.03, max(ys) + 0.075, "%d characters · %s" % (p["size"], p["sub"]),
                color=MUTED, fontsize=7.6, va="top")
    ax.text(-1.04, -0.77, "Scattered: %d characters left alone or in pairs" % len(dust),
            color=MUTED, fontsize=8.5)

    ax.set_title("The Marvel universe once its %d best bridges are gone" % brk,
                 color=INK, loc="left", fontsize=12.5, pad=12)
    ax.set_axis_off()
    ax.set_xlim(-1.08, 1.55)
    ax.set_ylim(-1.2, 0.95)
    fig.tight_layout()
    save(fig, "week3_seams_map.png")
    return pos, group


# --- 7. Chart data ---------------------------------------------------------

def _hist(draws, real):
    """Unit-width bins, widened to leave a little room around our own value so the
    red line never sits on the edge of the axis."""
    draws = np.asarray(draws)
    lo, hi = int(min(draws.min(), real)) - 2, int(max(draws.max(), real)) + 2
    edges = np.arange(lo - 0.5, hi + 1.5, 1.0)
    counts, _ = np.histogram(draws, bins=edges)
    return {"edges": [float(e) for e in edges], "counts": [int(c) for c in counts]}


def chart_data(single, curves, orders, rand, tests, nulls, seam, pos, group, G, names, nrep, nrand):
    brk = seam["break_step"]
    ids = sorted(pos)
    index = {v: i for i, v in enumerate(ids)}
    return {
        "nrep": nrep,
        "cutpoints": [{
            "name": r["name"], "lost": r["lost"], "degree": r["degree"],
            "deg_rank": r["deg_rank"], "bet_rank": r["bet_rank"],
        } for r in single["rows"]],
        "attacks": {
            "nrand": nrand,
            "random": {"mean": [round(float(v), 4) for v in rand.mean(0)],
                       "lo": [round(float(v), 4) for v in np.percentile(rand, 5, axis=0)],
                       "hi": [round(float(v), 4) for v in np.percentile(rand, 95, axis=0)]},
            "series": [{
                "key": key, "label": label,
                "colour": {"betweenness": "real", "degree": "deg",
                           "pagerank": "cfg", "closeness": "er"}[key],
                "curve": [round(float(v), 4) for v in curves[key]],
                "order": [plain(names, v) for v in orders[key]],
                "halving": halving_step(curves[key]),
            } for key, label, _, _ in ATTACKS],
        },
        "nulls": {key: {
            "real": tests[key]["real"],
            "series": [dict(key="swap", label="Shuffled universes",
                            colour="deg",
                            mean=round(tests[key]["mean"], 2),
                            **_hist([d[key]["halving"] for d in nulls], tests[key]["real"]))],
        } for key in ("degree", "betweenness")},
        "seams": {
            "break": brk,
            "main": seam["main_at_break"],
            "pockets": [{
                "label": p["label"], "sub": p["sub"], "size": p["size"],
                "split": p["split_step"], "links": p["internal_links"],
                "colour": {C_CLOSE: "er", C_DEG: "deg", C_PR: "cfg"}.get(p["colour"], "muted"),
                "bridges": [b[0] for b in p["bridges"]],
            } for p in seam["pockets"]],
            "nodes": [{
                "name": plain(names, v), "k": G.degree(v),
                "x": round(float(pos[v][0]), 4), "y": round(float(pos[v][1]), 4),
                "g": group[v], "left": seam["left_at"].get(v),
            } for v in ids],
            "edges": [[index[u], index[v]] for u, v in sorted(G.edges())
                      if u in pos and v in pos and group[u] == group[v] and group[u] != "dust"],
            "removed": [plain(names, v) for v in orders["betweenness"][:brk]],
        },
    }


# --- 8. Main ---------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="20 shuffled universes instead of 100")
    ap.add_argument("--json", action="store_true", help="dump every number to week3_numbers.json")
    args = ap.parse_args()
    nrep = 20 if args.fast else 100
    nrand = 1000

    names, D, GIANT, DGIANT = load()
    n0 = GIANT.number_of_nodes()
    print("Loaded  directed n=%d m=%d | giant n=%d m=%d (directed links among them: %d)" % (
        D.number_of_nodes(), D.number_of_edges(), n0, GIANT.number_of_edges(),
        DGIANT.number_of_edges()))

    # 1 - one at a time
    single = single_removals(GIANT, names)
    print("\nArticulation points: %d. Removing each, who falls off with it:" % len(single["rows"]))
    for r in single["rows"]:
        print("  %-18s k=%3d (#%3d)  betweenness #%3d  cuts off %d: %s" % (
            r["name"], r["degree"], r["deg_rank"], r["bet_rank"], len(r["lost"]), ", ".join(r["lost"])))
    print("  betweenness top 10 that are not articulation points (cut off nobody): %s"
          % ", ".join(single["top_bet_not_cut"]))
    print("  characters any single removal can cut off: %d; pendants (one link): %d; "
          "the extra ones: %s" % (len(single["cut_off_total"]), len(single["pendants"]),
                                  ", ".join(single["cut_off_not_pendant"]) or "none"))

    # 2 - attacks
    print("\nAdaptive attacks on our universe:")
    curves, orders = {}, {}
    for key, label, picker, _ in ATTACKS:
        t = time.time()
        order, curve = attack(GIANT, picker, n0, DG=DGIANT)
        orders[key], curves[key] = order, curve
        print("  %-12s half gone after %3d removals | first ten: %s  (%.0fs)" % (
            label, halving_step(curve), ", ".join(plain(names, v) for v in order[:10]),
            time.time() - t))
    rng = np.random.default_rng(SEED)
    rand = random_attacks(GIANT, n0, nrand, rng)
    rand_halvings = np.array([halving_step(c) for c in rand])
    print("  %-12s half gone after %.1f ± %.1f removals (%d runs; median %d)" % (
        "Random", rand_halvings.mean(), rand_halvings.std(), nrand, np.median(rand_halvings)))
    same = sum(1 for a, b in zip(orders["degree"], orders["betweenness"]) if a == b)
    first_diff = next(i for i, (a, b) in enumerate(zip(orders["degree"], orders["betweenness"])) if a != b)
    print("  degree and betweenness pick the same character at %d of the first 10 steps; "
          "first disagreement at step %d (%s vs %s)" % (
              sum(1 for a, b in zip(orders["degree"][:10], orders["betweenness"][:10]) if a == b),
              first_diff + 1, plain(names, orders["degree"][first_diff]),
              plain(names, orders["betweenness"][first_diff])))
    after = {k: curves[k][10] for k in curves}
    print("  main group after 10 removals: " + ", ".join("%s %.1f%%" % (k, 100 * v) for k, v in after.items()))

    # 3 - compared to what
    print("\nThe same attacks on %d degree-preserving shuffles (%d workers)..." % (
        nrep, max(1, (os.cpu_count() or 2) - 1)))
    t = time.time()
    nulls = null_attacks(GIANT, nrep, SEED)
    print("  done in %.0fs" % (time.time() - t))
    tests = {}
    for key in ("degree", "betweenness"):
        tests[key] = compare(halving_step(curves[key]), [d[key]["halving"] for d in nulls])
        tt = tests[key]
        print("  %-12s ours %d | shuffled %.1f ± %.1f | z %s | %d of %d shuffles as low or lower | p %.3f" % (
            key, tt["real"], tt["mean"], tt["sd"],
            "%.1f" % tt["z"] if tt["z"] is not None else "-", tt["as_low"], nrep, tt["p"]))
    # "Half gone" is a threshold we chose. Check the same comparison at two others,
    # using the full curves the workers already returned.
    def crossing(curve, th):
        below = np.nonzero(np.asarray(curve) < th)[0]
        return int(below[0]) if len(below) else len(curve)

    robustness = {}
    for th in (0.6, 0.4):
        for key in ("degree", "betweenness"):
            t2 = compare(crossing(curves[key], th), [crossing(d[key]["curve"], th) for d in nulls])
            robustness["%s@%.0f%%" % (key, 100 * th)] = t2
            print("  %-12s below %.0f%%: ours %d | shuffled %.1f ± %.1f | z %s | %d of %d as low" % (
                key, 100 * th, t2["real"], t2["mean"], t2["sd"],
                "%.1f" % t2["z"] if t2["z"] is not None else "-", t2["as_low"], nrep))
    thresholds = {}
    for th in (0.8, 0.7, 0.6, 0.5, 0.4, 0.33, 0.25):
        thresholds["%.2f" % th] = {k: crossing(curves[k], th) for k in curves}
        thresholds["%.2f" % th]["random"] = crossing(rand.mean(0), th)
    print("  removals to fall below each threshold: " + "; ".join(
        "%s%%: %s" % (int(float(k) * 100), ", ".join("%s %d" % (kk, vv) for kk, vv in v.items()))
        for k, v in thresholds.items()))

    giants = np.array([d["giant"] for d in nulls])
    print("  (shuffles' own main group before any attack: %.1f ± %.1f of 277)" % (giants.mean(), giants.std()))

    # 4 - the seams
    seam = seams(GIANT, names, orders["betweenness"], curves["betweenness"])
    name_pockets(seam)
    print("\nThe break (betweenness attack): second-largest piece peaks at step %d - "
          "main group %d, second piece %d; first piece of 10+ comes loose at step %s" % (
              seam["break_step"], seam["main_at_break"], seam["second_at_break"], seam["first_piece_10"]))
    for p in seam["pockets"]:
        print("  %s - pocket of %d (%d links inside), loose from step %d, held on through: %s" % (
            p["label"], p["size"], p["internal_links"], p["split_step"],
            ", ".join("%s (%d)" % b for b in p["bridges"])))
        print("    " + "; ".join(p["members"]))

    print("\nFigures:")
    fig_cutpoints(single)
    fig_attacks(curves, rand, names, orders)
    fig_nulls(tests, nulls)
    pos, group = fig_seams(GIANT, names, seam)

    charts = chart_data(single, curves, orders, rand, tests, nulls, seam, pos, group, GIANT, names, nrep, nrand)
    cpath = os.path.join(os.path.dirname(IMG), "data", "week3_charts.json")
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(charts, f, separators=(",", ":"), ensure_ascii=False)
    print("  wrote %s (%.0f kB)" % (os.path.relpath(cpath, os.path.dirname(IMG)),
                                    os.path.getsize(cpath) / 1024.0))

    if args.json:
        out = {
            "n_shuffles": nrep, "n_random_orders": nrand,
            "giant": {"n": n0, "m": GIANT.number_of_edges()},
            "cutpoints": [{k: v for k, v in r.items() if k != "lost_ids"} for r in single["rows"]],
            "cut_off_total": len(single["cut_off_total"]),
            "attacks": {k: {"halving": halving_step(curves[k]),
                            "first_ten": [plain(names, v) for v in orders[k][:10]]} for k in curves},
            "random_halving": {"mean": float(rand_halvings.mean()), "sd": float(rand_halvings.std())},
            "tests": tests,
            "tests_other_thresholds": robustness,
            "removals_to_threshold": thresholds,
            "seams": {k: v for k, v in seam.items() if k not in ("removed_at", "left_at")},
        }
        for p in out["seams"]["pockets"]:
            p.pop("ids", None)
            p.pop("colour", None)
        path = os.path.join(HERE, "week3_numbers.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print("\n  wrote " + path)


if __name__ == "__main__":
    main()
