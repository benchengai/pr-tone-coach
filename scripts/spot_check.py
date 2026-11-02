"""Print a seeded random sample of judged rewrites for a manual spot check of the judge.

    uv run python scripts/spot_check.py runs/test/synthetic --n 15 --seed 7

Each entry shows the draft, the rewrite, the deterministic token check and the
judge's lists, so a person can agree or disagree with each verdict. The
reviewer's verdicts are recorded by hand in docs/eval/judge-spot-check.md.
"""

import argparse
import json
import random
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("bench_dir")
parser.add_argument("--n", type=int, default=15)
parser.add_argument("--seed", type=int, default=7)
args = parser.parse_args()

records = []
for path in sorted(Path(args.bench_dir).glob("*/run1/*.json")):
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("judge"):
        records.append(record)
random.Random(args.seed).shuffle(records)
for record in records[: args.n]:
    r, j = record["result"], record["judge"]
    print(f"## {record['spec']} {record['id']}  judge pass: {j['pass']}")
    print(f"DRAFT:   {r['draft']}")
    print(f"REWRITE: {r['rewrite']}")
    missing = r["preservation"]["missing"] if r.get("preservation") else []
    print(f"TOKENS missing: {[t['value'] for t in missing]}")
    for key in ("missing_points", "added_claims", "softened_requests", "disrespect_left"):
        if j[key]:
            print(f"  {key}: {j[key]}")
    print()
