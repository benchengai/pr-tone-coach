"""Locate each quoted phrase in the draft and return its character offsets.

The model quotes the phrases that drive the risk; a quote counts only if it is
in the draft. Drafts are typed text, so matching is exact up to case,
whitespace and typographic quotes, and the offsets point into the original
draft so the UI can highlight them.
"""

from __future__ import annotations

_FOLD = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def _folded(text: str) -> tuple[str, list[int]]:
    """Lower-cased text with whitespace runs collapsed, and the original index of each char."""
    out, index, prev_space = [], [], False
    for i, ch in enumerate(text.translate(_FOLD)):
        if ch.isspace():
            if prev_space:
                continue
            ch, prev_space = " ", True
        else:
            prev_space = False
        out.append(ch.lower())
        index.append(i)
    return "".join(out), index


def locate(quote: str, draft: str, start: int = 0) -> tuple[int, int] | None:
    """(start, end) of `quote` in `draft`, or None. Prefers an exact match."""
    quote = quote.strip()
    if not quote:
        return None
    exact = draft.find(quote, start)
    if exact >= 0:
        return exact, exact + len(quote)
    fd, index = _folded(draft)
    fq, _ = _folded(quote)
    fq = fq.strip(" .,;:!?\"'")
    if not fq:
        return None
    from_folded = next((k for k, i in enumerate(index) if i >= start), len(fd))
    k = fd.find(fq, from_folded)
    if k < 0:
        return None
    return index[k], index[k + len(fq) - 1] + 1


def verify_phrases(phrases: list[dict], draft: str) -> tuple[list[dict], list[dict]]:
    """Split model phrases into (verified, rejected). Verified ones get `start`/`end` and the
    exact draft text. A quote that occurs several times in the draft is matched to its next
    unused occurrence; quoting the same occurrence twice keeps one copy."""
    verified, rejected, used = [], [], set()
    for p in phrases:
        span, start = None, 0
        while (found := locate(p["quote"], draft, start)) is not None:
            if found not in used:
                span = found
                break
            start = found[0] + 1
        if span is None:
            if locate(p["quote"], draft) is None:
                rejected.append({**p, "reason": "not in draft"})
            continue
        used.add(span)
        verified.append({**p, "quote": draft[span[0]:span[1]], "start": span[0], "end": span[1]})
    verified.sort(key=lambda p: p["start"])
    return verified, rejected


def char_set(spans: list[tuple[int, int]], text: str) -> set[int]:
    """Indices of non-space characters covered by the spans (for overlap scoring)."""
    return {i for s, e in spans for i in range(s, e) if not text[i].isspace()}

