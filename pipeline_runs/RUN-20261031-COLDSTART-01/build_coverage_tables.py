"""Build the coverage.md mapping tables from the case table + manifest."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "RUN-20261031-COLDSTART-01"
CSV = ROOT / "reports" / "test-cases" / "cartcheck-test-cases.csv"
OUT = ROOT / "pipeline_runs" / RUN / "coverage.md"

requirements = json.loads((ROOT / "pipeline_runs" / RUN / "requirements.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "evidence" / "manifest.json").read_text(encoding="utf-8"))
run = manifest["runs"][RUN]
rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig", newline="")))

by_req: dict[str, list[dict]] = {}
for row in rows:
    for req in [r.strip() for r in row["requirement_ids"].replace(";", ",").split(",") if r.strip()]:
        by_req.setdefault(req, []).append(row)

lines = ["| 需求 | 用例 | 执行结果 | 首要证据 |", "|---|---|---|---|"]
for item in requirements:
    rid = item["id"]
    cases = by_req.get(rid, [])
    if not cases:
        lines.append(f"| {rid} | （无） | 未覆盖 | - |")
        continue
    for row in cases:
        case = run["cases"].get(row["case_id"], {})
        ev = (case.get("evidence") or ["-"])[0]
        lines.append(f"| {rid} | {row['case_id']} | {row['status']} | {ev} |")

counts = {"passed": 0, "failed": 0}
for row in rows:
    counts[row["status"]] = counts.get(row["status"], 0) + 1

text = "\n".join(lines)
print(text)
print()
print("STATUS", counts)
print("REQ_TOTAL", len(requirements), "REQ_COVERED", sum(1 for i in requirements if by_req.get(i["id"])))
