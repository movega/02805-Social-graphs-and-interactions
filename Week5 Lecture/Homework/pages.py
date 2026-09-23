"""Week 5 - the Marvel article text, loaded once and correctly.

The week-5 release is the full plain-text Wikipedia article for each of the
same 303 characters the network weeks used. This module is the loader; the
analysis script imports it so the joining logic lives in one place.

    from pages import load_pages, load_roster
    pages = load_pages()          # node_id -> article text
    roster = load_roster()        # node_id -> {name, url, description, ...}

Run it directly for a summary of the corpus:

    python pages.py
"""

import csv
import os
import re
import urllib.parse
import zipfile

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
ZIP = os.path.join(DATA, "marvel_pages.zip")
NODES = os.path.join(DATA, "week1_nodes.tsv")


def load_roster(path=NODES):
    """The 303 characters, keyed by node_id - the same key the text uses."""
    out, header = {}, None
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                continue
            row = dict(zip(header, parts))
            out[row["node_id"]] = row
    return out


def load_pages(path=ZIP, check_against_roster=True):
    """node_id -> article text, read straight out of the zip.

    The filenames are URL-encoded because a filesystem will not take every
    Wikipedia title. Exactly one character is affected in this release -
    Mark_Hazzard%3A_Merc - so a naive join looks like it works and silently
    drops one article. Decoding the stem is the whole trick.
    """
    pages = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            base = os.path.basename(name)
            if not base.endswith(".txt") or base == "README.txt":
                continue
            node_id = urllib.parse.unquote(base[:-4])
            pages[node_id] = z.read(name).decode("utf-8")

    if check_against_roster:
        roster = set(load_roster())
        missing = roster - set(pages)
        extra = set(pages) - roster
        if missing or extra:
            raise SystemExit(
                "page set does not match the roster: %d missing (%s), %d extra (%s)"
                % (len(missing), sorted(missing)[:3], len(extra), sorted(extra)[:3]))
    return pages


_WORD = re.compile(r"[A-Za-z][A-Za-z'-]+")


def tokenize(text, lowercase=True):
    """Words only: no digits, no punctuation, hyphens and apostrophes kept so
    Spider-Man and O'Grady survive as single tokens."""
    words = _WORD.findall(text)
    return [w.lower() for w in words] if lowercase else words


if __name__ == "__main__":
    import statistics

    roster = load_roster()
    pages = load_pages()
    lens = {k: len(v) for k, v in pages.items()}
    words = {k: len(tokenize(v)) for k, v in pages.items()}
    v = sorted(lens.values())

    print("articles          %d" % len(pages))
    print("roster            %d  (all matched: %s)" % (
        len(roster), set(roster) == set(pages)))
    print("characters        %.1fM total, median %d, %d to %d" % (
        sum(v) / 1e6, statistics.median(v), v[0], v[-1]))
    print("words             %.1fM total, median %d" % (
        sum(words.values()) / 1e6, statistics.median(words.values())))
    print()
    print("longest   %-34s %7d chars" % (max(lens, key=lens.get), max(v)))
    print("shortest  %-34s %7d chars" % (min(lens, key=lens.get), min(v)))
    print()
    print("the one that needs the unquote:")
    tricky = "Mark_Hazzard:_Merc"
    print("  %-34s %7d chars" % (tricky, lens[tricky]))
