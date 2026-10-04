"""Week 5 - the word is in the sentence. The fight is somebody else's.

Every number the post claims is computed here. Figures go to the site's assets/img/,
the interactive charts' data to assets/data/week5_charts.json, numbers to stdout.
Both paths are found by walking up from this file, so it does not matter which
directory you run it from.

    python analysis_week5.py            # everything, 10,000 label permutations (~3 min)
    python analysis_week5.py --fast     # 1,000 permutations, skip the spaCy page pass
    python analysis_week5.py --json     # also dump every number to week5_numbers.json
    python analysis_week5.py --sample   # dump the labelled sentences we read by hand

The question: the network says A and B are connected, and the prose on A's page
says why. Can we read the relationship off the prose? Four passes.

  1. Count the corpus first, the way the network weeks counted nodes and edges:
     tokens, types, hapaxes, Zipf, Heaps. Section 5.3 and 5.4.
  2. Pull one sentence per edge - a concordance with one line per link - and
     label it with a keyword lexicon: foe, ally, kin. Section 5.5.
  3. Ask week 4's question of the labels: do foe edges cross community
     boundaries more than ally or kin edges? Test against a label permutation,
     which keeps the network and the label counts and breaks only the pairing.
  4. Then read the sentences. Restrict to the ones that name nobody but the two
     characters, and run pass 3 again. One of the two effects survives.

Everything runs on the 303-page week-5 release and the week-1 edges. The
community labels are week 4's frozen Louvain partition, read back out of
assets/data/week4_charts.json so the two posts cannot disagree.
"""

import argparse
import json
import math
import os
import random
import re
import statistics
import zipfile
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np

from pages import load_pages, load_roster, tokenize

HERE = os.path.dirname(os.path.abspath(__file__))


def _find(*candidates):
    """Walk up from this file, so it runs from any directory."""
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

# --- Palette (same tokens as weeks 1-4, so the figures match the site) -----
INK    = "#fcf3f0"
MUTED  = "#b09893"
GRID   = "#5a4441"
PANEL  = "#1d0c0b"
PAGE   = "#0c0403"
C_REAL = "#e0523f"     # the measured value        (red)
C_NULL = "#3d92d6"     # the label permutation     (blue)
C_ER   = "#b78a1c"     # the second comparison     (gold)
C_CLEAN = "#83c575"    # the two-character subset  (green)

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
             .replace(" (comics)", "").replace(" (Marvel Comics character)", "")
             .replace(" (Inhuman)", "").replace(" (Marvel Comics character)", ""))


# --- 1. The corpus, counted ------------------------------------------------
#
# One preprocessing choice, stated once and used everywhere below (5.4 item 2):
# the regex tokenizer in pages.py. Words only - no digits, no punctuation -
# lowercased, with hyphens and apostrophes kept inside a token so Spider-Man
# and O'Grady survive as single types. Nothing is stemmed or lemmatised, and no
# stopwords are removed; where that matters below, it is done explicitly and
# reported both ways.

def corpus_counts(pages):
    tokens = []
    per_page = {}
    for nid, text in pages.items():
        t = tokenize(text)
        per_page[nid] = t
        tokens.extend(t)
    counts = Counter(tokens)
    hapax = [w for w, n in counts.items() if n == 1]
    return tokens, per_page, counts, hapax


def descriptions_counts(roster):
    """The week-1 short descriptions, the corpus the course's own explorable starts on."""
    tokens = []
    for row in roster.values():
        tokens.extend(tokenize(row.get("description", "")))
    return tokens, Counter(tokens)


def zipf_fit(counts, rank_lo=10, rank_hi=1000):
    """Slope of log f against log r over a mid-range window, by least squares.

    Deliberately not fitted over the whole range: the head is too short to
    constrain a line and the tail is a staircase of ties at f = 1, 2, 3.
    """
    freqs = sorted(counts.values(), reverse=True)
    hi = min(rank_hi, len(freqs))
    r = np.arange(rank_lo, hi + 1)
    f = np.array(freqs[rank_lo - 1:hi], dtype=float)
    slope, intercept = np.polyfit(np.log10(r), np.log10(f), 1)
    return -slope, intercept, len(freqs)


def heaps(per_page, order):
    """Types seen so far against tokens seen so far, one point per page."""
    seen = set()
    xs, ys = [], []
    n = 0
    for nid in order:
        for w in per_page[nid]:
            seen.add(w)
        n += len(per_page[nid])
        xs.append(n)
        ys.append(len(seen))
    return xs, ys


def heaps_exponent(xs, ys):
    """V = K n^b, fitted in log-log. b near 0.5 is the textbook value."""
    b, logk = np.polyfit(np.log10(xs), np.log10(ys), 1)
    return b, 10 ** logk


# --- 2. Subword tokenization (5.3) -----------------------------------------

def tiktoken_split_rates(counts, top_n=None):
    """How many Marvel types does o200k_base cut into more than one piece?

    Counted over types, not tokens, and reported by frequency band - a split
    rate over the whole vocabulary is mostly a statement about the hapaxes.
    """
    try:
        import tiktoken
    except ImportError:
        print("  tiktoken not installed - skipping the subword pass")
        return None

    enc = tiktoken.get_encoding("o200k_base")
    types = sorted(counts, key=lambda w: -counts[w])
    if top_n:
        types = types[:top_n]

    pieces = {}
    for w in types:
        # A leading space is how the word actually reaches the model mid-sentence,
        # and it changes the segmentation: " spider" is one token, "spider" is two.
        pieces[w] = len(enc.encode(" " + w))

    bands = [("rank 1-100", 0, 100), ("101-1k", 100, 1000),
             ("1k-10k", 1000, 10000), ("10k+", 10000, len(types))]
    out = {"bands": [], "examples": {}}
    for name, lo, hi in bands:
        sub = types[lo:hi]
        if not sub:
            continue
        split = [w for w in sub if pieces[w] > 1]
        out["bands"].append({
            "band": name, "n": len(sub),
            "split": len(split), "rate": len(split) / len(sub),
            "mean_pieces": statistics.mean(pieces[w] for w in sub),
        })
    worst = sorted(types, key=lambda w: -pieces[w])[:12]
    out["examples"]["most_pieces"] = [
        {"type": w, "pieces": pieces[w], "count": counts[w],
         "segmentation": [enc.decode([i]) for i in enc.encode(" " + w)]}
        for w in worst]
    out["overall"] = {
        "n_types": len(types),
        "split": sum(1 for w in types if pieces[w] > 1),
        "rate": sum(1 for w in types if pieces[w] > 1) / len(types),
    }
    return out


def spacy_sentence_table(sentence):
    """5.3 item 1 and 2: spaCy's tokens and attributes for the 5.2 sentence."""
    try:
        import spacy
    except ImportError:
        return None
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("  en_core_web_sm not installed - skipping the spaCy pass")
        return None
    doc = nlp(sentence)
    rows = [{"text": t.text, "lower": t.lower_, "is_stop": bool(t.is_stop),
             "is_punct": bool(t.is_punct), "lemma": t.lemma_} for t in doc]
    pieces = None
    try:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        pieces = [enc.decode([i]) for i in enc.encode(sentence)]
    except ImportError:
        pass
    return {"tokens": rows, "n_tokens": len(rows), "subword": pieces}


# --- 3. Surface forms and the per-edge concordance -------------------------
#
# To find B on A's page we need the strings a human would actually write for B.
# The roster gives one title per character, often with a disambiguator, and
# sometimes with the civilian name in the parentheses.

STOP_PARENS = {"character", "comics", "marvel comics", "earth-616", "comic",
               "marvel comics character", "new earth"}


def surfaces(name):
    """The strings that count as naming this character, longest first."""
    base = re.sub(r"\s*\([^)]*\)", "", name).strip()
    out = {base}
    m = re.search(r"\(([^)]*)\)", name)
    if m:
        inner = m.group(1).strip()
        if inner.lower() not in STOP_PARENS and not inner.lower().startswith("marvel"):
            out.add(inner)
    # Four characters, so "Rom" and "Box" never match a common English word.
    # Longest first, then alphabetical: sorting on length alone leaves ties to
    # set iteration order, which Python's string hash randomisation changes
    # between runs - and a different first match means a different sentence.
    return sorted({s for s in out if len(s) > 3}, key=lambda s: (-len(s), s))


def load_edges(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if parts[0] == "source":
                continue
            out.append((parts[0], parts[1]))
    return out


def load_weights(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if parts[0] == "source":
                continue
            out[(parts[0], parts[1])] = int(parts[2])
    return out


def load_week4_communities(roster):
    """Week 4's frozen Louvain partition, keyed back to node_id.

    The chart payload stores the display name, so go through the roster rather
    than guessing the id - 'Abomination (character)' is not 'Abomination_(character)'
    and a naive join silently drops every multi-word title.
    """
    path = os.path.join(OUTDATA, "week4_charts.json")
    nodes = json.load(open(path, encoding="utf-8"))["marvel"]["map"]["nodes"]
    by_name = {row["name"]: nid for nid, row in roster.items()}
    comm, names = {}, {}
    missing = []
    for n in nodes:
        nid = by_name.get(n["n"])
        if nid is None:
            missing.append(n["n"])
            continue
        comm[nid] = n["c"]
    if missing:
        raise SystemExit("could not key %d week-4 nodes back to the roster: %s"
                         % (len(missing), missing[:3]))
    cdefs = json.load(open(path, encoding="utf-8"))["marvel"]["map"]["communities"]
    for c in cdefs:
        names[c["i"]] = c["name"]
    return comm, names


SENT_END = re.compile(r"(?<=[.!?])\s")


def sentence_around(text, start, end):
    """The sentence containing [start, end). Wikipedia prose, so split on
    terminal punctuation and accept that '#375 (March 1993)' will occasionally
    cut one short - which is why every count in the post was checked by eye."""
    lo = 0
    for m in SENT_END.finditer(text, 0, start):
        lo = m.end()
    m = SENT_END.search(text, end)
    hi = m.start() + 1 if m else len(text)
    return text[lo:hi].strip()


LEXICON = {
    "foe":  r"enem|foe\b|nemes|villain|rival|battl|fight|fought|defeat|kill|"
            r"murder|attack|destro|revenge|clash",
    "ally": r"\bally\b|allies|friend|team|join|member|partner|aid\b|helps?\b|"
            r"rescue|saves?\b|recruit",
    "kin":  r"marri|wife|husband|\bson\b|daughter|brother|sister|father|mother|"
            r"cousin|niece|nephew|uncle|aunt|parent|twin",
}
LABELS = ("foe", "ally", "kin")


def build_concordance(pages, roster, edges, comm):
    """One row per edge: the sentence on A's page where B is first named.

    Also counts how many *other* roster characters that sentence names, which
    turns out to be the whole story.
    """
    surf = {nid: surfaces(row["name"]) for nid, row in roster.items()}
    pats = {nid: [re.compile(r"\b" + re.escape(s) + r"\b") for s in ss]
            for nid, ss in surf.items()}

    rows = []
    for a, b in edges:
        if a not in comm or b not in comm:
            continue          # outside week 4's giant component
        text = pages[a]
        hit = None
        for p in pats[b]:
            m = p.search(text)
            if m:
                hit = m
                break
        if hit is None:
            rows.append({"a": a, "b": b, "sentence": None})
            continue
        sent = sentence_around(text, hit.start(), hit.end())
        low = sent.lower()
        labs = [k for k, pat in LEXICON.items() if re.search(pat, low)]
        third = 0
        for nid, ps in pats.items():
            if nid in (a, b):
                continue
            if any(p.search(sent) for p in ps):
                third += 1
        rows.append({"a": a, "b": b, "sentence": sent, "labels": labs,
                     "third": third, "cross": int(comm[a] != comm[b])})
    return rows


# --- 4. The test: labels against week 4's communities ----------------------

def crossing_rate(rows, want):
    sub = [r for r in rows if r["labels"] == [want]]
    if not sub:
        return float("nan"), 0
    return sum(r["cross"] for r in sub) / len(sub), len(sub)


def permutation_test(rows, nrep, seed=20260930):
    """Shuffle the labels across edges, keeping the network and every label
    count, and breaking only which edge carries which label.

    This is the null the network weeks' double_edge_swap cannot be: there is
    nothing to rewire. What it holds fixed is everything structural - degrees,
    communities, which pairs are linked - so a z-score here is a statement
    about the association between the label and the boundary, and nothing else.
    """
    labels = [tuple(r["labels"]) for r in rows]
    cross = [r["cross"] for r in rows]

    def rate(labs, want):
        idx = [i for i, l in enumerate(labs) if l == (want,)]
        return sum(cross[i] for i in idx) / len(idx) if idx else float("nan")

    obs = {w: rate(labels, w) for w in LABELS}
    draws = {w: [] for w in LABELS}
    rng = random.Random(seed)
    perm = list(labels)
    for _ in range(nrep):
        rng.shuffle(perm)
        for w in LABELS:
            draws[w].append(rate(perm, w))

    out = {}
    for w in LABELS:
        n = sum(1 for l in labels if l == (w,))
        mu = statistics.mean(draws[w])
        sd = statistics.pstdev(draws[w])
        # Two-sided empirical p with the +1/+1 correction, as in weeks 2-4.
        ge = sum(1 for v in draws[w] if abs(v - mu) >= abs(obs[w] - mu))
        out[w] = {"n": n, "obs": obs[w], "null_mean": mu, "null_sd": sd,
                  "z": (obs[w] - mu) / sd if sd else float("nan"),
                  "p": (ge + 1) / (nrep + 1),
                  "draws": draws[w]}
    out["_baseline"] = sum(cross) / len(cross)
    out["_n"] = len(rows)
    return out


def visibility_by_weight(rows, weights):
    """Does a link with no sentence behind it look different in week 4's weights?"""
    seen = {}
    for r in rows:
        w = weights.get((r["a"], r["b"]))
        if w is None:
            continue
        seen.setdefault(min(w, 6), []).append(r["sentence"] is not None)
    out = []
    for w in sorted(seen):
        v = seen[w]
        out.append({"weight": w, "label": ("%d" % w) if w < 6 else "6+",
                    "n": len(v), "visible": sum(v), "rate": sum(v) / len(v)})
    return out


# --- 5. The rest of the toolbox (5.5, 5.7) ---------------------------------

def collocations(tokens, n=12):
    """Bigrams by raw frequency and by two association measures."""
    try:
        from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder
    except ImportError:
        print("  nltk not installed - skipping collocations")
        return None
    finder = BigramCollocationFinder.from_words(tokens)
    finder.apply_freq_filter(5)
    m = BigramAssocMeasures()
    return {
        "raw": [" ".join(b) for b, _ in
                Counter(finder.ngram_fd).most_common(n)],
        "likelihood_ratio": [" ".join(b) for b in finder.nbest(m.likelihood_ratio, n)],
        "pmi": [" ".join(b) for b in finder.nbest(m.pmi, n)],
    }


def concordance_counts(per_page, word):
    """Where does one word actually occur? Count, and keep a few lines."""
    hits = []
    total = 0
    for nid, toks in per_page.items():
        c = toks.count(word)
        total += c
        if c:
            hits.append((c, nid))
    hits.sort(reverse=True)
    return {"word": word, "total": total, "pages": len(hits),
            "top": [{"page": short(n), "count": c} for c, n in hits[:8]]}


def bow_matrix(pages, roster, comm):
    """5.7: the document-term matrix, and what cosine similarity does with it."""
    try:
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return None

    ids = sorted(pages)
    docs = [pages[i] for i in ids]
    out = {}

    for tag, kwargs in (("raw", {}), ("no_stop", {"stop_words": "english"})):
        vec = CountVectorizer(lowercase=True, token_pattern=r"[A-Za-z][A-Za-z'-]+",
                              **kwargs)
        X = vec.fit_transform(docs)
        terms = vec.get_feature_names_out()
        totals = np.asarray(X.sum(axis=0)).ravel()
        order = np.argsort(-totals)
        out[tag] = {
            "shape": list(X.shape),
            "nnz": int(X.nnz),
            "sparsity": 1 - X.nnz / (X.shape[0] * X.shape[1]),
            "top_terms": [{"term": terms[i], "count": int(totals[i])} for i in order[:10]],
        }
        # Do the ten textual neighbours of a page tend to be its network neighbours?
        S = cosine_similarity(X)
        np.fill_diagonal(S, -1)
        out[tag]["mean_top10_cosine"] = float(np.mean(np.sort(S, axis=1)[:, -10:]))
        out[tag]["neighbours"] = {}
        for who in ("Wolverine_(character)", "Spider-Man", "Thor_(Marvel_Comics)"):
            if who not in pages:
                continue
            i = ids.index(who)
            top = np.argsort(-S[i])[:10]
            out[tag]["neighbours"][short(who)] = [
                {"page": short(ids[j]), "cos": round(float(S[i, j]), 3)} for j in top]

    # The 5.6 hand-built matrix, reproduced (item 1 of 5.7).
    hand = ["Thor fights the X-Men.", "The X-Men fight back.",
            "Thor and Loki fight and fight."]
    vec = CountVectorizer(lowercase=True)
    X = vec.fit_transform(hand)
    out["hand"] = {"vocab": list(vec.get_feature_names_out()),
                   "matrix": X.toarray().tolist()}
    vec2 = CountVectorizer(lowercase=True, token_pattern=r"[A-Za-z][A-Za-z'-]+")
    X2 = vec2.fit_transform(hand)
    out["hand_kept_hyphen"] = {"vocab": list(vec2.get_feature_names_out()),
                               "matrix": X2.toarray().tolist()}
    return out


# --- 6. Figures ------------------------------------------------------------

def fig_labels(allr, clean, fname="week5_labels.png"):
    """The headline: the same measurement, before and after reading the text."""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3), sharey=True)
    titles = ["Every sentence we could find\n(1 line per edge)",
              "Only sentences that name nobody else\n(the same measurement)"]
    for ax, res, title, colour in zip(axes, (allr, clean), titles,
                                      (C_REAL, C_CLEAN)):
        xs = np.arange(len(LABELS))
        obs = [res[w]["obs"] for w in LABELS]
        mu = [res[w]["null_mean"] for w in LABELS]
        sd = [res[w]["null_sd"] for w in LABELS]
        for i in xs:
            ax.add_patch(plt.Rectangle((i - 0.34, mu[i] - 2 * sd[i]), 0.68,
                                       4 * sd[i], facecolor=C_NULL, alpha=0.22,
                                       edgecolor="none", zorder=1))
            ax.plot([i - 0.34, i + 0.34], [mu[i]] * 2, color=C_NULL, lw=1.2,
                    zorder=2)
        ax.scatter(xs, obs, s=120, color=colour, zorder=4, edgecolor=PAGE,
                   linewidth=1.2)
        for i in xs:
            # Keep the labels clear of the null band, which otherwise swallows
            # them whenever the observed value sits inside it.
            top = max(obs[i], mu[i] + 2 * sd[i])
            bot = min(obs[i], mu[i] - 2 * sd[i])
            ax.annotate("z = %+.2f" % res[LABELS[i]]["z"], (i, top),
                        textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=9, color=INK, path_effects=HALO)
            ax.annotate("n = %d" % res[LABELS[i]]["n"], (i, bot),
                        textcoords="offset points", xytext=(0, -15),
                        ha="center", fontsize=8.5, color=MUTED)
        ax.set_xticks(xs)
        ax.set_xticklabels(["foe", "ally", "kin"], fontsize=11)
        ax.set_xlim(-0.6, len(LABELS) - 0.4)
        ax.set_title(title, fontsize=10, color=INK, pad=10)
        ax.grid(axis="y")
        ax.set_axisbelow(True)
        despine(ax)
    axes[0].set_ylabel("share of edges crossing a week-4 community")
    axes[0].set_ylim(0.15, 0.62)
    axes[0].annotate("blue band: label permutation, ±2 sd",
                     (0.02, 0.03), xycoords="axes fraction", fontsize=8.5,
                     color=MUTED)
    fig.suptitle("The foe effect was the other characters in the sentence",
                 fontsize=12.5, color=INK, y=1.02)
    save(fig, fname)


def fig_zipf(full_counts, desc_counts, fname="week5_zipf.png"):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))
    for ax, logscale in zip(axes, (False, True)):
        for counts, colour, lab in ((full_counts, C_REAL, "303 full pages"),
                                    (desc_counts, C_ER, "303 short descriptions")):
            f = sorted(counts.values(), reverse=True)
            r = np.arange(1, len(f) + 1)
            ax.plot(r, f, ".", ms=2.2, color=colour, label=lab, alpha=0.75)
        f = sorted(full_counts.values(), reverse=True)
        r = np.arange(1, len(f) + 1)
        ideal = f[0] / r
        ax.plot(r, ideal, "-", lw=1.1, color=C_NULL, label="ideal Zipf, s = 1")
        if logscale:
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title("log-log", fontsize=10, color=MUTED)
        else:
            ax.set_xlim(0, 120)
            ax.set_title("linear, first 120 ranks", fontsize=10, color=MUTED)
        ax.set_xlabel("frequency rank")
        ax.grid(True)
        ax.set_axisbelow(True)
        despine(ax)
    axes[0].set_ylabel("frequency")
    axes[1].legend(fontsize=8.5, loc="lower left")
    fig.suptitle("Marvel against the ideal curve", fontsize=12.5, color=INK,
                 y=1.01)
    save(fig, fname)


def fig_heaps(curves, fname="week5_heaps.png"):
    fig, ax = plt.subplots(figsize=(6.4, 4.3))
    for (name, xs, ys), colour in zip(curves, (C_REAL, C_ER, C_NULL)):
        ax.plot(xs, ys, "-", lw=1.6, color=colour, label=name)
    ax.set_xlabel("tokens read so far")
    ax.set_ylabel("distinct types seen so far")
    ax.grid(True)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9)
    despine(ax)
    ax.set_title("Heaps' law on the Marvel pages", fontsize=12, color=INK)
    save(fig, fname)


def fig_visibility(vis, fname="week5_visibility.png"):
    fig, ax = plt.subplots(figsize=(6.6, 4.1))
    xs = np.arange(len(vis))
    rates = [100 * v["rate"] for v in vis]
    ax.bar(xs, rates, width=0.62, color=C_REAL, alpha=0.85, zorder=3)
    for i, v in enumerate(vis):
        ax.annotate("%.0f%%" % (100 * v["rate"]), (i, 100 * v["rate"]),
                    textcoords="offset points", xytext=(0, 4), ha="center",
                    fontsize=9, color=INK)
        ax.annotate("n = %d" % v["n"], (i, 2), ha="center", fontsize=8.5,
                    color=PAGE, zorder=4)
    ax.set_xticks(xs)
    ax.set_xticklabels([v["label"] for v in vis])
    ax.set_xlabel("week-4 link weight (times A's article links to B)")
    ax.set_ylabel("% of links with the target named in the prose")
    ax.set_ylim(0, 108)
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    despine(ax)
    ax.set_title("A link nobody wrote a sentence about is a weak link",
                 fontsize=12, color=INK)
    save(fig, fname)


# --- 7. Chart data ---------------------------------------------------------

def _hist(v, bins=28):
    lo, hi = min(v), max(v)
    if hi == lo:
        hi = lo + 1e-9
    edges = np.linspace(lo, hi, bins + 1)
    n, _ = np.histogram(v, bins=edges)
    return {"lo": lo, "hi": hi, "n": n.tolist()}


def labels_payload(allr, clean):
    titles = {"all": "Every sentence we could find",
              "clean": "Only sentences that name nobody else"}
    out = {"panels": [],
           "alt": "Share of edges crossing a week-4 community by label, before "
                  "and after restricting to sentences naming only the pair"}
    for tag, res in (("all", allr), ("clean", clean)):
        out["panels"].append({
            "key": tag,
            "title": titles[tag],
            "baseline": round(res["_baseline"], 4),
            "n_edges": res["_n"],
            "rows": [{
                "label": w, "n": res[w]["n"],
                "obs": round(res[w]["obs"], 4),
                "mu": round(res[w]["null_mean"], 4),
                "sd": round(res[w]["null_sd"], 4),
                "z": round(res[w]["z"], 2),
                "p": round(res[w]["p"], 4),
                "hist": _hist(res[w]["draws"]),
            } for w in LABELS],
        })
    return out


def zipf_payload(full_counts, desc_counts, cap=4000):
    def series(counts):
        f = sorted(counts.values(), reverse=True)
        # Thin the tail: below the cap every rank is a tie at a small integer,
        # so keep one point per distinct frequency instead of 25,000 dots.
        pts = []
        last = None
        for i, v in enumerate(f, start=1):
            if i <= 300 or v != last:
                pts.append([i, v])
                last = v
        if pts[-1][0] != len(f):
            pts.append([len(f), f[-1]])   # keep the end of the tail
        return pts
    return {"full": series(full_counts), "desc": series(desc_counts)}


def heaps_payload(curves):
    return [{"name": n, "xs": xs[::2], "ys": ys[::2]} for n, xs, ys in curves]


# --- 8. Main ---------------------------------------------------------------

SENTENCE_52 = "Spider-Man didn't save Queens; Doctor Strange's portal did!"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true",
                    help="1,000 permutations instead of 10,000")
    ap.add_argument("--json", action="store_true", help="dump every number")
    ap.add_argument("--sample", action="store_true",
                    help="dump labelled sentences for hand checking")
    args = ap.parse_args()
    nrep = 1000 if args.fast else 10000

    print("Week 5 - the word is in the sentence")
    print("=" * 64)

    roster = load_roster()
    pages = load_pages()
    comm, cnames = load_week4_communities(roster)
    edges = load_edges(os.path.join(DATA, "week1_edges.tsv"))
    weights = load_weights(os.path.join(DATA, "week4_edges_weighted.tsv"))
    print("corpus    %d pages, roster %d, week-4 giant component %d"
          % (len(pages), len(roster), len(comm)))

    # 1. Counting the corpus (5.3, 5.4)
    print("\n1. The corpus, counted")
    tokens, per_page, counts, hapax = corpus_counts(pages)
    print("  tokens %d   types %d   hapaxes %d (%.0f%% of types)"
          % (len(tokens), len(counts), len(hapax), 100 * len(hapax) / len(counts)))
    print("  top 10: %s" % ", ".join("%s (%d)" % (w, n)
                                     for w, n in counts.most_common(10)))
    desc_tokens, desc_counts = descriptions_counts(roster)
    print("  short descriptions for comparison: %d tokens, %d types"
          % (len(desc_tokens), len(desc_counts)))

    s_full, _, _ = zipf_fit(counts)
    s_desc, _, _ = zipf_fit(desc_counts, rank_hi=400)
    print("  Zipf slope over ranks 10-1000:  full pages s = %.2f,"
          " descriptions s = %.2f" % (s_full, s_desc))

    # Heaps, in both directions (5.3 item 5)
    deg = Counter()
    for a, b in edges:
        deg[b] += 1
    famous = sorted(pages, key=lambda n: (-deg[n], n))
    curves = [("most-linked character first", *heaps(per_page, famous)),
              ("least-linked first", *heaps(per_page, famous[::-1])),
              ("alphabetical", *heaps(per_page, sorted(pages)))]
    b_exp, K = heaps_exponent(curves[0][1], curves[0][2])
    print("  Heaps: V = %.1f n^%.3f   (final vocabulary %d)"
          % (K, b_exp, curves[0][2][-1]))
    for name, xs, ys in curves:
        print("    %-28s types at half the corpus: %d" % (name, ys[len(ys) // 2]))

    # 2. Subword tokenization (5.3)
    print("\n2. Subword tokenization")
    sw = tiktoken_split_rates(counts)
    if sw:
        print("  o200k_base splits %d of %d Marvel types into >1 piece (%.0f%%)"
              % (sw["overall"]["split"], sw["overall"]["n_types"],
                 100 * sw["overall"]["rate"]))
        for band in sw["bands"]:
            print("    %-12s n=%6d  split %5.1f%%  mean pieces %.2f"
                  % (band["band"], band["n"], 100 * band["rate"],
                     band["mean_pieces"]))
        print("  most pieces: %s" % ", ".join(
            "%s (%d)" % (e["type"], e["pieces"]) for e in sw["examples"]["most_pieces"][:6]))
    sp = None
    if not args.fast:
        sp = spacy_sentence_table(SENTENCE_52)
        if sp:
            print("  spaCy on the 5.2 sentence: %d tokens -> %s"
                  % (sp["n_tokens"], " | ".join(r["text"] for r in sp["tokens"])))
            if sp["subword"]:
                print("  o200k_base on the same sentence: %d pieces -> %s"
                      % (len(sp["subword"]),
                         "|".join(p.replace(" ", "_") for p in sp["subword"])))

    # 3. The concordance, one line per edge
    print("\n3. One sentence per edge")
    rows = build_concordance(pages, roster, edges, comm)
    with_sent = [r for r in rows if r["sentence"]]
    print("  edges inside the giant component: %d" % len(rows))
    print("  with the target named in the prose: %d (%.1f%%)"
          % (len(with_sent), 100 * len(with_sent) / len(rows)))
    print("  with no textual trace at all:       %d (%.1f%%)"
          % (len(rows) - len(with_sent),
             100 * (len(rows) - len(with_sent)) / len(rows)))
    vis = visibility_by_weight(rows, weights)
    for v in vis:
        print("    weight %-3s n=%4d  named in prose %5.1f%%"
              % (v["label"], v["n"], 100 * v["rate"]))

    third = Counter(r["third"] for r in with_sent)
    print("  other roster characters named in the same sentence:")
    for k in sorted(third)[:6]:
        print("    %d others: %4d sentences (%.0f%%)"
              % (k, third[k], 100 * third[k] / len(with_sent)))
    clean_rows = [r for r in with_sent if r["third"] == 0]
    print("  sentences naming nobody but the pair: %d (%.0f%%)"
          % (len(clean_rows), 100 * len(clean_rows) / len(with_sent)))

    lab_counts = Counter(tuple(sorted(r["labels"])) for r in with_sent)
    print("  label combinations: %s" % ", ".join(
        "%s=%d" % ("+".join(k) if k else "none", v)
        for k, v in lab_counts.most_common()))

    # 4. The test
    print("\n4. Do the labels know about week 4's communities? (%d permutations)" % nrep)
    allr = permutation_test(with_sent, nrep)
    clean = permutation_test(clean_rows, nrep)
    for tag, res in (("all sentences", allr), ("pair-only sentences", clean)):
        print("  %s: n=%d, baseline crossing rate %.3f"
              % (tag, res["_n"], res["_baseline"]))
        for w in LABELS:
            d = res[w]
            print("    %-5s n=%4d  obs %.3f  null %.3f+-%.3f  z=%+.2f  p=%.4f"
                  % (w, d["n"], d["obs"], d["null_mean"], d["null_sd"],
                     d["z"], d["p"]))

    # 5. The rest of the toolbox
    print("\n5. The rest of the toolbox")
    col = collocations(tokens)
    if col:
        for k in ("raw", "likelihood_ratio", "pmi"):
            print("  %-16s %s" % (k, ", ".join(col[k][:8])))
    power = concordance_counts(per_page, "power")
    print("  'power' occurs %d times across %d of 303 pages; top: %s"
          % (power["total"], power["pages"],
             ", ".join("%s (%d)" % (t["page"], t["count"]) for t in power["top"][:4])))
    bow = bow_matrix(pages, roster, comm)
    if bow:
        for tag in ("raw", "no_stop"):
            b = bow[tag]
            print("  BoW %-8s shape %s  sparsity %.4f  mean top-10 cosine %.3f"
                  % (tag, b["shape"], b["sparsity"], b["mean_top10_cosine"]))
            print("    top terms: %s" % ", ".join(
                "%s (%d)" % (t["term"], t["count"]) for t in b["top_terms"][:6]))
        print("  Wolverine's 5 nearest pages, stopwords removed: %s"
              % ", ".join("%s %.2f" % (n["page"], n["cos"])
                          for n in bow["no_stop"]["neighbours"]["Wolverine"][:5]))

    # 6. Figures and chart data
    print("\n6. Figures")
    fig_labels(allr, clean)
    fig_zipf(counts, desc_counts)
    fig_heaps(curves)
    fig_visibility(vis)

    charts = {
        "labels": labels_payload(allr, clean),
        "zipf": zipf_payload(counts, desc_counts),
        "heaps": heaps_payload(curves),
        "visibility": vis,
        "corpus": {"tokens": len(tokens), "types": len(counts),
                   "hapax": len(hapax), "zipf_s": round(s_full, 3),
                   "heaps_b": round(float(b_exp), 3)},
    }
    cpath = os.path.join(OUTDATA, "week5_charts.json")
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(charts, f, separators=(",", ":"))
    print("  wrote data/week5_charts.json (%.0f kB)"
          % (os.path.getsize(cpath) / 1024.0))

    if args.sample:
        path = os.path.join(HERE, "week5_sentences.txt")
        rng = random.Random(7)
        with open(path, "w", encoding="utf-8") as f:
            for tag, pool in (("ALL SENTENCES", with_sent),
                              ("PAIR-ONLY SENTENCES", clean_rows)):
                single = [r for r in pool if len(r["labels"]) == 1]
                rng.shuffle(single)
                for w in LABELS:
                    f.write("\n%s / %s\n%s\n" % (tag, w, "=" * 60))
                    k = 0
                    for r in single:
                        if r["labels"][0] != w:
                            continue
                        k += 1
                        if k > 25:
                            break
                        f.write("%2d. %s -> %s  [%s, %d others]\n    %s\n"
                                % (k, short(r["a"]), short(r["b"]),
                                   "crosses" if r["cross"] else "same community",
                                   r["third"], r["sentence"]))
        print("  wrote %s" % os.path.relpath(path, HERE))

    if args.json:
        out = {
            "corpus": {"tokens": len(tokens), "types": len(counts),
                       "hapax": len(hapax),
                       "top10": counts.most_common(10),
                       "desc_tokens": len(desc_tokens),
                       "desc_types": len(desc_counts),
                       "zipf_s_full": s_full, "zipf_s_desc": s_desc,
                       "heaps_b": float(b_exp), "heaps_K": float(K)},
            "subword": sw,
            "spacy": sp,
            "edges": {"in_giant": len(rows), "with_sentence": len(with_sent),
                      "pair_only": len(clean_rows),
                      "third_party": dict(sorted(third.items())),
                      "labels": {"+".join(k) if k else "none": v
                                 for k, v in lab_counts.items()},
                      "visibility_by_weight": vis},
            "test": {tag: {w: {k: v for k, v in res[w].items() if k != "draws"}
                           for w in LABELS}
                     for tag, res in (("all", allr), ("pair_only", clean))},
            "collocations": col,
            "power": power,
            "bow": {k: {kk: vv for kk, vv in v.items()} for k, v in bow.items()}
            if bow else None,
        }
        jpath = os.path.join(HERE, "week5_numbers.json")
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=str)
        print("  wrote %s" % os.path.relpath(jpath, HERE))

    print("\nDone.")


if __name__ == "__main__":
    main()
