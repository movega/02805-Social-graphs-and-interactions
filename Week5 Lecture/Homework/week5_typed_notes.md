# Week 5 — the word is in the sentence, the fight is somebody else's

Companion to `analysis_week5.py` and to the post in `posts/week5.html`.
Answers section 5.9, taking the first of its openers ("turn links into
relationships… do enemies sit in different communities from week 4?"), and
folds in the parts of 5.3, 5.4, 5.5, 5.6 and 5.7 the post leans on.

Supersedes `week5_prep_notes.md`, written on 23 September when the course page
was still a 404. Two things in it were wrong by the time the exercises landed:
`wordcloud` is never asked for, and the environment it described was another
machine's — `nltk`, `spacy` and `tiktoken` all had to be installed here, and
both `pages.py` and `analysis_week4.py` needed `encoding="utf-8"` on their
roster reads before they would run on Windows at all.

---

## The question

> **The network says A and B are connected, and A's page says why. Can we read
> the relationship off the prose?**

The course's opener assumes we can: pull the sentence where B is mentioned,
label it from a word list, and you have a typed network. We built exactly that,
got a clean significant answer, and then read the sentences. The answer did not
survive. The post is about the gap between those two states.

## Setup

- **Corpus**: the week-5 release, 303 plain-text articles, loaded through
  `pages.py` (which is also where the URL-encoded-filename trap is handled).
- **Preprocessing, stated once** (5.4 item 2): the regex tokenizer in
  `pages.py`. Words only — no digits, no punctuation — lowercased, hyphens and
  apostrophes kept inside a token so `spider-man` and `o'grady` stay single
  types. Nothing stemmed or lemmatised, no stopwords removed. Where a choice
  matters below it is made explicitly and reported both ways.
- **Edges**: the week-1 directed links, restricted to week 4's giant
  component, so 1,762 of 1,784.
- **Communities**: week 4's frozen Louvain partition, read back out of
  `assets/data/week4_charts.json` so the two posts cannot disagree. Keyed back
  to `node_id` through the roster — the chart payload stores display names, and
  joining on those directly silently drops every multi-word title.
- **Labels**: three keyword families — `foe`, `ally`, `kin` — matched against
  the sentence, lowercased. An edge counts under a label only when that family
  is the *only* one matching, so the 208 edges whose sentence trips two or
  three families are excluded rather than arbitrarily assigned. That leaves
  240 `foe`, 305 `ally`, 99 `kin`, and 703 with no label at all.
- **Null**: 10,000 permutations of the labels across the labelled edges. This
  is the one piece of machinery that does not carry over from the network
  weeks — `double_edge_swap` has nothing to rewire here. The permutation keeps
  the network, the communities and every label count fixed and breaks only
  which edge carries which label, so a z-score is a statement about the
  association between label and boundary and nothing else. Two-sided empirical
  p with the +1/+1 correction, as in weeks 2–4; the floor at 10,000 draws is
  1/10,001.

## What it finds

1. **11.7% of the network's edges have no textual trace at all.** 207 of the
   1,762 edges name the target nowhere on the source's page — not under an
   alias, not as a substring. These are navbox and template links: the week-1
   crawl read the rendered HTML, and the week-5 text release strips exactly the
   furniture those links live in. `Anne Weying → Deadpool` is the clean case —
   "Deadpool" does not occur once in her 4,488 characters.
2. **Those invisible links are the weak ones.** Visibility rises monotonically
   with week 4's link weight: 85.2% at weight 1, 95.0% at 2, 97.2% at 3, 98.3%
   at 4, 100% at weight ≥6. A link nobody wrote a sentence about is a link that
   was only made once.
3. **The keyword method gives a beautiful answer.** Over all 1,555 edges with a
   sentence, against a baseline crossing rate of 0.430: `foe` 0.500
   (z = +2.38, p = 0.020), `ally` 0.390 (z = −1.55, p = 0.126), `kin` 0.263
   (z = −3.46, p = 0.0007). Monotone, two of three significant, and exactly the
   story the exercise invites — enemies across boundaries, family inside them.
4. **Most of the labels are wrong.** 901 of the 1,555 sentences (58%) name at
   least one *other* roster character, and that is frequently where the keyword
   belongs. Hand-read, pair-only subset, seed 7: `foe` 5 of 22 correct, `ally`
   9 of 20, `kin` 9 of 20 — **23 of 62, 37%.**
5. **The `foe` errors are not noise, they are sign-flipped.** Seven of those 22
   `foe` sentences describe A and B fighting *side by side* against a third
   party. `Ursa Major → War Machine`, labelled `foe`, reads "helping them and
   War Machine fight off a Skrull attempt". `Dargo Ktor → Hercules`, labelled
   `foe`, reads "Aided by Hercules". So the `foe` bucket is roughly a third
   real enemies and a third real allies, and its crossing rate is a weighted
   average of two opposite effects.
6. **Restricted to sentences naming nobody else, the foe effect is exactly
   zero.** On the 654 pair-only sentences, baseline 0.410: `foe` 0.409
   (z = −0.01, p = 1.00), `ally` 0.375 (z = −0.87, p = 0.43), `kin` 0.220
   (z = −2.56, p = 0.013). The headline in item 3 was sentence crowding. The
   kin effect survives, slightly stronger in effect size and still significant.
7. **Why kin survives and ally does not, when both read ~45% correct.** Not
   precision alone — that is the same for the two. The difference is the shape
   of the errors. `kin`'s failures are mostly third-party noise (a sentence
   about somebody else's brother), which dilutes the measurement toward the
   baseline without reversing it, so a real effect survives attenuated. `foe`'s
   failures actively point the other way, which is enough to cancel it. `ally`
   sits between: its errors include genuine foes (`Blade → Spitfire`, "stakes
   his new teammate"), and whatever true effect it has was never large —
   z = −1.55 before the restriction, which was never significant either.

## The fix that does not work

The obvious lexical patch is to drop sentences carrying a co-operation marker
(`alongside`, `along with`, `helping`, `aided by`, `teamed`, `as part of`). It
catches 27 of the 239 `foe` edges — 11% — where hand reading found 7 of 22, so
roughly a third. Most of the inversions are phrased with no such word at all:
"one of the students who battle the Hulk", "a group of heroes including
Darkhawk". And it changes nothing that matters: crossing rate 0.556 with the
marker, 0.495 without.

The confound is syntactic, not lexical. Doing this properly needs the
dependency parse — is B the object of the conflict verb, or a conjunct of its
subject? — plus coreference for "he", "the pair", "the team". spaCy ships the
parse; we did not use it, and that is the honest limitation.

---

## The numbered exercises

### 5.1 — Did you really read it?

1. **Tokenizer vs. model.** The tokenizer fixes the inventory: where boundaries
   fall, and therefore which integers the model ever sees. It is a fixed,
   deterministic table, trained once and then frozen. Everything about *which*
   token comes next — the probabilities — the model learns from training data.
   The toy generator at the top of the page hides this by shipping the table by
   hand.
2. **Token / type / vocabulary.** In "The Hulk fights the Hulk": 6 tokens; 4
   types if we lowercase (`the`, `hulk`, `fights`— three, in fact), 5 if we keep
   case, because `The` and `the` stay distinct. The vocabulary is the set of
   types. Lowercasing can only *reduce* the number of types or leave it
   unchanged, never increase it, and it reduces only where two forms collide —
   which is why the size of the effect is a property of the corpus, not a fixed
   discount.
3. **Order.** raw characters → tokenizer → token pieces → token IDs → model.
   The tokenizer decides that `New York` is two pieces; nothing downstream can
   put them back together, which is why 5.2 item 3 matters.
4. **Lowercasing**, thrown away: harmless for "which Marvel pages talk about
   families", where `Brother` and `brother` mean the same. Destructive for
   "which words are proper names" — on our corpus it is what merges the Human
   Torch's `Torch` with a literal torch.
5. **BPE.** Starts from the characters (or bytes) of the training text, with
   every one of them in the vocabulary. Repeats: find the most frequent
   adjacent pair of current units, merge it into one new unit, record the merge.
   Stops at a target vocabulary size. Because the base is single characters,
   any unseen word can always be spelled out piece by piece, so nothing is ever
   fully out-of-vocabulary — it just costs more tokens. Our corpus shows the
   cost: `will-they-won't-they` takes 8 pieces.

### 5.2 — Tokenization, by hand

Sentence: `Spider-Man didn't save Queens; Doctor Strange's portal did!`

Rules declared first: keep hyphens inside a word, so `Spider-Man` is one token;
split clitics, so `did` + `n't` and `Strange` + `'s`; punctuation is its own
token.

`Spider-Man | did | n't | save | Queens | ; | Doctor | Strange | 's | portal |
did | !`

**12 tokens, 11 types** — `did` occurs twice. Our first written answer was
13/13, and both halves were wrong: we miscounted the splits and forgot that
`did` repeats. Recorded here because 5.3 asks us to compare against spaCy.

- **After lowercasing**: 12 tokens, still 11 types. No two tokens here differ
  only by case, so the count does not move. The exercise asks why some counts
  stay the same — this is the case.
- **After dropping punctuation**: 10 tokens, 9 types.
- **Our stopword set** `{did, n't, 's, the}`: removes `did` twice, `n't` and
  `'s`, leaving 6 tokens. `Queens` and `portal` survive. The *relative*
  frequency of everything surviving rises, which is the trap in item 5.
3. **`New York` as two tokens.** Named-entity recognition is the task that puts
   them back together; chunking or phrase detection would too. Another case
   where boundaries and the object of interest disagree: negation. `didn't
   save` splits into three tokens and the thing we care about — that the saving
   did not happen — lives in none of them individually.
4. **Subword by hand**, vocabulary `un, believ, able, spider, man, hat, tan,
   wak, anda` plus every letter, longest match left to right:
   - `unbelievable` → `un + believ + able` (3)
   - `spiderman` → `spider + man` (2)
   - `wakanda` → `wak + anda` (2)
   - `manhattan` → `man + hat + tan` (3)
   - `thanos` → `t + h + a + n + o + s` (6)
   `thanos` costs the most, because none of its substrings are in the
   vocabulary. Still better than nothing: six tokens is something the model can
   learn from, where an `<unk>` throws away even which unknown word it was.
5. **`power` across two communities.** Lowercase: yes — `Power` at the start of
   a sentence is not a different word. It does also merge the codename `Power
   Man`, which argues for running the comparison both ways. Lemmatise: no —
   `power`, `powers` and `powered` are plausibly different usages and we want
   to see that. Remove stopwords: **no, and this is the trap.** We are
   comparing `count(power) / total tokens`. Removing stopwords removes no
   `power` token but shrinks the denominator by roughly half, so every rate
   doubles. If two communities have different stopword rates — and longer,
   more heavily-edited pages do — the comparison moves for a reason that has
   nothing to do with power.

### 5.3 — Tokenization, as code

**spaCy gives 14 tokens** against our 12:

`Spider | - | Man | did | n't | save | Queens | ; | Doctor | Strange | 's |
portal | did | !`

Two disagreements, and why each tokenizer chose as it did:

- **`Spider | - | Man`, three tokens where we had one.** spaCy treats an infix
  hyphen as a separator, because a parser wants the hyphen as a visible
  relation between two words. We kept it whole because in this corpus
  `Spider-Man` is a name and splitting it destroys the thing we are counting.
  Neither is right; they are built for different jobs.
- **`did | n't`** — agreement, and `Strange | 's` likewise. spaCy's clitic
  rules match the ones we wrote down by hand.

**`o200k_base` gives 12 pieces**, and the spaces are the story:

`Spider | -Man | ␣didn't | ␣save | ␣Queens | ; | ␣Doctor | ␣Strange | 's |
␣portal | ␣did | !`

The leading space lives *inside* the token. `-Man` is a single piece, and so is
`␣didn't` — the subword tokenizer does not split the contraction that both
word-level tokenizers did, because `didn't` is frequent enough in its training
text to have earned its own entry. The space is not cosmetic: `encode("spider")`
gives 2 tokens, `encode(" spider")` gives 1. That is why
`tiktoken_split_rates` encodes `" " + word` — mid-sentence, the second form is
what the model actually sees.

On the corpus, under the stated preprocessing: **690,709 tokens, 29,737 types,
11,769 hapaxes (40% of types)**. Top ten: `the` (45,470), `and`, `of`, `to`,
`in`, `as`, `is`, `by`, `his`, `with` — not one content word. The course quotes
727,000 tokens / 27,000 types / 36% hapax; we are 5% below on tokens and 10%
above on types because our regex drops digits and punctuation entirely (losing
tokens) and keeps hyphenated compounds whole (creating types like
`blackwater-meets-nascar`). Item 2 of 5.7 asks for exactly this explanation.

**The preprocessing decision that changes an answer**: keeping or splitting
hyphens. Keep them and `spider-man` is one type. Split them and those
occurrences land on `spider` and `man`, where `man` is already a frequent
common noun — so "which character is most talked about" quietly becomes "which
character has a one-word codename". Our entire edge-labelling pass depends on
the first choice, because it matches surface forms like `Spider-Man` against
the raw text.

**Heaps' law** (figure: `assets/img/week5_heaps.png`, produced by the script but
not used in the post): V = 22.6 · n^0.534, so b ≈ 0.53, close to the textbook 0.5. The
curve does not flatten — on log-log it is near-straight over three decades,
which is the point: a fixed word vocabulary never stops growing. Reading the
most-linked characters first reaches 25,904 of the 29,737 types by half the
corpus; reading the least-linked first, only 14,728. **Minor characters bring
new words.** Reversing the order matters because the famous pages are long and
share the same Wikipedia boilerplate, while the obscure ones each drag in their
own one-off vocabulary.

**Subword splits**: o200k_base splits 17,258 of the 29,737 types (58%) into
more than one piece, and the rate tracks frequency almost perfectly — 4% of the
top 100 types, 13% of ranks 101–1k, 36% of 1k–10k, 71% beyond 10k, with 2.02
mean pieces in the tail. What gets split is hyphenated compounds, names and
coinages: `man-thing-thang-thoom` (7), `plasti-steel-reinforced` (7). That is
the argument for subwords in one number — a fixed 200k vocabulary spends one
token each on the hundred words that are a third of the corpus, and still has
something to say about a word it has never seen.

### 5.4 — Is Marvel Zipf-like?

**Predicted first** (🧠): two reasons the short-description curve would deviate
from the ideal — (a) 5,015 tokens is far too small, so the tail is a staircase
of ties at f = 1 rather than a line, and (b) the descriptions are templated, so
`published`, `comics`, `marvel` and `american` are pushed far above their
natural rank by repetition rather than by use. Prediction for the full pages:
closer to the ideal through the middle, because the corpus is 140× larger, but
still with a flat head, because the boilerplate survives at full length too.

**Measured**: the Zipf slope over ranks 10–1,000 is **s = 0.90 for the full
pages and s = 1.02 for the descriptions**. Both near 1. The full-page curve is
visibly straighter over more decades, so the prediction held — and reason (a)
is the one that explains the difference. The description curve's problem was
sample size, not templating. Templating is still visible, but as a flat
shoulder in the top 30 ranks rather than as a bend.

**Is a straight-ish log-log line enough to conclude Zipf?** No. It supports
"frequency falls off roughly as a power of rank through the middle of the
range". It does not establish a power law: a lognormal over the same range
looks the same by eye; the head is a handful of points that constrain no fit;
and the tail is dominated by ties at small integers, so its apparent
straightness is partly an artefact of plotting rank against a staircase. Note
also that our own two fitted slopes differ (0.90 against 1.02) on corpora drawn
from the same source, which is itself a reason not to read much into one number.
Before claiming more we would want the fit over separately-chosen windows, a
comparison against a fitted lognormal, and the same measurement on independent
halves of the corpus. This is week 2's discipline on the degree distribution,
and the rank-frequency plot is literally that week's CCDF with the axes swapped.

**More and less Zipf-like**: *more* — a large single-author novel, Lestrade's
Moby Dick case, because it is one register with one vocabulary and no
templating. *Less* — a corpus of form submissions or log lines, where a handful
of fixed strings repeat exactly and almost nothing is in the tail.

### 5.5 — Context and local order

**The chosen word is `power`**, which occurs **784 times across 188 of the 303
pages**. The concordance separates uses that the single count of 784 merges:
superhuman ability ("searching for an immense power source"), a title or
codename (`The Power of Warlock` — a comic title; `Power Man`), and ordinary
political or physical senses. Its highest-count pages are Scarlet Witch (59),
Iron Fist (30), Power Man (28) and Star Brand (26) — and Power Man is on that
list for the codename, not the concept, which no frequency table would reveal.

`similar()` answers a different question: which other words occupy the same
immediate left-and-right contexts. On this corpus it returns

> `powers the and time team character series body avengers story death name`

which is instructive in the way the page warns about. `powers` is a genuine
near-relation; `the` and `and` are there because the corpus is small enough
that a handful of repeated Wikipedia frames (`the ___ of`) dominate the context
counts. Distributional similarity is not synonymy, and on 690k tokens it is
mostly a report on boilerplate.

**Bigrams, three rankings** (frequency filter ≥5):

| ranking | top of the list |
|---|---|
| raw frequency | `of the`, `in the`, `to the`, `and the`, `with the`, `by the` |
| likelihood ratio | `of the`, `in the`, `captain america`, `comic book`, `ghost rider` |
| PMI | `jb blanc`, `kavita rao`, `nintendo ds`, `arnim zola`, `avi arad` |

Raw frequency returns English. Likelihood ratio keeps the frequent pairs but
lets real collocations through — `captain america` (569 occurrences) becomes
visible because it is both common *and* tightly bound. PMI inverts the ranking
entirely and returns voice actors and licensed platforms: pairs where both
words are rare and occur almost only together, so the ratio against their
independent probabilities is enormous. `captain america` is nowhere under PMI,
because `captain` and `america` are each common enough alone to discount it.
PMI with no frequency floor is a rare-pair detector; that is what the filter is
for, and ≥5 is still not enough to stop it.

One artefact worth recording: **`the the` appears in the likelihood-ratio top
ten, 28 times.** It is real, and it is our own doing — the regex tokenizer
drops punctuation without inserting a boundary, so `…of the. The next…` becomes
`the the`. Sentence boundaries would have to be tokens for this to go away. It
is the tokenizer's fingerprint turning up in the results, which is exactly what
section 2 of the page warned about.

**Same unigrams, different order** (🧠): *"Venom hunts Spider-Man"* and
*"Spider-Man hunts Venom"*. Unigram counts are identical — `{venom: 1,
hunts: 1, spider-man: 1}` — and no Bag-of-Words vector can tell them apart. The
bigram `venom hunts` occurs in the first and not the second; `spider-man hunts`
does the reverse. This is not a toy concern for us: it is the direction problem
in our own edge labels, and the reason the `foe` bucket holds victims and
aggressors indiscriminately.

**Verified by hand in the raw text** (🔬): `the` at 45,470 corpus-wide, of which
`Scarlet_Witch.txt` contributes 813 — recounted two of its paragraphs by eye.
The bigram `captain america` at 569. One `power` concordance hit on
`Iron_Fist_(character).txt` (30 there), confirmed in context. No disagreement
between code and text, but the exercise is right that hand-checking is the only
thing that catches what `the the` turned out to be.

**The AI-drafted report, rewritten honestly.** The original:

> "The Marvel corpus is dominated by the language of publishing rather than
> heroism: the most frequent words are the, of, Marvel, Comics and published.
> Frequency against rank is a straight line on log-log axes, which proves the
> corpus follows Zipf's law. And power occurs 1,204 times, making it the
> central theme of the Marvel universe."

Three flaws. (1) `the` and `of` are facts about English, not about publishing,
so the evidence does not support the premise — on the full pages the top ten
are *all* function words, and `marvel` only reaches the top once stopwords are
removed. (2) A straight-ish log-log line does not *prove* a power law, for the
reasons in 5.4. (3) 1,204 is a raw count with no denominator, no comparison
corpus and no inspection — and it merges several senses of `power`, one of
which is a codename. (Our own count under our own tokenization is 784, which
makes the fourth point: the number is a property of the preprocessing too.)

Honestly, in three sentences:

> Under one stated tokenization, the 303 full Marvel pages give 690,709 tokens
> and 29,737 types, whose ten most frequent are all English function words;
> once NLTK's stopwords are removed the top of the list becomes `marvel`,
> `character`, `new`, `appears` and `series`, which is the language of
> encyclopedia-writing rather than of heroism. Frequency against rank is close
> to straight on log-log axes with a slope of 0.90 over ranks 10–1,000, which
> is consistent with a Zipf-like distribution through the middle of the range
> but does not establish one. `power` occurs 784 times across 188 of the 303
> pages, and reading the concordance shows that count mixing several distinct
> senses including the codename `Power Man`, so it is evidence about vocabulary
> rather than about what the Marvel universe is about.

### 5.6 — Bag of Words, by hand

Documents: `Thor fights the X-Men.` / `The X-Men fight back.` /
`Thor and Loki fight and fight.` Lowercased, punctuation dropped, `x-men` kept
whole. Vocabulary, alphabetical:

`and, back, fight, fights, loki, the, thor, x-men`

| | and | back | fight | fights | loki | the | thor | x-men |
|---|---|---|---|---|---|---|---|---|
| D1 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 |
| D2 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | 1 |
| D3 | 2 | 0 | 2 | 0 | 1 | 0 | 1 | 0 |

- **D1 and D2 share** `the` and `x-men`. **D3 connects** to D1 through `thor`
  and to D2 through `fight`.
- **The `fight` column** reads: D1 never uses that exact form, D2 uses it once,
  D3 twice. `fight` and `fights` get separate columns because the matrix keys
  on the surface form; **lemmatisation** is the step that merges them (stemming
  would too, more crudely).
- **Predicted changes**: add another `fight` to D2 and only cell (D2, `fight`)
  moves, 1 → 2, with the shape still 3×8. Add a brand-new word to D1 and a new
  column appears in alphabetical position, shape 3×9, the column 1 in D1 and 0
  elsewhere, every other cell untouched.
- **Losing word order is acceptable** for "which pages are about the X-Men" —
  topicality survives. It is close to useless for "who attacks whom", which is
  our post's question, and precisely why the post ends where it does.

### 5.7 — Bag of Words on Marvel, as code

`CountVectorizer` on the three documents returns **8 terms, like ours, but not
the same 8**:

`and, back, fight, fights, loki, men, the, thor`

`x-men` is gone and `men` has taken its place. The cause is the default
`token_pattern`, `(?u)\b\w\w+\b`: it requires two or more word characters, so
it splits on the hyphen and then discards the leftover single-character `x`
entirely. The vocabulary is the same size by coincidence — one term lost, one
gained. Passing `token_pattern=r"[A-Za-z][A-Za-z'-]+"` reproduces our
hand-built matrix cell for cell. The default also lowercases, which we had
done anyway.

On the full corpus, one page per document:

| | raw counts | stopwords removed |
|---|---|---|
| shape | 303 × 29,737 | 303 × 29,440 |
| zero cells | 97.42% | 97.74% |
| top terms | `the`, `and`, `of`, `to`, `in`, `as` | `marvel`, `character`, `new`, `appears`, `series` |
| mean top-10 cosine | 0.835 | 0.286 |

The vocabulary is not the 27,000 the course quotes, for the reasons in 5.3.

**One column, traced back**: `power` — 784 occurrences over 188 pages, highest
on Scarlet Witch (59) and Iron Fist (30). Opening both: Scarlet Witch's count
is genuine, recurring through a long section on the limits of her
reality-warping; Iron Fist's is substantially codename and a repeated phrase
about chi. The counts both make sense and mean different things, which is the
lesson.

**The one preprocessing change**: removing stopwords. NLTK's English list has
198 entries, 168 of which occur in our corpus, and the matrix shape barely
moves (29,737 → 29,440 — the two numbers differ by 297 rather than 168 because
`CountVectorizer`'s tokenization is not ours). Sparsity rises slightly. The top
of the term list changes completely. And the number that actually matters moves
hard: **mean cosine to a page's ten nearest neighbours falls from 0.835 to
0.286.** With raw counts every page resembles every other page, because `the`
dominates every vector and the angle between two documents is mostly the angle
between their stopword profiles. Removing them is what makes cosine mean
anything at all.

Wolverine's nearest pages after removal: Wolverine (Ultimate Marvel) 0.74,
Cyclops 0.40, Jubilee 0.33, Storm 0.33, Jean Grey (film series) 0.32 — the
X-Men, recovered from word counts by something never told the links exist.
That is the course's point about language rediscovering the network, and it is
also a warning about our own post: text similarity and network proximity are
correlated, so a typed-edge result that happens to track community structure
needs the permutation null before it means anything.

**What this matrix can and cannot answer.** It can answer which pages share
vocabulary, which terms concentrate in which community, how long and how
repetitive each page is, and which pairs talk alike without linking. It cannot
answer anything with a direction or a role in it — who attacks whom, who is
whose father — because the representation threw the order away. Our post needed
exactly that, which is why it ends by pointing at the dependency parse rather
than at a bigger matrix.

### 5.8 — Ship an explorable

Not shipped this week. The post's two interactive figures — the label panels
with their permutation histograms, and the Zipf curve toggling between the
short descriptions and the full pages — cover the ideas we most wanted easier
to see.

---

## Reproducing it

```
cd "Week5 Lecture/Homework"
python pages.py                     # corpus summary, validates against the roster
python analysis_week5.py            # everything; ~3 min, 10,000 permutations
python analysis_week5.py --fast     # 1,000, for iterating
python analysis_week5.py --json     # also dump week5_numbers.json
python analysis_week5.py --sample   # dump week5_sentences.txt, the hand-read sample
```

Needs `spacy` (with `en_core_web_sm`), `tiktoken`, `nltk` (with `punkt`,
`stopwords`, `gutenberg`) and `scikit-learn`, on top of the numpy/matplotlib
set the network weeks used.

**One reproducibility bug, found and fixed.** `surfaces()` originally sorted a
character's surface forms by length alone. Ties were then broken by set
iteration order, which Python's string hash randomisation changes between
runs — so a different alias matched first, a different sentence came back, and
the label counts moved (`foe` was 239 one run and 240 the next). Sorting on
`(-len, alphabetical)` fixed it; two consecutive runs now agree to the last
digit. Every number above is from the deterministic version, and the hand-read
sample was re-read against the regenerated sentences.

## Caveats

- **The labels are 37% correct** on a hand-read sample of 62. Every aggregate
  in the post inherits that. It is the post's subject rather than a footnote,
  but it does mean no individual edge label here should be quoted.
- **One sentence per edge, the first mention only.** A page mentioning B five
  times contributes one of them, chosen by position. A pass over every mention
  would give a different and probably better label distribution.
- **Direction is ignored.** `A kills B` and `B kills A` both yield `foe`.
- **The 654 pair-only sentences are not a random subset.** Short sentences
  naming two characters skew toward the lead and toward list-like lines, so the
  restriction trades the crowding confound for a length-and-section one. The
  kin result survives the restriction; we have not shown it survives *that*.
- **Week 4's partition is one Louvain run.** Week 4 measured run-to-run NMI at
  0.698, so another seed moves some boundaries and every crossing rate here
  moves with it. We did not propagate that uncertainty.
- **The `kin` cell is thin**: 41 pair-only edges carrying the surviving result.
  It is the smallest number the post leans on.
- **303 characters from one Wikipedia category.** Everything here is as much
  about Wikipedia's prose conventions as about Marvel.
