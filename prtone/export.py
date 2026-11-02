"""Export stored bench outputs for the static web demo.

The demo shows only what the pipeline produced: each sample is a cached bench
record (check, re-check of the rewrite, judge verdict) for a synthetic test
comment, re-verified with the current deterministic checks. Nothing is written
by hand, and every output keeps the request id of the API call behind it.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from .bench import load_gold, slug
from .check import reassemble
from .tokens import _present, technical_tokens

WORD_RE = re.compile(r"\S+\s*")


def side_by_side(before: str, after: str) -> dict:
    """Word-level diff as two lists of segments: removed words on the left, added on the right."""
    a, b = WORD_RE.findall(before), WORD_RE.findall(after)
    left, right = [], []
    matcher = difflib.SequenceMatcher(None, [w.strip() for w in a], [w.strip() for w in b], autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            left.append({"text": "".join(a[i1:i2]), "changed": False})
            right.append({"text": "".join(b[j1:j2]), "changed": False})
            continue
        if i2 > i1:
            left.append({"text": "".join(a[i1:i2]), "changed": True})
        if j2 > j1:
            right.append({"text": "".join(b[j1:j2]), "changed": True})
    return {"left": left, "right": right}


def _llm(meta: dict) -> dict:
    keys = ("model", "request_id", "latency_s", "cost_usd", "input_tokens", "cached_input_tokens", "output_tokens")
    return {k: meta.get(k) for k in keys}


def sample_output(record: dict) -> dict | None:
    if not record.get("result"):
        return None
    r = reassemble(record["result"])
    out = {
        "target": r["target"],
        "risk": r["risk"],
        "phrases": [{k: p[k] for k in ("quote", "cue", "start", "end")} for p in r["phrases"]],
        "rejected_phrases": [p["quote"] for p in r["rejected_phrases"]],
        "rewrite": r["rewrite"],
        "warnings": r["warnings"],
        "llm": _llm(r["llm"]),
    }
    if r["rewrite"]:
        kept = r["preservation"]
        exempt = {(t["kind"], t["value"]) for t in kept["exempt"]}
        out["tokens"] = [{**t, "kept": _present(t, r["rewrite"])} for t in technical_tokens(r["draft"])
                         if (t["kind"], t["value"]) not in exempt]
        out["diff"] = side_by_side(r["draft"], r["rewrite"])
    if record.get("recheck"):
        rc = record["recheck"]
        out["recheck"] = {"risk": rc["risk"], "target": rc["target"],
                          "phrases": [{"quote": p["quote"], "cue": p["cue"]} for p in rc["phrases"]],
                          "llm": _llm(rc["llm"])}
    if record.get("judge"):
        j = record["judge"]
        out["judge"] = {k: j[k] for k in ("missing_points", "added_claims", "softened_requests", "disrespect_left",
                                         "technical_points_kept", "no_added_claims", "request_strength_kept",
                                         "respectful", "pass")}
        out["judge"]["llm"] = _llm(j["llm"])
    return out


def export_demo(gold_path: Path, bench_dir: Path, specs: list[str], run: int, out_path: Path,
                summary: dict | None = None) -> dict:
    items = load_gold(gold_path)
    samples = []
    for item in items:
        outputs = {}
        for spec in specs:
            path = bench_dir / slug(spec) / f"run{run}" / f"{item['id']}.json"
            if path.exists() and (o := sample_output(json.loads(path.read_text(encoding="utf-8")))):
                outputs[spec.split(":")[-1]] = o
        if outputs:
            samples.append({"id": item["id"], "synthetic": item["source"] == "synthetic", "text": item["text"],
                            "gold": {k: item[k] for k in ("target", "risk", "phrases")},
                            "note": item.get("note"), "outputs": outputs})
    data = {
        "source": f"{gold_path.name}, bench run {run}",
        "models": [s.split(":")[-1] for s in specs],
        "samples": samples,
        "summary": summary,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data
