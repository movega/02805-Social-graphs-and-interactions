"""Week 2 - shuffle-testing the Marvel network.

Every number the post claims is computed here. Figures go to the site's assets/img/,
numbers go to stdout. Both paths are found by walking up from this file, so it does not
matter which directory you run it from.

    python analysis_week2.py            # 1000 replicates per null (a few minutes)
    python analysis_week2.py --fast     # 200 replicates, for iterating
    python analysis_week2.py --json     # also dump every number to week2_numbers.json

The question: which properties of the network survive a degree-preserving shuffle?
A property that a shuffle reproduces is already implied by the degree sequence and
says nothing more. A property that survives is a real structural claim.

Three scopes, because different quantities need different graphs:
  GIANT     undirected giant component, n=277 m=1421 - clustering, paths, cores
  FULL      whole undirected roster,    n=303 m=1434 - isolates, components
  DIRECTED  as harvested,               n=303 m=1784 - reciprocity
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

HERE = os.path.dirname(os.path.abspath(__file__))


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

# --- Palette (same tokens as week 1, so the figures match the site) --------
INK    = "#fcf3f0"     # --text
MUTED  = "#b09893"     # --muted
GRID   = "#5a4441"
PANEL  = "#1d0c0b"     # --bg-panel
PAGE   = "#0c0403"     # --bg: baked in so the PNG is never transparent
C_REAL = "#e0523f"     # the measured value            (red)
C_DEG  = "#3d92d6"     # degree-preserving null        (blue)
C_ER   = "#b78a1c"     # G(n,m) null                   (gold)
C_CFG  = "#8f7ad6"     # configuration model           (violet)

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
    with open(os.path.join(DATA, "week1_nodes.tsv")) as f:
        header = None
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                continue
            row = dict(zip(header, parts))
            names[row["node_id"]] = row["name"]

    D = nx.DiGraph()
    D.add_nodes_from(names)
    with open(os.path.join(DATA, "week1_edges.tsv")) as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                D.add_edge(parts[0], parts[1])

    FULL = nx.Graph(D)
    FULL.remove_edges_from(nx.selfloop_edges(FULL))
    giant = max(nx.connected_components(FULL), key=len)
    GIANT = FULL.subgraph(giant).copy()
    return names, D, FULL, GIANT


# --- 2. The quantities -----------------------------------------------------
# Each returns a plain float so real and null values go through identical code.

def _largest_cc(G):
    if G.number_of_nodes() == 0:
        return G
    return G.subgraph(max(nx.connected_components(G), key=len))


def q_avg_clustering(G):   return nx.average_clustering(G)
def q_transitivity(G):     return nx.transitivity(G)
def q_triangles(G):        return sum(nx.triangles(G).values()) / 3.0
def q_assortativity(G):    return nx.degree_assortativity_coefficient(G)
def q_max_kcore(G):        return float(max(nx.core_number(G).values()))


def q_avg_path(G):
    """On the replicate's own largest component - a G(n,m) draw at this density
    is not always connected, and an infinite mean would just discard the draw."""
    return nx.average_shortest_path_length(_largest_cc(G))


def q_diameter(G):         return float(nx.diameter(_largest_cc(G)))


def q_hub_share(G):
    """The biggest hub's share of all link endpoints. Included precisely because
    a degree-preserving null cannot move it: it is a control, not a test."""
    deg = [d for _, d in G.degree()]
    return max(deg) / float(sum(deg))


def q_isolates(G):         return float(sum(1 for _, d in G.degree() if d == 0))
def q_components(G):       return float(nx.number_connected_components(G))
def q_giant_size(G):       return float(len(max(nx.connected_components(G), key=len)))
def q_reciprocity(G):      return nx.reciprocity(G)


GIANT_QUANTITIES = [
    ("Average clustering", q_avg_clustering, "{:.4f}"),
    ("Transitivity",       q_transitivity,   "{:.4f}"),
    ("Triangles",          q_triangles,      "{:.0f}"),
    ("Degree assortativity", q_assortativity, "{:+.4f}"),
    ("Mean shortest path", q_avg_path,       "{:.4f}"),
    ("Diameter",           q_diameter,       "{:.0f}"),
    ("Max k-core",         q_max_kcore,      "{:.0f}"),
    ("Hub's share of links", q_hub_share,    "{:.4f}"),
]
FULL_QUANTITIES = [
    ("Isolated characters", q_isolates,   "{:.0f}"),
    ("Components",          q_components,  "{:.0f}"),
    ("Giant component size", q_giant_size, "{:.0f}"),
]
DIRECTED_QUANTITIES = [
    ("Reciprocity", q_reciprocity, "{:.4f}"),
]


# --- 3. The nulls ----------------------------------------------------------

def null_swap(G, rng):
    """Degree-preserving: rewire pairs of links, keeping every degree exact.
    10x the link count is the course's rule of thumb for losing the original."""
    H = G.copy()
    m = H.number_of_edges()
    try:
        nx.double_edge_swap(H, nswap=10 * m, max_tries=200 * m, seed=int(rng.integers(1 << 31)))
    except nx.NetworkXAlgorithmError:
        pass          # too few swappable pairs; the graph is returned as far as it got
    return H


def null_directed_swap(G, rng):
    """Degree-preserving for a directed graph: keeps in- AND out-degree exact."""
    H = G.copy()
    m = H.number_of_edges()
    try:
        nx.directed_edge_swap(H, nswap=10 * m, max_tries=200 * m, seed=int(rng.integers(1 << 31)))
    except nx.NetworkXAlgorithmError:
        pass
    return H


def null_gnm(G, rng):
    """Same nodes and same links, nothing else fixed."""
    return nx.gnm_random_graph(G.number_of_nodes(), G.number_of_edges(),
                               seed=int(rng.integers(1 << 31)))


def null_directed_gnm(G, rng):
    return nx.gnm_random_graph(G.number_of_nodes(), G.number_of_edges(),
                               seed=int(rng.integers(1 << 31)), directed=True)


def null_config(G, rng):
    """Configuration model, then simplified. Keeps the degree sequence only up to
    the self-loops and parallel links that get thrown away - which is the whole
    reason it is in this post."""
    deg = [d for _, d in G.degree()]
    H = nx.Graph(nx.configuration_model(deg, seed=int(rng.integers(1 << 31))))
    H.remove_edges_from(nx.selfloop_edges(H))
    return H


# --- 4. The test ------------------------------------------------------------

def shuffle_test(G, quantities, nulls, nrep, seed=20260909):
    """Measure every quantity on G, then on `nrep` draws from each null.

    Returns {quantity: {"real": v, null_name: {"mean","sd","z","p","draws"}}}.
    The p-value is two-sided and empirical: how often a draw is at least as far
    from the null mean as the real value, with the +1/+1 correction so a value no
    draw ever reaches is reported as p < 1/(nrep+1) rather than a bare 0.
    """
    out = {name: {"real": fn(G)} for name, fn, _ in quantities}

    for null_name, null_fn in nulls.items():
        rng = np.random.default_rng(seed)
        draws = {name: [] for name, _, _ in quantities}
        extra = {"edges": []}
        t0 = time.time()
        for i in range(nrep):
            H = null_fn(G, rng)
            extra["edges"].append(H.number_of_edges())
            for name, fn, _ in quantities:
                draws[name].append(fn(H))
        print("    %-22s %4d draws in %5.1fs" % (null_name, nrep, time.time() - t0))

        for name, _, _ in quantities:
            arr = np.asarray(draws[name], dtype=float)
            real = out[name]["real"]
            mean, sd = float(arr.mean()), float(arr.std(ddof=1))
            # A quantity the null fixes by construction - the hub's share of links
            # under a degree-preserving shuffle - gives identical draws, but the
            # variance still comes back as ~1e-18 of round-off rather than a hard
            # zero. Left alone that turns 0/0 into a meaningless z of ~1.
            if sd <= 1e-12 * max(1.0, abs(mean)):
                sd = 0.0
            z = (real - mean) / sd if sd > 0 else float("nan")
            atleast = int(np.sum(np.abs(arr - mean) >= abs(real - mean)))
            out[name][null_name] = {
                "mean": mean, "sd": sd, "z": z,
                "p": (atleast + 1) / (nrep + 1),
                "draws": arr,
            }
        out.setdefault("_edges", {})[null_name] = {
            "mean": float(np.mean(extra["edges"])),
            "min": int(np.min(extra["edges"])),
        }
    return out


# --- 5. Figures -------------------------------------------------------------

def fig_clustering(res, nrep):
    """Fig 1 - the headline: three nulls, one measured value, and the gap
    between the two degree-preserving ones that is pure methodology."""
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    real = res["Average clustering"]["real"]

    series = [
        ("G(n, m)", "gnm", C_ER),
        ("Configuration model", "config", C_CFG),
        ("Edge swaps", "swap", C_DEG),
    ]
    for label, key, colour in series:
        draws = res["Average clustering"][key]["draws"]
        ax.hist(draws, bins=42, color=colour, alpha=0.72, edgecolor=PAGE,
                linewidth=0.4, label="%s  (mean %.3f)" % (label, draws.mean()))

    ax.axvline(real, color=C_REAL, linewidth=2.2)
    ax.annotate("measured\n%.3f" % real, xy=(real, ax.get_ylim()[1] * 0.93),
                xytext=(-10, 0), textcoords="offset points", ha="right", va="top",
                color=C_REAL, fontsize=9.5, weight="bold", path_effects=HALO)

    ax.set_xlabel("Average clustering coefficient")
    ax.set_ylabel("Draws (of %d)" % nrep)
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", fontsize=8.6)
    despine(ax)
    save(fig, "week2_clustering_nulls.png")


def fig_zscores(rows):
    """Fig 2 - the whole battery on one axis: how many null standard deviations
    the measured value sits from each null's mean."""
    labels = [r["label"] for r in rows][::-1]
    z_deg = [r["z_deg"] for r in rows][::-1]
    z_er = [r["z_er"] for r in rows][::-1]

    y = np.arange(len(labels))
    h = 0.38
    LIM = 30.0
    fig, ax = plt.subplots(figsize=(7.8, 5.4))

    ax.axvspan(-2, 2, color=GRID, alpha=0.30, zorder=0)
    ax.axvline(0, color=MUTED, linewidth=0.9)

    for offset, vals, colour, label in (
            (+h / 2, z_er, C_ER, "vs G(n, m)"),
            (-h / 2, z_deg, C_DEG, "vs degree-preserving swap")):
        # A null that fixes a quantity by construction gives sd = 0 and so no
        # z at all. Drawing that as a zero-length bar would read as "matches the
        # null", the opposite of the truth, so it gets a word instead of a bar.
        finite = [v if np.isfinite(v) else 0.0 for v in vals]
        drawn = [max(-LIM, min(LIM, v)) if np.isfinite(v) else 0.0 for v in finite]
        ax.barh(y + offset, drawn, height=h, color=colour, alpha=0.9, label=label)
        for yi, v in zip(y + offset, vals):
            if not np.isfinite(v):
                ax.text(0.8, yi, "fixed by this null", va="center", ha="left",
                        fontsize=7.4, color=colour, style="italic")
            elif abs(v) > LIM:
                ax.text(np.sign(v) * (LIM - 1), yi, "%.0f " % v, va="center",
                        ha="right" if v > 0 else "left", fontsize=7.5,
                        color=PAGE, weight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_ylim(-0.7, len(labels) - 0.3)
    ax.set_xlabel("z-score  (measured − null mean, in null standard deviations)")
    ax.set_xlim(-LIM - 3, LIM + 3)
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=2, fontsize=8.8)
    ax.text(0, -0.62, "shaded: within 2 sd of the null", ha="center", va="center",
            fontsize=7.8, color=MUTED, style="italic")
    despine(ax)
    save(fig, "week2_zscores.png")


def fig_panels(res_giant, res_full, res_dir, nrep):
    """Fig 3 - six null distributions, so the z-scores in Fig 2 are not taken on
    trust. Blue is the degree-preserving null, gold is G(n,m), red is measured."""
    picks = [
        ("Transitivity",        res_giant, "swap", "gnm"),
        ("Degree assortativity", res_giant, "swap", "gnm"),
        ("Mean shortest path",  res_giant, "swap", "gnm"),
        ("Reciprocity",         res_dir,   "swap", "gnm"),
        ("Isolated characters", res_full,  "swap", "gnm"),
        ("Hub's share of links", res_giant, "swap", "gnm"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.0))
    for ax, (name, res, kdeg, ker) in zip(axes.ravel(), picks):
        real = res[name]["real"]
        allv = [real]
        for key, colour in ((ker, C_ER), (kdeg, C_DEG)):
            draws = res[name][key]["draws"]
            allv += [draws.min(), draws.max()]
            spread = draws.max() - draws.min()
            if spread == 0:
                # This null pins the quantity. Dashed and wider, so it stays
                # visible even when it lands under the measured line.
                ax.axvline(draws[0], color=colour, linewidth=2.6, alpha=0.95,
                           linestyle=(0, (4, 2)))
            else:
                ax.hist(draws, bins=30, color=colour, alpha=0.72,
                        edgecolor=PAGE, linewidth=0.3)
        ax.axvline(real, color=C_REAL, linewidth=2.0)

        # Matplotlib pads a near-degenerate histogram to a silly range - a share
        # of links plotted from -0.4 to 0.5 - so set the window from the data.
        lo, hi = min(allv), max(allv)
        pad = (hi - lo) * 0.10 or (abs(hi) * 0.10 or 1.0)
        ax.set_xlim(lo - pad, hi + pad)

        ax.set_title(name, fontsize=9.5, color=INK, pad=6)
        ax.tick_params(labelsize=7.5)
        ax.set_yticks([])
        despine(ax)
        ax.spines["left"].set_visible(False)

    fig.text(0.5, -0.02,
             "red = measured   ·   blue = degree-preserving shuffle   ·   gold = G(n, m)   "
             "·   dashed = the null pins that value   ·   %d draws each" % nrep,
             ha="center", fontsize=8.6, color=MUTED)
    fig.tight_layout()
    save(fig, "week2_null_panels.png")


def fig_dropped(GIANT, rng_seed, nrep_small):
    """Fig 4 - why the configuration model disagrees with edge swaps: it throws
    links away, and it throws them away at the hubs."""
    rng = np.random.default_rng(rng_seed)
    deg = dict(GIANT.degree())
    lost = {n: 0.0 for n in GIANT}
    kept = []
    for _ in range(nrep_small):
        H = null_config(GIANT, rng)
        kept.append(H.number_of_edges())
        for i, n in enumerate(GIANT.nodes()):
            lost[n] += deg[n] - H.degree(i)
    for n in lost:
        lost[n] /= nrep_small

    ks = np.array([deg[n] for n in GIANT])
    ls = np.array([lost[n] for n in GIANT])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.5),
                                   gridspec_kw={"width_ratios": [1, 1.25]})

    ax1.hist(kept, bins=28, color=C_CFG, alpha=0.8, edgecolor=PAGE, linewidth=0.4)
    ax1.axvline(GIANT.number_of_edges(), color=C_REAL, linewidth=2.2)
    ax1.annotate("real\n%d links" % GIANT.number_of_edges(),
                 xy=(GIANT.number_of_edges(), ax1.get_ylim()[1] * 0.9),
                 xytext=(-8, 0), textcoords="offset points", ha="right", va="top",
                 color=C_REAL, fontsize=9, weight="bold", path_effects=HALO)
    ax1.set_xlabel("Links surviving simplification")
    ax1.set_ylabel("Draws (of %d)" % nrep_small)
    ax1.grid(axis="y"); ax1.set_axisbelow(True); despine(ax1)

    ax2.scatter(ks, ls, s=16, color=C_CFG, alpha=0.75, edgecolor="none")
    ax2.set_xscale("log")
    ax2.set_xlabel("Degree in the real network (log)")
    ax2.set_ylabel("Mean degree lost")
    hub = max(deg, key=deg.get)
    ax2.annotate(hub.replace("_", " "), xy=(deg[hub], lost[hub]),
                 xytext=(-8, -12), textcoords="offset points", ha="right",
                 color=INK, fontsize=9, weight="bold", path_effects=HALO)
    ax2.grid(True); ax2.set_axisbelow(True); despine(ax2)

    fig.tight_layout()
    save(fig, "week2_config_dropped.png")
    return {"kept_mean": float(np.mean(kept)),
            "kept_min": int(np.min(kept)),
            "hub": hub, "hub_degree": deg[hub], "hub_lost": float(lost[hub]),
            "lost_total_mean": float(ls.sum()),
            "top_losers": sorted(((float(lost[n]), n, deg[n]) for n in lost),
                                 reverse=True)[:8]}


# --- 6. Report --------------------------------------------------------------

def verdict(z_deg, p_deg):
    if not np.isfinite(z_deg):
        return "fixed by the null"
    if p_deg > 0.05:
        return "explained by degrees"
    return "survives"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="200 replicates instead of 1000")
    ap.add_argument("--json", action="store_true", help="dump every number to week2_numbers.json")
    args = ap.parse_args()
    nrep = 200 if args.fast else 1000

    names, D, FULL, GIANT = load()
    print("Loaded  directed n=%d m=%d | undirected n=%d m=%d | giant n=%d m=%d" % (
        D.number_of_nodes(), D.number_of_edges(),
        FULL.number_of_nodes(), FULL.number_of_edges(),
        GIANT.number_of_nodes(), GIANT.number_of_edges()))

    print("\nGIANT component, %d replicates:" % nrep)
    res_giant = shuffle_test(GIANT, GIANT_QUANTITIES,
                             {"swap": null_swap, "gnm": null_gnm, "config": null_config}, nrep)

    print("\nFULL roster, %d replicates:" % nrep)
    res_full = shuffle_test(FULL, FULL_QUANTITIES,
                            {"swap": null_swap, "gnm": null_gnm}, nrep)

    print("\nDIRECTED, %d replicates:" % nrep)
    res_dir = shuffle_test(D, DIRECTED_QUANTITIES,
                           {"swap": null_directed_swap, "gnm": null_directed_gnm}, nrep)

    # --- the table the post uses
    rows = []
    for scope, res, quantities in (("giant", res_giant, GIANT_QUANTITIES),
                                   ("full", res_full, FULL_QUANTITIES),
                                   ("directed", res_dir, DIRECTED_QUANTITIES)):
        for label, _, fmt in quantities:
            r = res[label]
            rows.append({
                "label": label, "scope": scope, "fmt": fmt,
                "real": r["real"],
                "deg_mean": r["swap"]["mean"], "deg_sd": r["swap"]["sd"],
                "z_deg": r["swap"]["z"], "p_deg": r["swap"]["p"],
                "er_mean": r["gnm"]["mean"], "er_sd": r["gnm"]["sd"],
                "z_er": r["gnm"]["z"], "p_er": r["gnm"]["p"],
                "verdict": verdict(r["swap"]["z"], r["swap"]["p"]),
            })

    print("\n%-22s %10s | %10s %8s %9s | %10s %8s %9s | %s" % (
        "quantity", "measured", "deg mean", "z", "p", "G(n,m) mean", "z", "p", "verdict"))
    for r in rows:
        print("%-22s %10s | %10.4f %8.2f %9.4f | %10.4f %8.2f %9.4f | %s" % (
            r["label"], r["fmt"].format(r["real"]),
            r["deg_mean"], r["z_deg"], r["p_deg"],
            r["er_mean"], r["z_er"], r["p_er"], r["verdict"]))

    print("\nConfiguration model vs edge swaps (clustering):")
    cm = res_giant["Average clustering"]["config"]
    sw = res_giant["Average clustering"]["swap"]
    print("  config mean %.4f  sd %.4f" % (cm["mean"], cm["sd"]))
    print("  swap   mean %.4f  sd %.4f" % (sw["mean"], sw["sd"]))
    print("  gap    %.4f" % (sw["mean"] - cm["mean"]))
    print("  config kept %.1f of %d links on average (min %d)" % (
        res_giant["_edges"]["config"]["mean"], GIANT.number_of_edges(),
        res_giant["_edges"]["config"]["min"]))
    print("  swap   kept %.1f (exact by construction)" % res_giant["_edges"]["swap"]["mean"])

    print("\nFigures:")
    fig_clustering(res_giant, nrep)
    fig_zscores(rows)
    fig_panels(res_giant, res_full, res_dir, nrep)
    dropped = fig_dropped(GIANT, 20260909, nrep)

    print("\nWhere the configuration model loses its links:")
    print("  %.1f link-endpoints lost per draw; %s alone loses %.1f of its %d" % (
        dropped["lost_total_mean"], dropped["hub"], dropped["hub_lost"], dropped["hub_degree"]))
    for lost, node, k in dropped["top_losers"]:
        print("    %-28s k=%3d  loses %.2f" % (node, k, lost))

    if args.json:
        out = {
            "n_replicates": nrep,
            "graphs": {
                "directed": {"n": D.number_of_nodes(), "m": D.number_of_edges()},
                "full": {"n": FULL.number_of_nodes(), "m": FULL.number_of_edges()},
                "giant": {"n": GIANT.number_of_nodes(), "m": GIANT.number_of_edges()},
            },
            "rows": [{k: v for k, v in r.items() if k != "fmt"} for r in rows],
            "clustering_nulls": {
                "config": {"mean": cm["mean"], "sd": cm["sd"]},
                "swap": {"mean": sw["mean"], "sd": sw["sd"]},
                "gnm": {"mean": res_giant["Average clustering"]["gnm"]["mean"],
                        "sd": res_giant["Average clustering"]["gnm"]["sd"]},
                "real": res_giant["Average clustering"]["real"],
                "config_edges_kept": res_giant["_edges"]["config"]["mean"],
            },
            "config_dropped": {k: v for k, v in dropped.items() if k != "top_losers"},
            "config_top_losers": [{"node": n, "degree": k, "lost": l}
                                  for l, n, k in dropped["top_losers"]],
        }
        path = os.path.join(HERE, "week2_numbers.json")
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        print("\n  wrote " + path)


if __name__ == "__main__":
    main()
