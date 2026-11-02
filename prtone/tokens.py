"""Deterministic check that a rewrite keeps the technical content of the original.

`technical_tokens` pulls out what a reviewer cannot paraphrase without changing
the meaning: code spans, URLs, file paths, identifiers, issue references and
numbers. `preservation` checks that each one survives in the rewrite exactly
(code spans may lose their backticks; everything else must match as written).

This is a necessary check, not a sufficient one: a rewrite can keep every
token and still drop a request, which is what the LLM judge looks at.
"""

from __future__ import annotations

import re

FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
CODE_RE = re.compile(r"`([^`\n]+)`")
URL_RE = re.compile(r"https?://[^\s)>\]]+")
# a/b, ./a, ../a, a/b.c, src/x.py; at least one slash and a word on each side.
PATH_RE = re.compile(r"(?<![\w/.:-])(?:\.{1,2}/|~/|/)?(?:[\w.@-]+/)+[\w.@-]*\w")
FILE_RE = re.compile(r"(?<![\w/.-])[\w-]+\.(?:[a-z]{1,5}|[A-Z]{1,4})(?![\w(])")
ISSUE_RE = re.compile(r"(?<![\w&])#\d+\b")
IDENT_PATTERNS = [
    re.compile(r"\b[A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)+(?:\(\))?"),  # dotted.name, obj.method()
    re.compile(r"\b[A-Za-z_]\w*::\w+(?:::\w+)*"),                  # Rust/C++ paths
    re.compile(r"\b[A-Za-z_]\w*\(\)"),                               # call()
    re.compile(r"\b_*[a-z0-9]+(?:_[a-z0-9]+)+_*\b"),                 # snake_case
    re.compile(r"\b[A-Z0-9]+(?:_[A-Z0-9]+)+\b"),                     # SCREAMING_CASE
    re.compile(r"\b[a-z]+[a-z0-9]*(?:[A-Z][a-z0-9]*)+\b"),           # camelCase
    re.compile(r"\b(?:[A-Z][a-z0-9]+){2,}\b"),                       # PascalCase, two humps or more
    re.compile(r"\b[A-Z][a-z0-9]*[A-Z]+[a-z0-9]*\w*\b"),             # HttpURL, IOError, XMLParser
]
NUMBER_RE = re.compile(r"(?<![\w.])v?\d+(?:[.,:]\d+)*(?![\w.]*\w)|(?<![\w.])\d+(?:\.\d+)*(?=[a-zA-Z%]{1,3}\b)")

# Words that look like identifiers to the patterns above but are prose.
PROSE = {"e.g", "i.e", "etc", "vs", "a.k.a", "PRs", "IDs", "APIs", "URLs", "LGTM", "TODOs", "OK", "OKs",
         "CI", "PR", "ID", "API", "URL", "TODO", "FYI", "IMO", "IMHO", "TL;DR", "nit", "iOS", "macOS",
         "JavaScript", "TypeScript", "GitHub", "GitLab", "PostgreSQL", "MySQL", "YouTube", "OpenStack",
         "WebSocket", "WebSockets", "LinkedIn", "PyPI", "NumPy", "SciPy", "FastAPI", "GraphQL", "DevOps"}

KINDS = ("code", "url", "path", "issue", "identifier", "number")


def _spans_outside(text: str, taken: list[tuple[int, int]]):
    """Yield (start, end) ranges of text not covered by `taken`."""
    pos = 0
    for s, e in sorted(taken):
        if s > pos:
            yield pos, s
        pos = max(pos, e)
    if pos < len(text):
        yield pos, len(text)


def technical_tokens(text: str) -> list[dict]:
    """Tokens in order of appearance: {"kind", "value"}; duplicates removed."""
    found: list[tuple[int, str, str]] = []
    taken: list[tuple[int, int]] = []

    def claim(kind: str, regex: re.Pattern, group: int = 0, scope=None):
        ranges = [(0, len(text))] if scope is None else list(scope)
        for lo, hi in ranges:
            for m in regex.finditer(text, lo, hi):
                s, e = m.span()
                if any(s < te and ts < e for ts, te in taken):
                    continue
                value = m.group(group).strip()
                if value:
                    found.append((s, kind, value))
                    taken.append((s, e))

    claim("code", FENCE_RE, 1)
    claim("code", CODE_RE, 1)
    claim("url", URL_RE)
    rest = lambda: list(_spans_outside(text, taken))  # noqa: E731
    claim("path", PATH_RE, scope=rest())
    claim("path", FILE_RE, scope=rest())
    claim("issue", ISSUE_RE, scope=rest())
    for regex in IDENT_PATTERNS:
        claim("identifier", regex, scope=rest())
    claim("number", NUMBER_RE, scope=rest())

    out, seen = [], set()
    for _, kind, value in sorted(found):
        value = value.rstrip(".,;:") if kind in ("url", "path", "identifier") else value
        if value in PROSE or value.lower() in {"e.g", "i.e"} or (kind, value) in seen:
            continue
        if kind == "identifier" and value.isalpha() and value.isupper():
            continue  # TTL, JSON, WHY: acronyms and shouting, not identifiers
        if kind == "path" and _looks_like_prose_slash(value):
            continue
        seen.add((kind, value))
        out.append({"kind": kind, "value": value})
    return out


PROSE_SLASH = {"and/or", "either/or", "read/write", "yes/no", "on/off", "true/false", "input/output",
               "client/server", "he/she", "his/her", "w/o", "n/a", "i/o", "pros/cons", "before/after",
               "front/back", "start/stop", "open/close", "get/set", "add/remove", "this/that"}


def _looks_like_prose_slash(value: str) -> bool:
    return value.lower() in PROSE_SLASH


def _present(token: dict, rewrite: str) -> bool:
    value = token["value"]
    if token["kind"] == "number":
        return re.search(rf"(?<![\w.]){re.escape(value)}(?![\d])", rewrite) is not None
    if token["kind"] == "code" and "\n" in value:
        squash = lambda s: " ".join(s.split())  # noqa: E731
        return squash(value) in squash(rewrite)
    return value in rewrite


def preservation(original: str, rewrite: str, flagged: list[tuple[int, int]] = ()) -> dict:
    """Which technical tokens of `original` are missing from `rewrite`.

    Numbers that only occur inside flagged phrases ("for the third time", "I've done this for
    8 years") belong to the wording being replaced, so they are listed as exempt rather than
    required. Code spans, identifiers, paths and URLs are always required."""
    tokens = technical_tokens(original)
    inside = lambda s, e: any(fs <= s and e <= fe for fs, fe in flagged)  # noqa: E731
    required, exempt = [], []
    for t in tokens:
        if t["kind"] == "number":
            spans = [m.span() for m in re.finditer(rf"(?<![\w.]){re.escape(t['value'])}(?![\d])", original)]
            if spans and all(inside(s, e) for s, e in spans):
                exempt.append(t)
                continue
        required.append(t)
    missing = [t for t in required if not _present(t, rewrite)]
    return {
        "tokens": len(required),
        "kept": len(required) - len(missing),
        "missing": missing,
        "exempt": exempt,
        "all_kept": not missing,
    }
