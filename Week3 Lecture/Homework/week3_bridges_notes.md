# Week 3 — who holds the Marvel universe together

Companion to `analysis_week3.py` and to the post in `posts/week3.html`.
Answers section 3.12, taking the fragmentation opener ("which single character's removal
fragments the network the most? Is it the same as the highest betweenness? Remove
characters one by one in order of some measure and compare orders"), and runs it against
week 2's degree-preserving null.

---

## The question

> **Which characters is the network actually relying on — and is that more than their
> fame explains?**

## Setup

- Graph: the undirected giant component, n = 277, m = 1,421. PageRank alone uses the
  1,762 directed links among the same 277.
- **Single removals**: every articulation point, removed on its own.
- **Attacks**: adaptive — the measure is recomputed after every removal. Four orders
  (degree, betweenness, closeness, PageRank) plus 1,000 random orders. Ties break on the
  node id, so every run gives the identical order.
- **Null**: 100 degree-preserving rewirings (`double_edge_swap`, 10 × m swaps, as in
  week 2), each attacked by degree and by betweenness. Run in parallel, one process per
  core; about 4 minutes on 12 cores.
- **Measure**: removals until the largest remaining piece falls below a threshold of the
  original 277 (50 % in the headline, 60 % and 40 % as checks). z-scores and two-sided
  empirical p-values with the +1/+1 correction, as in week 2; the p floor at 100 draws
  is 1/101 ≈ 0.01.

## What it finds

1. **No single point of failure matters much.** 13 articulation points. The worst,
   Spider-Man, cuts off 5 characters. Across all 13, exactly 19 characters can be cut off
   by one removal: week 1's 18 pendants plus Rockman.
2. **Top betweenness ≠ top fragmenter.** Second place goes to Black Widow (degree #23,
   betweenness #8, cuts off 3). Six of the betweenness top 10 — Hulk, Wolverine,
   She-Hulk, Hercules, Phoenix, U.S. Agent — cut off nobody.
3. **Targeted orders are far worse than random, and betweenness is the worst.**
   Removals to halve the giant: betweenness 63, degree 73, closeness 78, PageRank 79,
   random 128.5 ± 3.8. Degree and betweenness agree on 6 of the first 10 removals and
   first differ at step 7 (Phoenix vs Hercules). After 10 removals every order still has
   ~93 % connected (257 of 277).
4. **Removing hubs does exactly what the degree sequence predicts.** Degree attack:
   73 vs 75.1 ± 2.1 in the shuffles, z = −1.0, 22 of 100 as fast, p = 0.34.
5. **Removing brokers breaks it sooner than the null — but not further.**

   | threshold | ours | shuffled | z | shuffles as fast |
   |---|---|---|---|---|
   | 60 % | 53 | 64.4 ± 3.6 | −3.2 | 0 of 100 |
   | 50 % | 63 | 72.5 ± 3.3 | −2.9 | 0 of 100 |
   | 40 % | 74 | 76.1 ± 2.4 | −0.9 | 26 of 100 |

   Whole groups come away early in the real network; the shuffles, which have fame but no
   neighbourhoods, shed characters one or two at a time and catch up by 40 %.
6. **The seams.** At the betweenness attack's most destructive step (74 removals: main
   piece 88, second piece 31, 52 characters alone or in pairs) three pockets of five or
   more have broken away:

   | pocket | size | links inside | loose after | mostly held on by |
   |---|---|---|---|---|
   | Other futures, other universes | 8 | 8 | 61 | Star Brand (3), Spider-Man (2), Black Panther (2) |
   | Canada and the teen teams | 24 | 32 | 53 | Wolverine (10), Hulk (7), Cyclops (6), Betsy Braddock (6) |
   | The cosmic block | 31 | 41 | 74 | Spider-Man (10), Doctor Strange (8), Hulk (7) |

## What was checked against Wikipedia (not just asserted)

Every group label and every character claim in the post was checked against the
character's article through the API (intro extract or wiki-source), not written from
memory:

- **Other futures, other universes** — Doom 2099 and Hulk 2099 (intros name the Marvel
  2099 line), Ravage 2099; Justice, Nightmask, Mark Hazzard: Merc (intros name the New
  Universe imprint); Killraven ("post-apocalyptic alternate futures"); Starr the Slayer
  (reintroduced in *newuniversal*, the New Universe reboot); Star Brand (the New Universe
  imprint's 1986–89 series). This pocket is clean: all eight fit.
- **Canada and the teen teams** — Alpha Flight: Northstar, Puck, Guardian, Vindicator,
  Wild Child. Young Avengers: Hulkling, Speed, Iron Lad. Runaways: Alex Wilder, Chase
  Stein. X-Men students / New Mutants / Hellions: Anole, Rockslide, Hellion, Surge. Not
  every member fits (e.g. the Ultimate Wolverine and Iron Man), hence "mostly".
- **The cosmic block** — Eternals: Ajak, Ikaris, Makkari, Thena. Shi'ar / Starjammers:
  Gladiator, Vulcan, Raza Longknife, Ch'od, Korvus. Guardians of the Galaxy: Star-Lord,
  Rocket Raccoon, Bug. Kree: Mahr Vehl, Genis-Vell. Also contains Red Guardian, Yelena
  Belova, Jessica Jones, Gwenpool and others who are not cosmic — the loosest label,
  said as such in the post.
- **Black Widow's three** — Rockman: Timely, *U.S.A. Comics* #1 (August 1941). His
  article links Natasha Romanova only inside "The Black Widow (unrelated to [the modern
  character] of that name)", in the passage on *The Twelve* (2008), which also links The
  Witness. Blue Eagle: alternate-universe character; the only link to Natasha is the
  *Heroes Reborn* (2021) sentence in which Black Widow and Hawkeye kill him.

The pocket labels in `analysis_week3.py` are tied to two member ids each. If a different
removal order produced different pockets, they would be printed as "A pocket of N"
rather than mislabelled.

## Things to be careful about

- **Short names collide.** The roster has three Spider-Women, three Ghost Riders, two
  Human Torches, two Wolverines, two She-Hulks and more. Stripping every bracket made
  "Spider-Woman" appear three times in the removal list. Labels now keep the bracket
  unless it is generic ("character", "comics", "Marvel Comics") or the short name is
  unique.
- **The threshold matters, and was chosen before the check.** The 50 % result was found
  first; 60 % and 40 % were added afterwards as a robustness check, and the 40 % result
  changed the claim from "breaks faster" to "breaks sooner". Above about two thirds
  betweenness, degree and PageRank are tied to within one or two removals; closeness
  trails by three or four.
- **Greedy is not optimal.** Adaptive highest-score-first removal is a heuristic;
  the minimum set of nodes that dismantles the network is a much harder problem.
- **Pockets depend on the exact order**, including tie-breaks. Only the eight-character
  pocket is clean enough to state without "mostly".
- **The null keeps degrees, not clustering.** Week 2 showed the clustering is real; this
  test cannot say whether the early fragmentation comes from it.

## Files

```
analysis_week3.py        every figure, the chart data and every number in the post
week3_bridges_notes.md   this file
week3_numbers.json       written by --json
```
