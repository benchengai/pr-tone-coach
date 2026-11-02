"""Score check results against gold labels.

Gold items come in two shapes:
- synthetic items carry `target`, `risk` and `phrases` (the words that drive the risk);
- external items (a human-labelled toxicity sample) carry only `toxic` (0/1), and
  optionally `spans` (character offsets of toxic phrases).
"""

from __future__ import annotations

from .check import RISKS, TARGETS
from .evidence import char_set, locate

RISK_LEVEL = {r: i for i, r in enumerate(RISKS)}


def f1_scores(gold: list[str], pred: list[str], labels: tuple[str, ...]) -> dict:
    """Per-class precision/recall/F1 and macro-F1 over the classes present in gold or pred."""
    per = {}
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, pred))
        fp = sum(g != label and p == label for g, p in zip(gold, pred))
        fn = sum(g == label and p != label for g, p in zip(gold, pred))
        if tp + fp + fn == 0:
            continue
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    macro = sum(v["f1"] for v in per.values()) / len(per) if per else 0.0
    accuracy = sum(g == p for g, p in zip(gold, pred)) / len(gold) if gold else 0.0
    return {"macro_f1": macro, "accuracy": accuracy, "per_class": per}


def confusion(gold: list[str], pred: list[str], labels: tuple[str, ...]) -> dict:
    return {g: {p: sum(1 for a, b in zip(gold, pred) if a == g and b == p) for p in labels} for g in labels}


def binary(gold: list[bool], pred: list[bool]) -> dict:
    tp = sum(g and p for g, p in zip(gold, pred))
    fp = sum(p and not g for g, p in zip(gold, pred))
    fn = sum(g and not p for g, p in zip(gold, pred))
    tn = sum(not g and not p for g, p in zip(gold, pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def gold_spans(item: dict) -> list[tuple[int, int]]:
    if "spans" in item:
        return [tuple(s) for s in item["spans"]]
    spans = []
    for phrase in item.get("phrases", []):
        if (span := locate(phrase, item["text"])) is not None:
            spans.append(span)
    return spans


def phrase_overlap(items: list[dict], results: list[dict]) -> dict:
    """Character-level overlap between verified phrases and gold phrases, pooled over items
    that have gold phrases (non-space characters only)."""
    tp = fp = fn = 0
    for item, r in zip(items, results):
        gold = gold_spans(item)
        if not gold:
            continue
        g = char_set(gold, item["text"])
        p = char_set([(x["start"], x["end"]) for x in r["phrases"]], item["text"])
        tp += len(g & p)
        fp += len(p - g)
        fn += len(g - p)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def phrase_hit_rate(items: list[dict], results: list[dict]) -> float | None:
    """Share of gold phrases that at least one verified phrase overlaps."""
    hits = total = 0
    for item, r in zip(items, results):
        pred = [(x["start"], x["end"]) for x in r["phrases"]]
        for s, e in gold_spans(item):
            total += 1
            hits += any(ps < e and s < pe for ps, pe in pred)
    return hits / total if total else None


def score_labels(items: list[dict], results: list[dict]) -> dict:
    """Synthetic gold: target and risk agreement, phrase validity and overlap."""
    gt, pt = [i["target"] for i in items], [r["target"] for r in results]
    gr, pr = [i["risk"] for i in items], [r["risk"] for r in results]
    returned = sum(len(r["phrases"]) + len(r["rejected_phrases"]) for r in results)
    verified = sum(len(r["phrases"]) for r in results)
    flagged_gold = [g != "low" for g in gr]
    flagged_pred = [p != "low" for p in pr]
    return {
        "n": len(items),
        "target": f1_scores(gt, pt, TARGETS),
        "risk": f1_scores(gr, pr, RISKS),
        "target_confusion": confusion(gt, pt, TARGETS),
        "risk_confusion": confusion(gr, pr, RISKS),
        "risk_within_one": sum(abs(RISK_LEVEL[g] - RISK_LEVEL[p]) <= 1 for g, p in zip(gr, pr)) / len(items),
        "flag": binary(flagged_gold, flagged_pred),
        "high_recall": binary([g == "high" for g in gr], [p == "high" for p in pr])["recall"],
        "phrases_returned": returned,
        "phrase_validity": verified / returned if returned else None,
        "phrase_overlap": phrase_overlap(items, results),
        "phrase_hit_rate": phrase_hit_rate(items, results),
        "unsupported_risk": sum(r["risk"] != "low" and not r["phrases"] for r in results),
    }


def score_toxicity(items: list[dict], results: list[dict]) -> dict:
    """External human labels: does risk agree with the binary toxic label?"""
    toxic = [bool(i["toxic"]) for i in items]
    returned = sum(len(r["phrases"]) + len(r["rejected_phrases"]) for r in results)
    verified = sum(len(r["phrases"]) for r in results)
    out = {
        "n": len(items),
        "toxic": sum(toxic),
        "high_vs_toxic": binary(toxic, [r["risk"] == "high" for r in results]),
        "flag_vs_toxic": binary(toxic, [r["risk"] != "low" for r in results]),
        "person_share_toxic": (sum(r["target"] == "person" for r, t in zip(results, toxic) if t) / sum(toxic))
        if sum(toxic) else None,
        "phrase_validity": verified / returned if returned else None,
    }
    span_items = [(i, r) for i, r in zip(items, results) if i.get("spans")]
    if span_items:
        out["span_overlap"] = phrase_overlap([i for i, _ in span_items], [r for _, r in span_items])
        out["span_hit_rate"] = phrase_hit_rate([i for i, _ in span_items], [r for _, r in span_items])
    return out


def score_rewrites(results: list[dict], rechecks: list[dict | None], judgements: list[dict | None]) -> dict:
    """Rewrite quality for the results that offered one."""
    rewritten = [i for i, r in enumerate(results) if r["rewrite"]]
    flagged = [i for i, r in enumerate(results) if r["risk"] != "low"]
    kept = [results[i]["preservation"] for i in rewritten]
    with_tokens = [k for k in kept if k["tokens"]]
    after = [rechecks[i]["risk"] for i in rewritten if rechecks[i] is not None]
    judged = [judgements[i] for i in rewritten if judgements[i] is not None]
    return {
        "flagged": len(flagged),
        "rewrites": len(rewritten),
        "rewrite_rate_when_flagged": sum(bool(results[i]["rewrite"]) for i in flagged) / len(flagged)
        if flagged else None,
        "tokens_all_kept": sum(k["all_kept"] for k in with_tokens) / len(with_tokens) if with_tokens else None,
        "token_kept_rate": sum(k["kept"] for k in with_tokens) / sum(k["tokens"] for k in with_tokens)
        if with_tokens else None,
        "rechecked": len(after),
        "after_low": sum(a == "low" for a in after) / len(after) if after else None,
        "after_high": sum(a == "high" for a in after) / len(after) if after else None,
        "judged": len(judged),
        **{f"judge_{c}": (sum(j[c] for j in judged) / len(judged) if judged else None)
           for c in ("technical_points_kept", "no_added_claims", "request_strength_kept", "respectful", "pass")},
    }
