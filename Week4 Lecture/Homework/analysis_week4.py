"""Week 4 - communities, on two networks at once.

Every number the post claims is computed here. Figures go to the site's assets/img/,
chart data to assets/data/, numbers to stdout. All paths are found by walking up from
this file, so it does not matter which directory you run it from.

    python analysis_week4.py            # 500 null draws, 100 Louvain runs
    python analysis_week4.py --fast     # 60 and 25, for iterating
    python analysis_week4.py --json     # also dump every number to week4_numbers.json

The point of running both networks is that only one of them has an answer key.
Wikipedia tells us which century each philosopher belongs to and, for some, which
subfield - so on the philosophers we can ask not just "did the algorithm find
groups" but "are they the right ones". Marvel has no such labels. So we calibrate
on the philosophers and carry the calibration over.

The study guide lists three ways a modularity claim goes wrong: no null model, one
run treated as the answer, and the names you give the groups treated as findings.
This script is arranged so the post can avoid all three.
"""

import argparse
import json
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from networkx.algorithms import community as nxc
from sklearn.metrics import normalized_mutual_info_score

HERE = os.path.dirname(os.path.abspath(__file__))


def _find(*candidates):
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
OUTDATA = os.path.join(os.path.dirname(IMG), "data")

# --- Palette (same tokens as weeks 1-2, so the figures match the site) -----
INK    = "#fcf3f0"
MUTED  = "#b09893"
GRID   = "#5a4441"
PANEL  = "#1d0c0b"
PAGE   = "#0c0403"
C_REAL = "#e0523f"     # the measured value        (red)
C_DEG  = "#3d92d6"     # degree-preserving null    (blue)
C_ER   = "#b78a1c"     # G(n,m) null               (gold)

# One colour per community, in the site's register: warm reds and golds against
# cool blues and violets, all readable on the dark page.
TEAM = ["#e24a3f", "#f8ab5e", "#887b2c", "#83c575", "#0f8774",
        "#90e0ec", "#2784d5", "#ac9cf0", "#904e95", "#f2a3c1"]

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


def short(n):
    """Article titles carry disambiguators nobody says out loud."""
    return (n.replace("_", " ")
             .replace(" (character)", "").replace(" (Marvel Comics)", "")
             .replace(" (comics)", "").replace(" (Marvel Comics character)", ""))


# --- 1. The graphs ---------------------------------------------------------

def _rows(path, has_header):
    """The two releases disagree about whether the column names are commented out,
    so say explicitly which one you are reading."""
    out, header = [], None
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if has_header and header is None:
                header = parts
                continue
            out.append(parts)
    return out


def _undirected(D):
    """Collapse direction, summing weights: a tie counts both ways round."""
    U = nx.Graph()
    U.add_nodes_from(D)
    for u, v, d in D.edges(data=True):
        if u == v:
            continue
        w = d.get("weight", 1)
        if U.has_edge(u, v):
            U[u][v]["weight"] += w
        else:
            U.add_edge(u, v, weight=w)
    return U


def load_marvel():
    meta = {r[0]: {"name": r[1]} for r in _rows(os.path.join(DATA, "week1_nodes.tsv"), True)}
    D = nx.DiGraph()
    D.add_nodes_from(meta)
    for r in _rows(os.path.join(DATA, "week4_edges_weighted.tsv"), False):
        if len(r) < 2:
            continue
        w = int(r[2]) if len(r) > 2 and r[2] else 1
        if D.has_edge(r[0], r[1]):
            D[r[0]][r[1]]["weight"] += w
        else:
            D.add_edge(r[0], r[1], weight=w)
    U = _undirected(D)
    G = U.subgraph(max(nx.connected_components(U), key=len)).copy()
    return meta, D, U, G


def load_philosophers():
    meta = {}
    for r in _rows(os.path.join(DATA, "week4_philosophers_nodes.tsv"), True):
        meta[r[0]] = {"name": r[1], "era": r[4] if len(r) > 4 else "",
                      "subfields": r[5] if len(r) > 5 else ""}
    D = nx.DiGraph()
    D.add_nodes_from(meta)
    for r in _rows(os.path.join(DATA, "week4_philosophers_edges.tsv"), True):
        if len(r) < 2:
            continue
        w = int(r[2]) if len(r) > 2 and r[2] else 1
        if D.has_edge(r[0], r[1]):
            D[r[0]][r[1]]["weight"] += w
        else:
            D.add_edge(r[0], r[1], weight=w)
    U = _undirected(D)
    G = U.subgraph(max(nx.connected_components(U), key=len)).copy()
    return meta, D, U, G


# --- 2. Partitions ---------------------------------------------------------

def labels_of(G, part, order):
    """Partition (list of sets) -> one integer label per node, in a fixed order."""
    lab = {}
    for i, c in enumerate(part):
        for n in c:
            lab[n] = i
    return np.array([lab[n] for n in order])


def nmi(a, b):
    return float(normalized_mutual_info_score(a, b))


def louvain_runs(G, n_runs, order):
    """Louvain is seed-dependent, so one run is a sample, not an answer."""
    runs = []
    for s in range(n_runs):
        part = nxc.louvain_communities(G, seed=s, weight=None)
        runs.append({"part": part,
                     "Q": nxc.modularity(G, part, weight=None),
                     "k": len(part),
                     "labels": labels_of(G, part, order)})
    return runs


def pairwise_nmi(runs):
    n = len(runs)
    M = np.ones((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            M[i, j] = M[j, i] = nmi(runs[i]["labels"], runs[j]["labels"])
    return M


def membership_stability(G, runs, order):
    """Per-character stability: across every pair of runs, how much does the set of
    people sitting with you overlap? 1.0 = always the same company, 0 = never."""
    comm_of = []
    for r in runs:
        d = {}
        for c in r["part"]:
            for n in c:
                d[n] = c
        comm_of.append(d)

    out = {}
    pairs = [(i, j) for i in range(len(runs)) for j in range(i + 1, len(runs))]
    for n in order:
        tot = 0.0
        for i, j in pairs:
            a, b = comm_of[i][n], comm_of[j][n]
            tot += len(a & b) / float(len(a | b))
        out[n] = tot / len(pairs)
    return out


# --- 3. Nulls (the week-2 machinery, now scoring modularity) ---------------

def null_swap(G, rng):
    H = G.copy()
    m = H.number_of_edges()
    try:
        nx.double_edge_swap(H, nswap=10 * m, max_tries=200 * m, seed=int(rng.integers(1 << 31)))
    except nx.NetworkXAlgorithmError:
        pass
    return H


def null_gnm(G, rng):
    return nx.gnm_random_graph(G.number_of_nodes(), G.number_of_edges(),
                               seed=int(rng.integers(1 << 31)))


def null_modularity(G, nrep, seed=20260923):
    """Louvain finds groups in anything. The question is how good a score it gets
    on a network with no groups in it by construction."""
    out = {}
    for name, fn in (("swap", null_swap), ("gnm", null_gnm)):
        rng = np.random.default_rng(seed)
        qs, ks = [], []
        t0 = time.time()
        for i in range(nrep):
            H = fn(G, rng)
            part = nxc.louvain_communities(H, seed=i, weight=None)
            qs.append(nxc.modularity(H, part, weight=None))
            ks.append(len(part))
        print("    %-6s %4d draws in %5.1fs   Q = %.4f ± %.4f" % (
            name, nrep, time.time() - t0, np.mean(qs), np.std(qs, ddof=1)))
        out[name] = {"Q": np.asarray(qs), "k": np.asarray(ks)}
    return out


# --- 4. One pipeline, applied to each network ------------------------------

def kclique(G, ks=(3, 4, 5)):
    out = {}
    for k in ks:
        comms = [set(c) for c in nxc.k_clique_communities(G, k)]
        covered = set().union(*comms) if comms else set()
        counts = {}
        for c in comms:
            for n in c:
                counts[n] = counts.get(n, 0) + 1
        out[k] = {
            "n": len(comms), "covered": len(covered),
            "in_two": sum(1 for n in counts if counts[n] >= 2),
            "overlap_top": sorted(((c, n) for n, c in counts.items() if c >= 2), reverse=True),
        }
    return out


def analyse(G, meta, nrep, nruns, title, truth_keys=()):
    """Identical treatment for both networks, so the numbers are comparable.

    Everything is unweighted: weighted and unweighted modularity are not on the
    same scale, so mixing them would make the two networks incomparable too.
    """
    print("\n" + "=" * 68)
    print("%s: n=%d  m=%d" % (title, G.number_of_nodes(), G.number_of_edges()))
    order = list(G)
    deg = dict(G.degree())

    # Louvain is seed-dependent. Run an ensemble, show its best, report the spread.
    t0 = time.time()
    runs = louvain_runs(G, nruns, order)
    qs = np.array([r["Q"] for r in runs])
    best = int(np.argmax(qs))
    part = sorted(runs[best]["part"], key=len, reverse=True)
    Q_real = float(qs[best])
    M = pairwise_nmi(runs)
    stab = membership_stability(G, runs, order)
    iu = np.triu_indices(nruns, 1)
    kcount = {}
    for r in runs:
        kcount[r["k"]] = kcount.get(r["k"], 0) + 1

    print("  %d Louvain runs in %.1fs" % (nruns, time.time() - t0))
    print("  best (seed %d): %d communities, Q = %.4f" % (best, len(part), Q_real))
    print("  Q across runs  %.4f to %.4f (mean %.4f)" % (qs.min(), qs.max(), qs.mean()))
    print("  group counts   %s" % dict(sorted(kcount.items())))
    print("  run-to-run NMI median %.3f (%.3f to %.3f)" % (
        np.median(M[iu]), M[iu].min(), M[iu].max()))
    for i, c in enumerate(part[:10]):
        print("    %2d (%4d): %s" % (i + 1, len(c), ", ".join(
            meta[n]["name"] for n in sorted(c, key=lambda x: -deg[x])[:5])))

    greedy = sorted(nxc.greedy_modularity_communities(G, weight=None), key=len, reverse=True)
    Q_greedy = nxc.modularity(G, greedy, weight=None)
    nmi_lg = nmi(labels_of(G, part, order), labels_of(G, greedy, order))
    Q_one = nxc.modularity(G, [set(G)], weight=None)
    print("  greedy: %d communities, Q = %.4f, NMI vs Louvain %.3f" % (
        len(greedy), Q_greedy, nmi_lg))
    print("  one community: Q = %.4f" % Q_one)

    Q_weighted = nxc.modularity(G, part, weight="weight")
    strengths = dict(G.degree(weight="weight"))
    print("  same partition scored with weights: Q = %.4f (not comparable to %.4f)" % (
        Q_weighted, Q_real))

    # Does the partition agree with anything Wikipedia already knew?
    truth = {}
    labels_best = labels_of(G, part, order)
    for key in truth_keys:
        vals = [meta[n].get(key, "") for n in order]
        keep = [i for i, v in enumerate(vals) if v.strip()]
        truth[key] = {
            "nmi": nmi([labels_best[i] for i in keep], [vals[i] for i in keep]),
            "n": len(keep),
            "classes": len(set(vals[i] for i in keep)),
        }
        print("  NMI vs %-10s %.3f  (over the %d with a label, %d classes)" % (
            key, truth[key]["nmi"], truth[key]["n"], truth[key]["classes"]))

    print("  nulls, %d draws each:" % nrep)
    nulls = null_modularity(G, nrep)
    nullstats = {}
    for key in ("swap", "gnm"):
        q = nulls[key]["Q"]
        nullstats[key] = {"mean": float(q.mean()), "sd": float(q.std(ddof=1)),
                          "max": float(q.max()),
                          "z": float((Q_real - q.mean()) / q.std(ddof=1)),
                          "beat": int(np.sum(q >= Q_real))}
        print("    %-5s mean %.4f sd %.4f | z = %+.1f | %d of %d reached ours" % (
            key, q.mean(), q.std(ddof=1), nullstats[key]["z"], nullstats[key]["beat"], nrep))

    kdata = kclique(G)
    print("  k-clique communities:")
    for k in sorted(kdata):
        print("    k=%d: %3d groups, %4d of %d placed, %d in two or more" % (
            k, kdata[k]["n"], kdata[k]["covered"], G.number_of_nodes(), kdata[k]["in_two"]))

    return {
        "title": title, "G": G, "meta": meta, "order": order, "deg": deg,
        "part": part, "Q": Q_real, "k": len(part), "best_seed": best,
        "runs": runs, "qs": qs, "M": M, "stab": stab, "kcount": kcount,
        "nmi_pairs": M[iu],
        "greedy": {"k": len(greedy), "Q": Q_greedy, "nmi": nmi_lg},
        "one_Q": Q_one, "Q_weighted": Q_weighted, "strength": strengths,
        "truth": truth, "nulls": nulls, "nullstats": nullstats,
        "kdata": kdata, "nrep": nrep, "nruns": nruns,
    }


# --- 5. Figures ------------------------------------------------------------

def fig_map(res, fname, seed=7, figsize=(9.2, 7.6), min_label=12):
    """The roster, coloured by the community the algorithm put it in.

    One label per community rather than the top-N by degree: the hubs all sit in
    the same dense middle, so labelling them by degree just piles the names on
    top of each other and names nothing.
    """
    G, part, deg, meta = res["G"], res["part"], res["deg"], res["meta"]
    colour = {}
    for i, c in enumerate(part):
        for n in c:
            colour[n] = TEAM[i % len(TEAM)]

    pos = nx.spring_layout(G, seed=seed, k=1.2 / np.sqrt(G.number_of_nodes()),
                           iterations=200, weight=None)
    fig, ax = plt.subplots(figsize=figsize)

    for u, v in G.edges():
        same = colour[u] == colour[v]
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=colour[u] if same else GRID,
                lw=0.34 if same else 0.22, alpha=0.42 if same else 0.14, zorder=1)

    mx = max(deg.values())
    for n in G:
        ax.scatter(pos[n][0], pos[n][1], s=6 + 90.0 * deg[n] / mx, color=colour[n],
                   edgecolor=PAGE, linewidth=0.3, zorder=2)

    handles = []
    for i, c in enumerate(part):
        if len(c) < min_label:
            continue
        # The name of the biggest member, placed over the group's own mass rather
        # than on that member: every tradition's hub is dragged into the same
        # crowded middle, so labelling them where they sit stacks the names.
        top = max(c, key=lambda x: deg[x])
        cx = float(np.median([pos[n][0] for n in c]))
        cy = float(np.median([pos[n][1] for n in c]))
        ax.annotate(meta[top]["name"], (cx, cy), fontsize=9.5, color=INK, weight="bold",
                    path_effects=HALO, zorder=4, ha="center", va="center")
        handles.append(plt.Line2D([0], [0], marker="o", linestyle="none",
                                  markersize=7, markerfacecolor=TEAM[i % len(TEAM)],
                                  markeredgecolor=PAGE,
                                  label="%s  (%d)" % (name_of(res, c), len(c))))

    ax.legend(handles=handles, loc="upper left", fontsize=8.4, labelcolor=INK,
              handletextpad=0.5, borderpad=0.7, labelspacing=0.55)
    ax.set_axis_off()
    fig.tight_layout()
    save(fig, fname)
    return pos, colour


def fig_nulls(results):
    """Modularity against the two nulls, both networks. Louvain scores well on
    noise too - the whole point of the figure."""
    fig, axes = plt.subplots(1, len(results), figsize=(4.9 * len(results), 3.5))
    if len(results) == 1:
        axes = [axes]
    for ax, res in zip(axes, results):
        for key, label, colour in (("gnm", "Random G(n, m)", C_ER),
                                   ("swap", "Degree-preserving", C_DEG)):
            q = res["nulls"][key]["Q"]
            ax.hist(q, bins=34, color=colour, alpha=0.75, edgecolor=PAGE, linewidth=0.4,
                    label="%s  %.3f" % (label, q.mean()))
        ax.axvline(res["Q"], color=C_REAL, linewidth=2.2)
        ax.annotate("real\n%.3f" % res["Q"], xy=(res["Q"], ax.get_ylim()[1] * 0.92),
                    xytext=(-8, 0), textcoords="offset points", ha="right", va="top",
                    color=C_REAL, fontsize=9.5, weight="bold", path_effects=HALO)
        ax.set_title(res["title"], fontsize=10.5, color=INK, pad=6)
        ax.set_xlabel("Modularity Q")
        ax.set_ylabel("Draws (of %d)" % res["nrep"])
        ax.grid(axis="y"); ax.set_axisbelow(True)
        ax.legend(loc="upper left", fontsize=8.2)
        despine(ax)
    fig.tight_layout()
    save(fig, "week4_modularity_nulls.png")


def fig_agreement(phil, marvel):
    """The calibration. How much the algorithm agrees with itself, set against how
    much it agrees with the labels Wikipedia already had."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.6),
                                   gridspec_kw={"width_ratios": [1.15, 1]})

    rows = [
        ("Two Louvain runs\n(philosophers)", np.median(phil["nmi_pairs"]), C_DEG),
        ("Louvain vs era", phil["truth"]["era"]["nmi"], C_ER),
        ("Louvain vs subfield", phil["truth"]["subfields"]["nmi"], C_ER),
        ("Louvain vs greedy", phil["greedy"]["nmi"], "#8f7ad6"),
        ("Two Louvain runs\n(Marvel)", np.median(marvel["nmi_pairs"]), C_REAL),
    ][::-1]
    y = np.arange(len(rows))
    ax1.barh(y, [r[1] for r in rows], color=[r[2] for r in rows], alpha=0.9, height=0.62)
    for yi, r in zip(y, rows):
        ax1.annotate("%.2f" % r[1], (r[1], yi), xytext=(5, 0), textcoords="offset points",
                     va="center", fontsize=9, color=INK, weight="bold")
    ax1.set_yticks(y)
    ax1.set_yticklabels([r[0] for r in rows], fontsize=8.6)
    ax1.set_xlim(0, 1)
    ax1.set_xlabel("Agreement (NMI):  0 = unrelated, 1 = identical")
    ax1.grid(axis="x"); ax1.set_axisbelow(True); despine(ax1)

    for res, colour, label in ((phil, C_DEG, "Philosophers"), (marvel, C_REAL, "Marvel")):
        ax2.hist(res["nmi_pairs"], bins=28, color=colour, alpha=0.7,
                 edgecolor=PAGE, linewidth=0.3, label="%s (median %.2f)" % (
                     label, np.median(res["nmi_pairs"])))
    ax2.set_xlabel("Agreement between two runs of the same algorithm")
    ax2.set_ylabel("Pairs of runs")
    ax2.grid(axis="y"); ax2.set_axisbelow(True)
    ax2.legend(loc="upper left", fontsize=8.4)
    despine(ax2)

    fig.tight_layout()
    save(fig, "week4_agreement.png")


# --- 6. Chart data ---------------------------------------------------------

def _hist(v, bins, lo=None, hi=None):
    v = np.asarray(v, dtype=float)
    if lo is None:
        lo, hi = float(v.min()), float(v.max())
    if hi <= lo:
        hi = lo + 1e-9
    counts, edges = np.histogram(v, bins=bins, range=(lo, hi))
    return {"edges": [round(float(e), 6) for e in edges],
            "counts": [int(c) for c in counts]}


def map_payload(res, pos):
    G, part, deg, meta = res["G"], res["part"], res["deg"], res["meta"]
    order = res["order"]
    idx = {n: i for i, n in enumerate(order)}
    comm = {}
    for i, c in enumerate(part):
        for n in c:
            comm[n] = i
    return {
        "nodes": [{"n": meta[n]["name"], "x": round(float(pos[n][0]), 3),
                   "y": round(float(pos[n][1]), 3), "k": deg[n], "c": comm[n],
                   "s": round(res["stab"][n], 2)} for n in order],
        "links": [[idx[u], idx[v], 1 if comm[u] == comm[v] else 0] for u, v in G.edges()],
        "communities": [{"i": i, "size": len(c), "name": name_of(res, c),
                         "top": [meta[n]["name"] for n in sorted(c, key=lambda x: -deg[x])[:6]]}
                        for i, c in enumerate(part)],
    }


def nulls_payload(res):
    qs = [res["nulls"]["gnm"]["Q"], res["nulls"]["swap"]["Q"]]
    lo = min(float(min(q.min() for q in qs)), res["Q"])
    hi = max(float(max(q.max() for q in qs)), res["Q"])
    pad = (hi - lo) * 0.06
    lo, hi = lo - pad, hi + pad
    return {
        "real": round(res["Q"], 6), "nrep": res["nrep"],
        "series": [
            {"key": "gnm", "label": "Random G(n, m)", "colour": "er",
             "mean": round(float(res["nulls"]["gnm"]["Q"].mean()), 6),
             **_hist(res["nulls"]["gnm"]["Q"], 34, lo, hi)},
            {"key": "swap", "label": "Degree-preserving", "colour": "deg",
             "mean": round(float(res["nulls"]["swap"]["Q"].mean()), 6),
             **_hist(res["nulls"]["swap"]["Q"], 34, lo, hi)},
        ],
    }


# --- 7. Main ---------------------------------------------------------------

# Our names for the groups, read off their biggest members. These are a label we
# put on afterwards, not something the algorithm produced - the post says so.
# Keyed by the group's highest-degree member rather than by position, because
# which seed wins the ensemble decides the order and that is not stable.
NAMES = {
    "Aristotle": "Greeks and Romans",
    "Thomas Aquinas": "Christian theology",
    "Immanuel Kant": "German idealism and after",
    "Ren\u00e9 Descartes": "Early modern Europe",
    "Bertrand Russell": "Analytic and pragmatist",
    "Avicenna": "Islamic golden age",
    "The Buddha": "Indian traditions",
    "Confucius": "Chinese traditions",
    "Karl Marx": "Marx and the Russians",
    "Wolverine (character)": "X-Men",
    "Spider-Man": "Spider-Man's corner",
    "Hulk": "Gamma and brawlers",
    "Doctor Strange": "Occult and horror",
    "Black Panther (character)": "Street-level New York",
    "Adam Warlock": "Cosmic tier",
    "Hercules (Marvel Comics)": "Cosmic tier",
    # A grab-bag: two 2099 characters, a cyborg, a teenage runaway. Calling it a
    # theme would be inventing one.
    "Cloak and Dagger (characters)": "Loose ends",
    "Scarlet Witch": "Avengers family",
    "Black Widow (Natasha Romanova)": "Tech and espionage",
    "Captain Marvel (Marvel Comics)": "Cosmic tier",
}


def name_of(res, community):
    """Label a group by our name for its biggest member, or fall back to saying so."""
    top = max(community, key=lambda n: res["deg"][n])
    return NAMES.get(res["meta"][top]["name"], res["meta"][top]["name"] + "'s group")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    nrep = 60 if args.fast else 500
    nruns = 25 if args.fast else 100

    pmeta, pD, pU, pG = load_philosophers()
    mmeta, mD, mU, mG = load_marvel()
    print("Philosophers  roster %d, giant %d, components %d" % (
        pU.number_of_nodes(), pG.number_of_nodes(), nx.number_connected_components(pU)))
    print("Marvel        roster %d, giant %d, components %d" % (
        mU.number_of_nodes(), mG.number_of_nodes(), nx.number_connected_components(mU)))

    phil = analyse(pG, pmeta, nrep, nruns, "Philosophers", truth_keys=("era", "subfields"))
    marvel = analyse(mG, mmeta, nrep, nruns, "Marvel")

    print("\nFigures:")
    ppos, _ = fig_map(phil, "week4_philosophers_map.png", seed=7, min_label=30)
    mpos, _ = fig_map(marvel, "week4_marvel_map.png", seed=11, figsize=(8.6, 7.0), min_label=8)
    fig_nulls([phil, marvel])
    fig_agreement(phil, marvel)

    charts = {
        "philosophers": {
            "n": pG.number_of_nodes(), "m": pG.number_of_edges(),
            "map": map_payload(phil, ppos),
            "nulls": nulls_payload(phil),
            "nmi": {"pairs": _hist(phil["nmi_pairs"], 28),
                    "median": round(float(np.median(phil["nmi_pairs"])), 4),
                    "min": round(float(phil["nmi_pairs"].min()), 4),
                    "max": round(float(phil["nmi_pairs"].max()), 4),
                    "era": round(phil["truth"]["era"]["nmi"], 4),
                    "subfields": round(phil["truth"]["subfields"]["nmi"], 4),
                    "greedy": round(phil["greedy"]["nmi"], 4)},
            "q": {"min": round(float(phil["qs"].min()), 4),
                  "max": round(float(phil["qs"].max()), 4),
                  "counts": {str(k): v for k, v in sorted(phil["kcount"].items())}},
        },
        "marvel": {
            "n": mG.number_of_nodes(), "m": mG.number_of_edges(),
            "map": map_payload(marvel, mpos),
            "nulls": nulls_payload(marvel),
            "nmi": {"pairs": _hist(marvel["nmi_pairs"], 28),
                    "median": round(float(np.median(marvel["nmi_pairs"])), 4),
                    "min": round(float(marvel["nmi_pairs"].min()), 4),
                    "max": round(float(marvel["nmi_pairs"].max()), 4),
                    "greedy": round(marvel["greedy"]["nmi"], 4)},
            "q": {"min": round(float(marvel["qs"].min()), 4),
                  "max": round(float(marvel["qs"].max()), 4),
                  "counts": {str(k): v for k, v in sorted(marvel["kcount"].items())}},
        },
    }
    os.makedirs(OUTDATA, exist_ok=True)
    cpath = os.path.join(OUTDATA, "week4_charts.json")
    with open(cpath, "w") as f:
        json.dump(charts, f, separators=(",", ":"))
    print("  wrote data/week4_charts.json (%.0f kB)" % (os.path.getsize(cpath) / 1024.0))

    if args.json:
        def dump(res):
            return {
                "n": res["G"].number_of_nodes(), "m": res["G"].number_of_edges(),
                "Q": res["Q"], "k": res["k"], "best_seed": res["best_seed"],
                "q_min": float(res["qs"].min()), "q_max": float(res["qs"].max()),
                "q_mean": float(res["qs"].mean()),
                "group_counts": {str(k): v for k, v in sorted(res["kcount"].items())},
                "nmi_runs": {"median": float(np.median(res["nmi_pairs"])),
                             "min": float(res["nmi_pairs"].min()),
                             "max": float(res["nmi_pairs"].max())},
                "greedy": res["greedy"], "one_community_Q": res["one_Q"],
                "Q_weighted_same_partition": res["Q_weighted"],
                "nulls": res["nullstats"],
                "truth": {k: v for k, v in res["truth"].items()},
                "kclique": {str(k): {kk: vv for kk, vv in res["kdata"][k].items()
                                     if kk != "overlap_top"} for k in res["kdata"]},
                "communities": [{"size": len(c),
                                 "name": name_of(res, c),
                                 "top": [res["meta"][n]["name"]
                                         for n in sorted(c, key=lambda x: -res["deg"][x])[:6]]}
                                for i, c in enumerate(res["part"])],
                "least_settled": [{"name": res["meta"][n]["name"], "degree": res["deg"][n],
                                   "stability": round(res["stab"][n], 3)}
                                  for n in sorted(res["order"], key=lambda x: res["stab"][x])[:10]],
                "most_settled": [{"name": res["meta"][n]["name"], "degree": res["deg"][n],
                                  "stability": round(res["stab"][n], 3)}
                                 for n in sorted(res["order"], key=lambda x: -res["stab"][x])[:10]],
            }
        out = {"nrep": nrep, "nruns": nruns,
               "philosophers": dump(phil),
               "marvel": dump(marvel)}
        jpath = os.path.join(HERE, "week4_numbers.json")
        with open(jpath, "w") as f:
            json.dump(out, f, indent=2)
        print("  wrote week4_numbers.json")


if __name__ == "__main__":
    main()
