# Week 5 — preparation

**Status: the data is in, the exercises are not.** Written 23 September 2026.

The course page for week 5 does not exist yet —
`sunelehmann.com/socialgraphs2026-web/weeks/week5.html` returns 404. Week 5 is
NLP I and lands Wednesday 30 September, after Test 1. Nothing here decides what
the post will argue, because the exercises are not out. This is only the
plumbing, so Wednesday starts at the analysis rather than at the download.

## What is in

`Data/marvel_pages.zip` (1.8 MB), the week-5 release: the full plain-text
Wikipedia article for each of the 303 characters from the network weeks. Same
roster, same `node_id` key, so it joins straight onto `week1_nodes.tsv` and onto
every network result we already have.

| | |
|---|---|
| articles | 303, matching the roster exactly |
| characters | 4.4M total, median 7,642, from 1,244 to 87,256 |
| words | 0.7M total, median 1,182 per article |
| longest | Scarlet Witch, 87,256 characters |
| shortest | Helix, 1,244 characters |

The text is rendered prose with templates and markup stripped, but it keeps
section headings and Wikipedia's phrasing.

## The filename trap, handled

Filenames in the zip are URL-encoded, because a filesystem will not take every
Wikipedia title. **Exactly one character is affected in this release** —
`Mark_Hazzard%3A_Merc.txt` for `Mark_Hazzard:_Merc` — which is precisely what
makes it dangerous: a naive join returns 302 of 303 articles and looks like it
worked.

`pages.py` handles it and refuses to return a page set that does not match the
roster, so the failure is loud rather than silent.

## Use it like this

```python
from pages import load_pages, load_roster, tokenize

pages = load_pages()      # node_id -> article text, validated against the roster
roster = load_roster()    # node_id -> name, url, description, wikidata_id
tokens = tokenize(pages["Spider-Man"])   # words only, hyphens and apostrophes kept
```

`python pages.py` prints the corpus summary above.

## Environment

Already installed: `nltk` 3.9.1, `scikit-learn` 1.6.1, `wordcloud` 1.9.4, plus
the numpy/pandas/matplotlib/networkx/scipy set the network weeks used.

Downloaded the NLTK corpora that NLP I will almost certainly want: `punkt`,
`punkt_tab`, `stopwords` (198 English), `vader_lexicon` (sentiment). Verified
all three import and run.

**Not** installed, if an exercise calls for them: `spacy`, `gensim`, `textblob`.

## What to do on Wednesday

1. Read the week-5 page in full, including the study guide at the bottom — that
   is where the course names the mistakes it wants the post to avoid.
2. Check whether a further release appears on the course data page.
3. Decide the null model **before** writing any prose. This is the one thing
   that does not carry over from the network weeks: `double_edge_swap` means
   nothing to a word count. Candidates worth thinking about are shuffling words
   between articles while keeping each article's length, sampling a
   frequency-matched vocabulary from the whole corpus, or computing the same
   measure on a category nobody claims is special. Whichever it is, generate
   many and report how many beat the real value — that habit is the reason the
   posts have worked.
4. One obvious hazard to control for early: article length varies by a factor of
   70. Almost any raw count will correlate with it, so most measures want
   normalising or length-matching before they mean anything.

## Not decided

The post's question, its metaphor, its figures, and whether it uses the
philosophers corpus as a second network the way week 4 did. All of that waits
for the exercises.
