"""Run checkers on a gold set several times and report quality, cost and latency.

Each (model, run, item) is cached as one JSON file, so an interrupted bench
resumes where it stopped and a re-score costs nothing. A run that returns
invalid output is recorded and counted as a failure, not retried; a transient
API error is not cached, so the next invocation tries again.

Per item and run: one check call; if the checker offered a rewrite, one more
check call on the rewrite (same model, "risk after rewrite"), and a judge call
with a fixed model and rubric on the rewrite for the first `judge_runs` runs.
"""

from __future__ import annotations

import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import openai
from pydantic import ValidationError

from .check import check, reassemble
from .evaluate import score_labels, score_rewrites, score_toxicity
from .judge import RUBRIC_VERSION, judge
from .llm import LLMError, parse_model_spec


def load_gold(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def slug(spec: str) -> str:
    return spec.replace(":", "_").replace("/", "_")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _provider(spec: str) -> tuple[str, str | None]:
    return ("rules", None) if spec == "rules" else parse_model_spec(spec)


def run_item(item: dict, spec: str, path: Path, recheck: bool, judge_spec: str | None) -> dict:
    record = _read(path) if path.exists() else {"id": item["id"], "spec": spec}
    provider, model = _provider(spec)
    changed = False
    try:
        if "result" not in record and "error" not in record:
            changed = True
            record["result"] = check(item["text"], provider, model)
        result = record.get("result")
        if result and result["rewrite"] and recheck and "recheck" not in record:
            changed = True
            again = check(result["rewrite"], provider, model)
            record["recheck"] = {k: again[k] for k in ("target", "risk", "phrases", "llm")}
        stale = (record.get("judge", {}).get("spec"), record.get("judge", {}).get("rubric")) != (judge_spec, RUBRIC_VERSION)
        if result and result["rewrite"] and judge_spec and stale:
            changed = True
            verdict, meta = judge(item["text"], result["rewrite"], *parse_model_spec(judge_spec))
            record["judge"] = {"spec": judge_spec, **verdict, "llm": meta}
    except (LLMError, ValidationError, json.JSONDecodeError) as e:
        changed = True
        record["error"] = str(e)[:500]
    except openai.APIError as e:  # transient: keep what finished, retry the rest next time
        if changed:
            _write(path, {k: v for k, v in record.items()})
        return {**record, "transient_error": str(e)[:200]}
    if changed:
        _write(path, record)
    return record


def _calls(records: list[dict], key: str) -> list[dict]:
    if key == "result":
        return [r["result"]["llm"] for r in records if r.get("result")]
    return [r[key]["llm"] for r in records if r.get(key)]


def _cost(calls: list[dict]) -> float | None:
    return None if any(c["cost_usd"] is None for c in calls) else sum(c["cost_usd"] for c in calls)


def score_run(items: list[dict], records: list[dict]) -> dict:
    ok = [(i, r) for i, r in zip(items, records) if r.get("result")]
    oi, results = [i for i, _ in ok], [reassemble(r["result"]) for _, r in ok]
    checks = _calls(records, "result")
    latencies = sorted(c["latency_s"] for c in checks)
    row = {
        "items": len(items),
        "failed": len(items) - len(ok),
        "errors": [r["error"] for r in records if r.get("error")][:5],
        "cost_check_usd": _cost(checks),
        "cost_recheck_usd": _cost(_calls(records, "recheck")),
        "cost_judge_usd": _cost(_calls(records, "judge")),
        "cost_per_comment_usd": _cost(checks) / len(checks) if checks and _cost(checks) is not None else None,
        "latency_mean_s": statistics.fmean(latencies) if latencies else None,
        "latency_p90_s": latencies[int(0.9 * (len(latencies) - 1))] if latencies else None,
        "output_tokens_mean": statistics.fmean(c["output_tokens"] for c in checks) if checks else None,
    }
    if not ok:
        return row
    if "toxic" in oi[0]:
        row["toxicity"] = score_toxicity(oi, results)
    else:
        row["labels"] = score_labels(oi, results)
    row["rewrites"] = score_rewrites(results, [r.get("recheck") for _, r in ok], [r.get("judge") for _, r in ok])
    return row


def bench(gold_path: Path, specs: list[str], runs: int, out_root: Path, judge_spec: str | None = None,
          workers: int = 6, recheck: bool = True, judge_runs: int = 1) -> dict:
    items = load_gold(gold_path)
    judge_spec = None if judge_spec in (None, "none") else judge_spec
    jobs = []
    for spec in specs:
        for k in range(1, (1 if spec == "rules" else runs) + 1):
            for item in items:
                jobs.append((spec, k, item))

    def job(args):
        spec, k, item = args
        path = out_root / slug(spec) / f"run{k}" / f"{item['id']}.json"
        return (spec, k, item["id"]), run_item(item, spec, path, recheck, judge_spec if k <= judge_runs else None)

    with ThreadPoolExecutor(workers) as pool:
        records = dict(pool.map(job, jobs))

    results = {"gold": str(gold_path), "items": len(items), "runs_per_model": runs, "judge": judge_spec,
               "prompt_sha256": prompt_fingerprint(),
               "judge_runs": judge_runs, "recheck": recheck, "models": {}}
    for spec in specs:
        n = 1 if spec == "rules" else runs
        rows = [score_run(items, [records[(spec, k, i["id"])] for i in items]) for k in range(1, n + 1)]
        results["models"][spec] = {"runs": rows, "summary": aggregate(rows)}
        failed = sum(r["failed"] for r in rows)
        print(f"  {spec}: {n} run(s), {failed} failed item(s)", flush=True)
    _write(out_root / "results.json", results)
    return results


def prompt_fingerprint() -> dict:
    """Hashes of the prompts and schemas, so a results file names the exact prompt version."""
    import hashlib

    from . import check as check_mod, judge as judge_mod

    digest = lambda *parts: hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12]  # noqa: E731
    return {"check": digest(check_mod.SYSTEM, check_mod.SCHEMA), "judge": digest(judge_mod.SYSTEM, judge_mod.SCHEMA)}


def _flatten(row: dict, prefix: str = "") -> dict:
    flat = {}
    for key, value in row.items():
        if isinstance(value, dict) and key not in ("per_class", "target_confusion", "risk_confusion"):
            flat.update(_flatten(value, f"{prefix}{key}."))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            flat[f"{prefix}{key}"] = value
    return flat


def aggregate(rows: list[dict]) -> dict:
    flats = [_flatten(r) for r in rows]
    keys = sorted({k for f in flats for k in f})
    summary = {}
    for key in keys:
        values = [f[key] for f in flats if f.get(key) is not None]
        if values:
            summary[key] = {"mean": statistics.fmean(values), "min": min(values), "max": max(values)}
    return summary


def cell(summary: dict, key: str, fmt: str = "{:.2f}") -> str:
    if key not in summary:
        return "–"
    v = summary[key]
    if fmt.format(v["min"]) == fmt.format(v["max"]):
        return fmt.format(v["mean"])
    return f"{fmt.format(v['mean'])} ({fmt.format(v['min'])}–{fmt.format(v['max'])})"


def render_markdown(results: dict) -> str:
    models = results["models"]
    first = next(iter(models.values()))["runs"][0]
    toxicity = "toxicity" in first
    lines = [
        f"### `{Path(results['gold']).name}`: {results['items']} comments, {results['runs_per_model']} runs per model",
        "",
        "Mean across runs, range in brackets. The keyword baseline is deterministic and runs once.",
        "",
    ]
    if toxicity:
        lines += [
            "| Model | High = toxic: P | R | F1 | Flagged (medium+) = toxic: P | R | F1 | Toxic items aimed at person "
            "| Quotes verified | Span hit rate | Cost per comment (USD) | Latency mean / p90 (s) | Failed |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for spec, m in models.items():
            s = m["summary"]
            lines.append(
                f"| `{spec}` | {cell(s, 'toxicity.high_vs_toxic.precision')} | {cell(s, 'toxicity.high_vs_toxic.recall')} "
                f"| {cell(s, 'toxicity.high_vs_toxic.f1')} | {cell(s, 'toxicity.flag_vs_toxic.precision')} "
                f"| {cell(s, 'toxicity.flag_vs_toxic.recall')} | {cell(s, 'toxicity.flag_vs_toxic.f1')} "
                f"| {cell(s, 'toxicity.person_share_toxic')} | {cell(s, 'toxicity.phrase_validity')} "
                f"| {cell(s, 'toxicity.span_hit_rate')} | {cell(s, 'cost_per_comment_usd', '{:.5f}')} "
                f"| {cell(s, 'latency_mean_s', '{:.1f}')} / {cell(s, 'latency_p90_s', '{:.1f}')} "
                f"| {sum(r['failed'] for r in m['runs'])} |")
        return "\n".join(lines) + "\n"
    lines += [
        "| Model | Target macro-F1 | Risk macro-F1 | Risk exact | Flag F1 (medium+) | High recall | Quotes verified "
        "| Phrase overlap F1 | Gold phrases hit | Cost per comment (USD) | Latency mean / p90 (s) | Failed |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for spec, m in models.items():
        s = m["summary"]
        lines.append(
            f"| `{spec}` | {cell(s, 'labels.target.macro_f1')} | {cell(s, 'labels.risk.macro_f1')} "
            f"| {cell(s, 'labels.risk.accuracy')} | {cell(s, 'labels.flag.f1')} | {cell(s, 'labels.high_recall')} "
            f"| {cell(s, 'labels.phrase_validity')} | {cell(s, 'labels.phrase_overlap.f1')} "
            f"| {cell(s, 'labels.phrase_hit_rate')} | {cell(s, 'cost_per_comment_usd', '{:.5f}')} "
            f"| {cell(s, 'latency_mean_s', '{:.1f}')} / {cell(s, 'latency_p90_s', '{:.1f}')} "
            f"| {sum(r['failed'] for r in m['runs'])} |")
    lines += [
        "",
        "Rewrites. Tokens: share of rewrites that keep every identifier, code span, number, path and URL of the "
        "draft (deterministic). After: the same model re-checks its rewrite. Judge: "
        f"`{results['judge']}` with a fixed rubric, on the rewrites of the first {results['judge_runs']} run(s).",
        "",
        "| Model | Rewrites per run | Tokens all kept | Tokens kept | After: low | After: high | Judge: points kept "
        "| No added claims | Request strength kept | Respectful | All four |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for spec, m in models.items():
        if spec == "rules":
            continue
        s = m["summary"]
        lines.append(
            f"| `{spec}` | {cell(s, 'rewrites.rewrites', '{:.1f}')} | {cell(s, 'rewrites.tokens_all_kept')} "
            f"| {cell(s, 'rewrites.token_kept_rate')} | {cell(s, 'rewrites.after_low')} | {cell(s, 'rewrites.after_high')} "
            f"| {cell(s, 'rewrites.judge_technical_points_kept')} | {cell(s, 'rewrites.judge_no_added_claims')} "
            f"| {cell(s, 'rewrites.judge_request_strength_kept')} | {cell(s, 'rewrites.judge_respectful')} "
            f"| {cell(s, 'rewrites.judge_pass')} |")
    return "\n".join(lines) + "\n"
