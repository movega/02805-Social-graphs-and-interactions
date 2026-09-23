# Week 4 — schools, not centuries

Companion to `analysis_week4.py` and to the post in `posts/week4.html`.
Answers section 4.13, and folds in the parts of 4.5, 4.6, 4.7 and 4.10 the post
leans on.

---

## The question

> **Does the network fall into groups, and are they the right ones?**

The first half is nearly free: point any community algorithm at anything and it
returns groups. The second half needs an answer key. The philosophers have one
(era, and a subfield for 322 of them); Marvel has none. So we calibrate on the
philosophers and carry the calibration over.

## Setup

Both networks get identical treatment. Louvain ×100 seeds, greedy modularity,
500 degree-preserving shuffles, 500 G(n,m) draws, k-clique percolation at
k = 3, 4, 5. **Everything unweighted** — see the trap below.

| | philosophers | Marvel |
|---|---|---|
| roster / giant | 1444 / 1374 | 303 / 277 |
| links (undirected) | 9139 | 1421 |
| best of 100 runs | Q = 0.5084, 9 groups | Q = 0.3901, 8 groups |
| Q across runs | 0.4851–0.5084 | 0.3632–0.3901 |
| greedy | Q = 0.4162, 15 groups | Q = 0.3464, 8 groups |
| one community | Q = 0 | Q = 0 |
| degree-preserving null | 0.2221 ± 0.0023 | 0.2481 ± 0.0045 |
| G(n,m) null | 0.2325 | 0.2802 |
| run-to-run NMI (median) | 0.717 | 0.698 |

## What it finds

1. **The groups are traditions.** Greeks and Romans, Christian theology, Islamic
   golden age, Indian traditions, Chinese traditions, early modern Europe,
   German idealism, analytic — plus a stray pair. Instantly recognisable, from
   the links alone.
2. **They are not centuries.** NMI against era is **0.415** over all 1374. The
   Greeks group spans a millennium; the Islamic group crosses two of Wikipedia's
   era lists; the German group is 18th and 19th together.
3. **They are not subjects either.** NMI against subfield is **0.263** over the
   322 who carry one. The 51 logicians land in 7 of the 9 groups, the 39
   ethicists likewise in 7.
4. **Half the score is free.** A network built to have no groups still scores
   0.22–0.23. The real margin is the gap above that, and it is large (z = +123),
   but 0.508 on its own would be a misleading number to quote.
5. **The algorithm agrees with itself more than with anything else.** Two runs:
   0.717. Against era: 0.415. Against greedy: 0.541. Against subfield: 0.263.
   Run-to-run agreement is the ceiling on every other comparison in the post.
6. **Marvel behaves the same way.** Run-to-run 0.698, near-identical to the
   philosophers, so its groups deserve the same credit and no more. The groups
   themselves are an X-Men cluster, a Spider-Man cluster, a cosmic tier, a
   street-level New York cluster and an occult cluster.

## Who moves

No relationship between degree and stability among the 52 philosophers with 50+
links (correlation **0.08**). Aristotle, the biggest hub at 300 links, keeps the
same company in only **42%** of run pairs; Plato at 218 manages 75%. The least
settled of the well-connected are Galileo (29%), Darwin (30%) and Spinoza (36%).
Copernicus lands with the *Greeks and Romans* at 36% stability, which is either
a real fact about whose work his article links to or algorithmic wobble; the
numbers alone cannot separate the two.

## Overlap (4.7, 4.8)

A partition gives everyone exactly one group, which is wrong for both networks.
k-clique percolation on the philosophers:

| k | groups | placed (of 1374) | in two or more |
|---|---|---|---|
| 3 | 19 | 1189 | 29 |
| 4 | 36 | 909 | 86 |
| 5 | 40 | 555 | 112 |

Tighten k and coverage collapses; loosen it and the groups blur together.
Neither setting gives what Louvain gives, and Louvain buys completeness by
pretending nobody has two affiliations.

## The weighted trap (4.10.4)

Scoring the *same* partition with link weights takes the philosophers from
0.5084 to **0.5578** and Marvel from 0.3901 to 0.4850. That is not stronger
structure. Weighted Q normalises by total weight instead of total link count, so
the two are different measurements on different scales and the comparison is
meaningless. The post reports it only because the bigger number is exactly what
gets quoted as progress.

## Two things that nearly went wrong

- **Seed 1 was the worst run.** Our first draft showed the partition from seed 1,
  which turned out to be the lowest-scoring of the ensemble. Showing it while
  quoting a range would have been the "one run as the answer" mistake the study
  guide lists. The script now runs the ensemble first and shows its best,
  labelled as such.
- **NetworkX uses weights by default.** Both of this week's releases ship
  weights, so `louvain_communities(G)` and `modularity(G, part)` were silently
  computing weighted quantities while we described them as unweighted — which
  would also have made the two networks incomparable with each other and with
  week 2. Every Q now passes `weight=None` explicitly.

## Not done

- No Infomap (not installed) and no link-community implementation, so 4.9 is
  answered with k-clique percolation rather than either of its two options.
- No disparity-filter backbone (4.11). The weighted Marvel release would support
  it; we ran out of post.
- The community names are ours, read off the largest members. Not checked
  against any philosophy reference.
- Modularity's resolution limit is not explored. Groups we report as absent may
  simply be below the size the method can see.
