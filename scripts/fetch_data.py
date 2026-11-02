"""Download the external human-labelled dataset into data/external/ (git-ignored).

    uv run python -I scripts/fetch_data.py

ToxiSpanSE (Sarker et al., ESEM 2023) labels the ToxiCR code review comments
as toxic or not and marks the toxic words. The file is GPL-3.0 and is not
redistributed here; only the row numbers of the sampled comments are committed
(data/gold/toxispanse_test_ids.json).
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "toxispanse/CR_full_span_dataset.csv":
        "https://raw.githubusercontent.com/WSU-SEAL/ToxiSpanSE/main/models/CR_full_span_dataset.csv",
}

for rel, url in FILES.items():
    path = ROOT / "data/external" / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
        if len(data) > 50_000_000:
            sys.exit(f"{url} is larger than 50 MB; not saved")
        path.write_bytes(data)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{rel}: {path.stat().st_size:,} bytes, sha256 {digest}")
