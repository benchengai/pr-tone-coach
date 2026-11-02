"""Draw the held-out sample of human-labelled code review comments from ToxiSpanSE.

    uv run python -I scripts/fetch_data.py
    uv run python -I scripts/make_toxispanse_sample.py

Population: unique comment texts of 20 to 600 characters (drops "Done."-style
acknowledgements and long pasted logs). Sample: 50 toxic and 50 non-toxic,
seeded. Writes the committed id list (row numbers and text hashes, no text) and
the full sample with text and spans to data/external/ (git-ignored). If the id
list exists it is reused, so the sample stays the same.
"""

import ast
import csv
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/external/toxispanse/CR_full_span_dataset.csv"
IDS = ROOT / "data/gold/toxispanse_test_ids.json"
OUT = ROOT / "data/external/toxispanse_test.jsonl"
SEED, PER_CLASS, MIN_LEN, MAX_LEN = 2026, 50, 20, 600

csv.field_size_limit(10**8)


def ranges(offsets: list[int]) -> list[list[int]]:
    """[3, 4, 5, 9, 10] -> [[3, 6], [9, 11]] (end-exclusive)."""
    out = []
    for i in sorted(set(offsets)):
        if out and out[-1][1] == i:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return out


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


rows = list(csv.DictReader(SOURCE.open(encoding="utf-8", newline="")))
if IDS.exists():
    chosen = json.loads(IDS.read_text(encoding="utf-8"))["items"]
else:
    seen, pool = set(), {True: [], False: []}
    for i, r in enumerate(rows):
        text = r["text"]
        if not (MIN_LEN <= len(text.strip()) <= MAX_LEN) or text in seen:
            continue
        seen.add(text)
        pool[r["is_toxic"] == "1"].append(i)
    rng = random.Random(SEED)
    picked = rng.sample(pool[True], PER_CLASS) + rng.sample(pool[False], PER_CLASS)
    rng.shuffle(picked)
    chosen = [{"row": i, "sha256_16": sha(rows[i]["text"]), "toxic": int(rows[i]["is_toxic"] == "1")} for i in picked]
    IDS.write_text(json.dumps({
        "source": "https://raw.githubusercontent.com/WSU-SEAL/ToxiSpanSE/main/models/CR_full_span_dataset.csv",
        "licence": "GPL-3.0 (text not redistributed here)",
        "population": {"unique_texts_20_to_600_chars": len(pool[True]) + len(pool[False]),
                       "toxic": len(pool[True]), "non_toxic": len(pool[False])},
        "seed": SEED,
        "items": chosen,
    }, indent=1) + "\n", encoding="utf-8")

with OUT.open("w", encoding="utf-8") as f:
    for k, c in enumerate(chosen):
        r = rows[c["row"]]
        assert sha(r["text"]) == c["sha256_16"], f"row {c['row']} changed upstream"
        spans = ranges(ast.literal_eval(r["spans"]))
        f.write(json.dumps({"id": f"x{k + 1:03d}", "row": c["row"], "source": "toxispanse", "text": r["text"],
                            "toxic": c["toxic"], "spans": spans}, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(chosen)} comments) and {IDS}")
