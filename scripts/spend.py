"""Sum the API spend recorded in cached bench runs (check, re-check and judge calls).

    uv run python scripts/spend.py runs/
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "runs")
by_model, total = defaultdict(float), 0.0
for path in root.rglob("*.json"):
    record = json.loads(path.read_text(encoding="utf-8"))
    if "spec" not in record:
        continue
    for key in ("result", "recheck", "judge"):
        llm = (record.get(key) or {}).get("llm") or {}
        if llm.get("cost_usd"):
            by_model[f"{llm['model']} ({key})"] += llm["cost_usd"]
            total += llm["cost_usd"]
for name, cost in sorted(by_model.items()):
    print(f"{name:45s} ${cost:.4f}")
print(f"{'total':45s} ${total:.4f}")
