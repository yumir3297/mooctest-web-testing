"""Write the real execution results back into the case table.

The CSV is the delivery artifact, so `status` / `actual` / `executed_in_run`
must reflect what actually happened - never a hand-written "passed".  Values
come from the evidence manifest (assertions + case actual) and, for failed
cases, from the independent reproduction run (`repro.json`) which repeats the
same interaction.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "RUN-20261031-COLDSTART-01"
CSV = ROOT / "reports" / "test-cases" / "cartcheck-test-cases.csv"
MANIFEST = ROOT / "evidence" / "manifest.json"
REPRO = ROOT / "pipeline_runs" / RUN / "repro.json"
CASES = ROOT / "pipeline_runs" / RUN / "cases.json"

COLUMNS = ["case_id", "title", "priority", "requirement_ids", "case_type", "method",
           "preconditions", "test_data", "steps", "expected", "actual", "status",
           "automation", "evidence_required", "executed_in_run", "notes"]


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    run = manifest["runs"][RUN]
    cases = run["cases"]
    repro = {item["case_id"]: item for item in json.loads(REPRO.read_text(encoding="utf-8"))["results"]}

    with CSV.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    updated = 0
    structured = json.loads(CASES.read_text(encoding="utf-8"))
    by_id = {item["case_id"]: item for item in structured["cases"]}

    for row in rows:
        cid = row["case_id"]
        case = cases.get(cid)
        if not case:
            row["status"] = "NOT_RUN"
            row["actual"] = "未在 manifest 中登记（未执行）"
            continue
        status = case["status"]
        assertions = case.get("assertions") or []
        first_ev = (case.get("evidence") or [""])[0]
        if status == "passed":
            row["status"] = "passed"
            row["actual"] = case.get("actual") or "(断言通过，无失败信息)"
        elif status == "failed":
            row["status"] = "failed"
            obs = repro.get(cid)
            failing = next((a for a in assertions if not a.get("passed")), None)
            detail = ""
            if failing:
                detail = (f"断言失败：{failing['name']} 期望 {failing['expected']}，"
                          f"实际 {failing['actual']}")
            if obs:
                row["actual"] = (f"discount={obs['discount']}；payable={obs['payable']}；"
                                 f"message={obs['message'] or '(空)'}；{detail}")
            else:
                row["actual"] = detail or (case.get("actual") or "")[:300]
        else:
            row["status"] = status
            row["actual"] = case.get("actual") or ""
        row["executed_in_run"] = RUN
        updated += 1
        item = by_id.get(cid)
        if item:
            item["test_status"] = row["status"].upper() if row["status"] != "passed" else "PASS"
            item["test_status"] = {"passed": "PASS", "failed": "FAIL"}.get(row["status"], row["status"].upper())
            item["evidence_ref"] = first_ev
    with CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    structured["cases"] = [by_id[k] for k in [r["case_id"] for r in rows] if k in by_id]
    CASES.write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated {updated} rows in {CSV}")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print("status:", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
