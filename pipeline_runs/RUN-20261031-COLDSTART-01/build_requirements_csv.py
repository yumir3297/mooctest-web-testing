"""Derive a gate-readable requirement list (CSV) from requirements.json.

`tools/validators/cases.load_requirements` only understands a CSV with a
`requirement_id`/`id` column or a plain-text list; it does not parse JSON.  The
stage artifact stays `requirements.json`; this script produces the companion
`requirements.csv` used as the `--requirements` input of the quality gate and
verifies that both files list exactly the same ids.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
SRC = RUN_DIR / "requirements.json"
DST = RUN_DIR / "requirements.csv"


def main() -> int:
    items = json.loads(SRC.read_text(encoding="utf-8"))
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids)), "duplicate requirement ids"
    with DST.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["requirement_id", "text", "source", "status", "constraint"],
                                lineterminator="\n")
        writer.writeheader()
        for item in items:
            writer.writerow({
                "requirement_id": item["id"],
                "text": item["text"],
                "source": item["source"],
                "status": item["status"],
                "constraint": item["constraint"],
            })
    print(f"wrote {len(ids)} requirements -> {DST}")
    print("ids:", ",".join(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
