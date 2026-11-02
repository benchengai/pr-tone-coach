"""Command-line entry point.

    prtone check "Did you even run this? getUser() returns null on 404."
    prtone check --file draft.md --model gpt-6.1-sol
    prtone check --file draft.md --rules            # keyword baseline, no API key
    prtone bench data/gold/synthetic_test.jsonl -m gpt-6-luna gpt-6.1-terra --runs 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RISK_LEVEL = {"low": 0, "medium": 1, "high": 2}


def load_dotenv(path: Path) -> None:
    """Read KEY=VALUE lines into the environment without overriding variables already set."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_env() -> None:
    """`.env` in the repository root, then the file named by PRTONE_ENV_FILE, if any."""
    load_dotenv(PROJECT_ROOT / ".env")
    if extra := os.environ.get("PRTONE_ENV_FILE"):
        load_dotenv(Path(extra).expanduser())


def _api_error_message(e: Exception) -> str | None:
    import openai

    if isinstance(e, openai.AuthenticationError):
        return "the API key was rejected"
    if isinstance(e, openai.RateLimitError):
        return "rate limited, retry later"
    if isinstance(e, openai.APIStatusError):
        return f"API error {e.status_code}: {e.message}"
    if isinstance(e, openai.APIConnectionError):
        return "could not reach the API"
    if isinstance(e, openai.OpenAIError) and "api_key" in str(e):
        return "no OpenAI credentials. Set OPENAI_API_KEY in .env, or use --rules for the offline baseline."
    return None


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {path}", file=sys.stderr)


def cmd_check(args) -> int:
    from .check import check
    from .llm import LLMError, parse_model_spec
    from .report import render_text

    if args.file:
        draft = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    elif args.comment:
        draft = args.comment
    else:
        print("give a comment, or --file PATH (- for stdin)", file=sys.stderr)
        return 2
    if not draft.strip():
        print("the draft is empty", file=sys.stderr)
        return 2
    if args.rules:
        provider, model = "rules", None
    else:
        provider, model = parse_model_spec(args.model)
    try:
        result = check(draft, provider, model)
        if args.recheck and result["rewrite"]:
            again = check(result["rewrite"], provider, model)
            result["rewrite_check"] = {k: again[k] for k in ("target", "risk", "phrases", "llm")}
    except LLMError as e:
        print(f"check failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # API errors: say what went wrong without a traceback
        if (message := _api_error_message(e)) is None:
            raise
        print(f"check failed: {message}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else render_text(result, color=args.color))
    if args.fail_on and RISK_LEVEL[result["risk"]] >= RISK_LEVEL[args.fail_on]:
        return 3
    return 0


def cmd_bench(args) -> int:
    from .bench import bench, render_markdown

    results = bench(Path(args.gold), args.models, args.runs, Path(args.out), judge_spec=args.judge,
                    workers=args.workers, recheck=not args.no_recheck, judge_runs=args.judge_runs)
    report = render_markdown(results)
    print(report)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"wrote {args.report}", file=sys.stderr)
    return 0


SUMMARY_KEYS = ("labels.target.macro_f1", "labels.risk.macro_f1", "labels.flag.f1", "labels.high_recall",
                "labels.phrase_validity", "labels.phrase_hit_rate", "rewrites.tokens_all_kept",
                "rewrites.after_low", "rewrites.judge_pass", "cost_per_comment_usd", "latency_mean_s",
                "toxicity.high_vs_toxic.f1", "toxicity.flag_vs_toxic.f1", "toxicity.flag_vs_toxic.precision",
                "toxicity.flag_vs_toxic.recall", "toxicity.phrase_validity", "toxicity.span_hit_rate")


def cmd_export_demo(args) -> int:
    from .export import export_demo

    summary = {}
    for path in args.results or []:
        results = _read(Path(path))
        table = summary.setdefault(Path(results["gold"]).stem, {"items": results["items"],
                                                                 "runs": results["runs_per_model"], "models": {}})
        for spec, m in results["models"].items():
            table["models"][spec.split(":")[-1]] = {k: m["summary"][k] for k in SUMMARY_KEYS if k in m["summary"]}
    data = export_demo(Path(args.gold), Path(args.bench_dir), args.models, args.run, Path(args.out), summary)
    print(f"wrote {args.out}: {len(data['samples'])} samples", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    load_env()
    parser = argparse.ArgumentParser(prog="prtone", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="check one draft review comment before posting it")
    p.add_argument("comment", nargs="?", help="the draft comment text")
    p.add_argument("--file", "-f", help="read the draft from a file (- for stdin)")
    p.add_argument("--model", "-m", default="openai:gpt-6-luna",
                   help="provider:model or an OpenAI model name (default openai:gpt-6-luna)")
    p.add_argument("--rules", action="store_true", help="keyword baseline only: no API call, no rewrite")
    p.add_argument("--recheck", action="store_true", help="also check the rewrite (one more call)")
    p.add_argument("--json", action="store_true", help="print the full result as JSON")
    p.add_argument("--color", action=argparse.BooleanOptionalAction, default=sys.stdout.isatty(),
                   help="highlight phrases with ANSI colours (default: when printing to a terminal)")
    p.add_argument("--fail-on", choices=("medium", "high"),
                   help="exit with status 3 when the risk is at or above this level (for scripts)")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("bench", help="score models on a gold set, several runs each")
    p.add_argument("gold", help="JSONL gold set (data/gold/*.jsonl)")
    p.add_argument("--models", "-m", nargs="+", required=True, help="model specs; 'rules' is the keyword baseline")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--judge", default="openai:gpt-6.1-sol", help="model that judges rewrites ('none' to skip)")
    p.add_argument("--judge-runs", type=int, default=1, help="judge the rewrites of the first N runs (default 1)")
    p.add_argument("--no-recheck", action="store_true", help="do not re-check rewrites")
    p.add_argument("--workers", type=int, default=6, help="parallel API calls")
    p.add_argument("--out", "-o", required=True, help="folder for cached per-item results")
    p.add_argument("--report", help="also write the markdown table here")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("export-demo", help="export stored bench outputs for the web demo")
    p.add_argument("gold", help="JSONL gold set the bench ran on")
    p.add_argument("--bench-dir", required=True, help="bench output folder (the --out of `bench`)")
    p.add_argument("--models", "-m", nargs="+", required=True)
    p.add_argument("--run", type=int, default=1, help="which run to show (default 1, the judged run)")
    p.add_argument("--results", nargs="*", help="bench results.json files for the results panel")
    p.add_argument("--out", default=str(PROJECT_ROOT / "web/public/samples.json"))
    p.set_defaults(func=cmd_export_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
