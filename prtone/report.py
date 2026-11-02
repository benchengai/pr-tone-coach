"""Plain-text rendering of a check result for the terminal."""

from __future__ import annotations

import difflib
import textwrap

TARGET_LABEL = {"code": "the code", "person": "the person", "tool_process": "a tool or process",
                "none": "nothing (no criticism)"}
RISK_COLOR = {"low": "32", "medium": "33", "high": "31"}


def _c(text: str, code: str, color: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if color else text


def highlight(draft: str, phrases: list[dict], color: bool) -> str:
    """Mark verified phrases: colour in a terminal, [[brackets]] otherwise."""
    out, pos = [], 0
    for p in phrases:
        if p["start"] < pos:
            continue  # overlapping phrase: the earlier one is already marked
        out.append(draft[pos:p["start"]])
        quote = draft[p["start"]:p["end"]]
        out.append(_c(quote, "1;4;35", color) if color else f"[[{quote}]]")
        pos = p["end"]
    out.append(draft[pos:])
    return "".join(out)


def word_diff(before: str, after: str, color: bool) -> str:
    a, b = before.split(), after.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op == "equal":
            out.append(" ".join(a[i1:i2]))
            continue
        if i2 > i1:
            removed = " ".join(a[i1:i2])
            out.append(_c(removed, "9;31", color) if color else f"[-{removed}-]")
        if j2 > j1:
            added = " ".join(b[j1:j2])
            out.append(_c(added, "32", color) if color else f"{{+{added}+}}")
    return " ".join(out)


def render_text(result: dict, color: bool = False) -> str:
    risk = result["risk"]
    lines = [
        f"Risk:   {_c(risk.upper(), RISK_COLOR[risk], color)}  (reads as destructive criticism or pushback)",
        f"Target: {TARGET_LABEL[result['target']]}",
        "",
        "Draft:",
        textwrap.indent(highlight(result["draft"], result["phrases"], color), "  "),
    ]
    if result["phrases"]:
        lines += ["", "Phrases:"]
        lines += [f"  - \"{p['quote']}\"  ({p['cue'].replace('_', ' ')})" for p in result["phrases"]]
    if result["rewrite"]:
        lines += ["", "Suggested rewrite:", textwrap.indent(result["rewrite"], "  "),
                  "", "Changes:", textwrap.indent(word_diff(result["draft"], result["rewrite"], color), "  ")]
        kept = result["preservation"]
        if kept and kept["tokens"]:
            status = "all kept" if kept["all_kept"] else "MISSING " + ", ".join(t["value"] for t in kept["missing"])
            lines += ["", f"Technical tokens: {kept['kept']} of {kept['tokens']} kept ({status})"]
    if "rewrite_check" in result:
        lines.append(f"Rewrite re-checked: risk {result['rewrite_check']['risk']}")
    for w in result["warnings"]:
        lines.append(f"Note: {w}")
    llm = result.get("llm") or {}
    if llm.get("provider") == "rules":
        lines += ["", "Keyword baseline (no model call, no rewrite)."]
    elif llm:
        cost = f"${llm['cost_usd']:.4f}" if llm.get("cost_usd") is not None else "unknown cost"
        lines += ["", f"{llm['model']}: {llm['latency_s']} s, {cost}. Labels describe the text, not its writer."]
    return "\n".join(lines)
