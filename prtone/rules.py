"""Keyword baseline: the same output shape as the LLM checker, from fixed patterns.

It exists to answer "does the LLM add anything over a word list?" and to give
the CLI an offline mode. It never rewrites. Patterns were written from the
cue definitions in check.py and the development set only.
"""

from __future__ import annotations

import re

from .evidence import verify_phrases

_W = r"(?<![\w-])"
_E = r"(?![\w-])"


def _rx(*words: str) -> re.Pattern:
    return re.compile(_W + "(?:" + "|".join(words) + ")" + _E, re.I)


PATTERNS = {
    "insult": _rx(r"idiot\w*", r"stupid\w*", r"moron\w*", r"dumb\w*", r"garbage", r"trash", r"crap\w*",
                  r"clown\w*", r"incompetent", r"amateur\w*", r"brain[- ]?dead", r"retard\w*", r"lazy",
                  r"pathetic", r"joke", r"embarrassing", r"disgrace\w*", r"horrible", r"terrible", r"awful",
                  r"atrocious", r"insane", r"nonsense", r"rubbish", r"monkey\w*"),
    "profanity": _rx(r"f+u+c+k\w*", r"f\*+k\w*", r"wtf", r"shit\w*", r"s\*+t", r"damn\w*", r"hell",
                     r"bullshit", r"ass(?:hole)?s?", r"bloody", r"piss\w*", r"bastard\w*"),
    "person_directed": re.compile(
        _W + r"(?:you|you're|your)\s+(?:clearly|obviously|apparently|really|just|never|always|don't|didn't|"
        r"can't|couldn't|have no|has no|no idea|lack|keep|forgot|forget|again|seem to|must not)" + _E
        + r"|did you (?:even|actually|bother|not)" + _E
        + r"|(?:have|has) you (?:even|ever)" + _E
        + r"|do you (?:even|know|understand)" + _E, re.I),
    "mocking_or_sarcasm": re.compile(
        r"(?:^|[.!?]\s+)(?:great|wow|nice|brilliant|genius|congrats|lovely|wonderful)[,!.]+\s"
        r"|\bwhat could (?:possibly )?go wrong\b|\bsaid no one\b|/s\b|🙄|\blol\b", re.I),
    "dismissive": re.compile(r"(?:^|[.!?]\s+)no\.(?:\s|$)|" + _W + r"(?:pointless|useless|worthless|"
                             r"waste of time|not worth|makes no sense|doesn't make any sense|"
                             r"why would anyone|throw (?:it|this) away|start over)" + _E, re.I),
    "vague_negative": re.compile(r"^\s*(?:this|that|it) (?:is|looks) (?:wrong|bad|broken|ugly|messy|weird)[.!]?"
                                 r"|" + _W + r"(?:bad code|ugly|messy|hacky|sloppy|a mess|wrong)" + _E, re.I),
    "absolute_language": _rx(r"always", r"never", r"every (?:single )?time", r"nobody", r"no one",
                             r"everyone knows", r"all the time"),
    "condescending": _rx(r"obviously", r"clearly", r"simply", r"surely", r"basic", r"trivial",
                         r"any (?:junior|beginner|first[- ]year|intern)\w*", r"even a", r"learn to",
                         r"read the (?:docs|manual)", r"rtfm", r"come on"),
    "impatience": re.compile(_W + r"(?:(?:for )?the (?:\w+ )?(?:third|fourth|fifth|nth|\d+(?:st|nd|rd|th)) time"
                             r"|how many times|once again|yet again|again\?|as i (?:already )?said"
                             r"|i already (?:said|told|explained)|still not fixed)" + _E, re.I),
    "blocking_without_reason": re.compile(r"(?:^|\s)(?:-1|-2)(?:\.|\s|$)|" + _W +
                                          r"(?:not merging|won't merge|will not merge|not approving|rejected|veto)" + _E,
                                          re.I),
    "authority_appeal": re.compile(_W + r"(?:because i said so|i(?:'ve| have) been doing this for|"
                                   r"trust me|i'm the (?:lead|owner|maintainer)|i know better|senior)" + _E, re.I),
    "threat": re.compile(_W + r"(?:or else|i will revoke|i'll revoke|revoke your|get you (?:fired|removed)|"
                         r"report you|last warning|you'll regret|ban you)" + _E, re.I),
}
HIGH_CUES = {"insult", "threat"}
TOOL_RE = _rx(r"ci", r"jenkins", r"travis", r"zuul", r"gerrit", r"github actions?", r"pipelines?", r"builds?",
              r"linter", r"lint", r"compiler", r"ide", r"library", r"libraries", r"framework", r"orm", r"sdk",
              r"api docs", r"upstream", r"vendor", r"bot", r"process", r"policy", r"tooling", r"infra",
              r"dependabot", r"npm", r"pip", r"maven", r"gradle", r"webpack", r"docker", r"kubernetes", r"k8s",
              r"the (?:review|release) process")
POSITIVE_RE = _rx(r"lgtm", r"thanks?", r"thank you", r"nice", r"great", r"good catch", r"looks good", r"\+1",
                  r"approved?", r"well done", r"neat", r"love (?:this|it)")
NEGATIVE_RE = re.compile(r"\b(?:not|no|don't|doesn't|isn't|wrong|bug|broken|fail\w*|missing|should|must|"
                         r"needs?|instead|why|remove|rename|fix|avoid|incorrect|leak\w*|slow|unclear|"
                         r"confusing|duplicat\w*|unnecessary|redundant|nit)\b", re.I)


def find_cues(draft: str) -> list[dict]:
    phrases = []
    for cue, regex in PATTERNS.items():
        for m in regex.finditer(draft):
            quote = m.group(0).strip(" .,!?")
            if quote:
                phrases.append({"quote": quote, "cue": cue})
    return phrases


def rule_check(draft: str) -> dict:
    phrases, rejected = verify_phrases(find_cues(draft), draft)
    cues = {p["cue"] for p in phrases}
    # Profanity counts as an attack when it sits in a sentence that addresses the reader.
    addressed = re.search(r"\byou(?:r|'re)?\b", draft, re.I) is not None
    if "person_directed" in cues or (addressed and cues & {"insult", "profanity", "condescending"}):
        target = "person"
    elif TOOL_RE.search(draft) and not re.search(r"\b(?:this|your) (?:change|patch|code|function|method)\b",
                                                 draft, re.I):
        target = "tool_process"
    elif cues or NEGATIVE_RE.search(draft):
        target = "code"
    elif POSITIVE_RE.search(draft) or draft.strip().endswith("?"):
        target = "none"
    else:
        target = "code"
    if cues & HIGH_CUES or (target == "person" and cues & {"profanity", "condescending", "person_directed"}
                            and len(cues) >= 2):
        risk = "high"
    elif cues:
        risk = "medium"
    else:
        risk = "low"
    if target == "tool_process" and risk == "high" and "threat" not in cues:
        risk = "medium"  # contempt for a tool is not an attack on the recipient
    return {
        "draft": draft,
        "target": target,
        "risk": risk,
        "phrases": phrases,
        "rejected_phrases": rejected,
        "rewrite": None,
        "preservation": None,
        "warnings": [],
        "llm": {"provider": "rules", "model": "keyword-baseline", "input_tokens": 0, "cached_input_tokens": 0,
                "output_tokens": 0, "reasoning_tokens": 0, "latency_s": 0.0, "cost_usd": 0.0},
    }
