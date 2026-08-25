#!/usr/bin/env python3
"""spell_correct.py — forgive typos by correcting against the archive's OWN words.

A search word that isn't found in the transcripts is checked against the
archive's real vocabulary (archive_vocab.json, ~42k words). If a close match
exists (edit distance 1, then 2), the real word is used instead. So "Isreal"
finds "Israel," "Jerusaelm" finds "Jerusalem" — corrected against the very
words the recordings actually say. Only activates for words NOT already in
the vocabulary, so it can never harm a correctly-spelled search.
"""

import json
import os

_VOCAB = None
_BYLEN = None


def _load():
    global _VOCAB, _BYLEN
    if _VOCAB is not None:
        return
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archive_vocab.json")
    _VOCAB = json.load(open(path))   # {word: count}
    _BYLEN = {}
    for w in _VOCAB:
        _BYLEN.setdefault(len(w), []).append(w)


def _osa_leq(a, b, maxd):
    """Optimal String Alignment distance <= maxd — like Levenshtein but an
    ADJACENT SWAP counts as ONE edit (so 'isreal'->'israel' is distance 1)."""
    la, lb = len(a), len(b)
    if abs(la - lb) > maxd:
        return False
    prev2 = None
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        best = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if (i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]):
                cur[j] = min(cur[j], prev2[j - 2] + 1)   # transposition
            best = min(best, cur[j])
        if best > maxd:
            return False
        prev2, prev = prev, cur
    return prev[lb] <= maxd


def correct_word(word):
    """Return the word if it's real; else the nearest archive word (ties
    broken toward the more common word), else the word unchanged."""
    _load()
    w = word.lower()
    if len(w) < 3 or w in _VOCAB:
        return word
    for maxd in (1, 2):
        candidates = []
        for L in range(len(w) - maxd, len(w) + maxd + 1):
            for cand in _BYLEN.get(L, ()):
                if cand[0] != w[0] and cand[-1] != w[-1]:
                    continue  # cheap prefilter: share first or last letter
                if _osa_leq(w, cand, maxd):
                    candidates.append(cand)
        if candidates:
            # pick the most COMMON word in the archive (best "did you mean")
            best = max(candidates, key=lambda c: _VOCAB.get(c, 0))
            return best if word.islower() or word.isupper() else best
    return word


def correct_query(text):
    """Correct each word in a query string; return (corrected_text, changes)."""
    import re
    changes = []
    out = []
    for tok in re.findall(r"[A-Za-z']+|[^A-Za-z']+", text):
        if tok.isalpha():
            c = correct_word(tok)
            if c.lower() != tok.lower():
                changes.append((tok, c))
            out.append(c)
        else:
            out.append(tok)
    return "".join(out), changes


if __name__ == "__main__":
    for test in ["isreal", "jerusaelm", "galilie", "abrahm", "the God of Isreal",
                 "Israel", "jesus", "remembrence"]:
        corrected, changes = correct_query(test)
        mark = f"   {changes}" if changes else "   (no change)"
        print(f"  {test!r:35} -> {corrected!r}{mark}")
