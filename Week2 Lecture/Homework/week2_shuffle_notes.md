# Week 2 — what survives a shuffle

Companion to `analysis_week2.py` and to the post in `posts/week2.html`.
Answers section 2.11, taking the shuffle-test option ("pick any number you can compute
and shuffle-test it"), and folds in the parts of 2.8 that option depends on.

---

## The question

> **Which of our numbers survive a degree-preserving shuffle?**

Every quantity has a boring explanation available: the degree sequence forces it. A
measurement only becomes a claim once a network that copies the degrees and nothing
else fails to reproduce it.

## Setup

Twelve quantities, three scopes, two nulls, 1000 draws each.

| scope | graph | quantities |
|---|---|---|
| `GIANT` | undirected giant component, n=277 m=1421 | clustering, transitivity, triangles, assortativity, mean path, diameter, max k-core, hub share |
| `FULL` | whole undirected roster, n=303 m=1434 | isolates, components, giant size |
| `DIRECTED` | as harvested, n=303 m=1784 | reciprocity |

Nulls: `double_edge_swap` at 10× the link count (degree-preserving; `directed_edge_swap`
for the directed scope, which holds in- and out-degree separately), and `gnm_random_graph`
(same n and m, nothing else). The configuration model is run on clustering only, as a
demonstration of why not to use it.

Every quantity is a function of a graph, so the measured value and the shuffled values
go through identical code. p-values are two-sided and empirical with the +1/+1
correction, so the floor at 1000 draws is 1/1001 ≈ 0.001.

## What it finds

1. **Clustering is real, and the usual comparison overstates it by half.** 0.320
   measured; 0.037 under `G(n,m)`; **0.155 under the degree-preserving null**. Half the
   famous "9× a random graph" gap is just the existence of hubs. The remaining half is
   structure (z = 18.2, p < 0.001).
2. **The disassortativity is an artefact.** −0.105 measured, −0.122 under the null,
   z = 1.5, p = 0.14. With one node at degree 106 in a population of 277 there is
   nobody for Spider-Man to be similar to, so the negative value is arithmetic. Against
   `G(n,m)` it reads as a solid z = −3.9 finding, which is the trap.
3. **The diameter goes the same way.** 6 measured, 5.47 ± 0.54 under the null, p = 0.45.
4. **Reciprocity is the strongest survivor.** 0.392 against 0.063, z = 46.
5. **The giant component is too small.** 277 against 285.9 ± 0.5, z = −19.4. Given these
   degrees the network should be better connected than it is — week 1's nine-character
   *Strikeforce: Morituri* island is a genuine structural feature, not a degree effect.
6. **Two quantities cannot be tested this way at all.** The hub's share of links and the
   count of isolated characters are functions of the degree sequence, so the null returns
   them unchanged 1000 times out of 1000. Reporting their `G(n,m)` z-scores (54.6 and
   118) would be reporting that we did not deal the links at random.

## Configuration model vs edge swaps

The two "degree-preserving" nulls disagree on clustering: **0.111 vs 0.155**, about five
standard deviations of either one's spread. The configuration model is the wrong one.

It pairs stubs at random, which produces self-loops and repeats; deleting those to get a
simple graph silently stops preserving the degree sequence. It keeps **1318 of 1421
links on average** and never once returned all of them in 1000 draws. The losses land on
the hubs — Spider-Man loses 29.1 of his 106 per draw, Hulk 12.8 of 65, Wolverine 12.0 of
63 — because a high-degree node's stubs have the most chances to collide. Shaved hubs
mean less clustering, so every z-score computed against this null comes out too big.

## Two things to be careful about

- **Round-off is not variance.** A quantity the null fixes gives 1000 identical draws,
  but `np.std` on identical floats returns ~1e-18 rather than 0. Dividing by that turned
  the hub's share of links into a confident, meaningless z of 1.00. The script now
  treats `sd <= 1e-12 * max(1, |mean|)` as zero and reports "fixed by the null".
- **Two verdicts are weak and are labelled as such.** *Mean shortest path* clears
  p < 0.001 but the effect is 2.674 vs 2.602 — seven hundredths of a hop, a statement
  about having 1000 draws rather than about Marvel. *Components* lands on p = 0.050
  exactly (49 of 1000 draws reached 19+), which would flip with another seed. Neither
  would survive a correction for testing twelve quantities at once, and we did not
  apply one.

## Not done

- No convergence check on the swap chain. 10× the link count is the course's rule of
  thumb, not a proof of mixing.
- Mean path and diameter are computed on each draw's own largest component, since a
  `G(n,m)` draw at this density is not always connected. That biases both slightly
  downwards for the permissive null.
