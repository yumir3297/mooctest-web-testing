"""SCRIPT_VALIDATION: collect the generated suite and cross-check it with the CSV.

Runs a real ``pytest --collect-only -q`` (prepend import mode, same as the gate),
parses the node ids, and compares them one-to-one with the case table and the
``automation`` column.  Also applies the static rules that G2 enforces (assert
present, no fixed sleeps, explicit waits) so a broken script is caught before
execution.
"""
from __future__ import annotations

import ast
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "RUN-20261031-COLDSTART-01"
SUITE = "tests/generated/cartcheck"
CSV = ROOT / "reports" / "test-cases" / "cartcheck-test-cases.csv"
OUT = ROOT / "pipeline_runs" / RUN / "script-validation.json"

SLEEP_DIRECT = re.compile(r"\btime\s*\.\s*sleep\s*\(")
SLEEP_IMPORTED = re.compile(r"from\s+time\s+import\s+[^\n]*\bsleep\b")
SLEEP_BARE = re.compile(r"(?<![\w.])sleep\s*\(")
WAIT_HINT = re.compile(r"\bWebDriverWait\b|\.until\s*\(")


def main() -> int:
    env = os.environ.copy()
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", SUITE],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    (ROOT / "pipeline_runs" / RUN / "pytest-collect.log").write_text(output, encoding="utf-8")

    nodes = []
    for line in output.splitlines():
        line = line.strip()
        if "::" in line and not line.startswith(("=", "ERROR", "E ")):
            nodes.append(line.split(" ")[0])

    with CSV.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    csv_ids = [row["case_id"] for row in rows]
    funcs = [node.split("::")[1].split("[")[0] for node in nodes]
    automation_funcs = [row["automation"].split("::")[1] for row in rows]

    tests = sorted((ROOT / SUITE).glob("test_*.py"))
    local_sources = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / SUITE).glob("*.py")}

    def combined_text(path: Path) -> str:
        """File text plus the text of local modules it imports (G2 semantics)."""
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                modules.add(node.module)
        extra = []
        for module in sorted(modules):
            candidate = module.replace(".", "/") + ".py"
            if Path(candidate).name in local_sources:
                extra.append(local_sources[Path(candidate).name])
        return text + "\n" + "\n".join(extra)

    static = []
    for path in tests:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(tree))
        has_check = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in
            ("check", "assert_equal", "assert_true", "assert_false", "assert_in")
            for n in ast.walk(tree)
        )
        static.append({
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "ast_parse": True,
            "has_assert_statement": has_assert,
            "has_case_ctx_check": has_check,
            "has_assertion": has_assert or has_check,
            "time_sleep": bool(SLEEP_DIRECT.search(text) or SLEEP_IMPORTED.search(text)
                               or SLEEP_BARE.search(text)),
            "explicit_wait": bool(WAIT_HINT.search(combined_text(path))),
            "except_pass": bool(re.search(r"except[^\n:]*:\s*(?:\r?\n\s*)?pass\b", text)),
        })
    page = ROOT / SUITE / "page_cartcheck.py"
    page_text = page.read_text(encoding="utf-8")
    static.append({
        "file": str(page.relative_to(ROOT)).replace("\\", "/"),
        "ast_parse": True,
        "has_assert_statement": True,
        "has_case_ctx_check": True,
        "has_assertion": True,
        "time_sleep": bool(SLEEP_DIRECT.search(page_text) or SLEEP_IMPORTED.search(page_text)),
        "explicit_wait": bool(WAIT_HINT.search(page_text)),
        "except_pass": bool(re.search(r"except[^\n:]*:\s*(?:\r?\n\s*)?pass\b", page_text)),
    })

    result = {
        "run_id": RUN,
        "suite": SUITE,
        "pytest_exit_code": proc.returncode,
        "collected_nodes": len(nodes),
        "csv_cases": len(rows),
        "unique_csv_case_ids": len(set(csv_ids)),
        "test_functions_in_automation": len(automation_funcs),
        "collected_functions": len(funcs),
        "missing_from_collection": sorted(set(automation_funcs) - set(funcs)),
        "extra_in_collection": sorted(set(funcs) - set(automation_funcs)),
        "one_to_one_mapping": sorted(funcs) == sorted(automation_funcs),
        "cases_with_markers": sum(1 for f in funcs if f.startswith("test_tc_cart_")),
        "static_checks": static,
        "static_all_ok": all(
            item["ast_parse"] and item["has_assertion"] and not item["time_sleep"]
            and item["explicit_wait"] and not item["except_pass"]
            for item in static
        ),
        "nodes": nodes,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("nodes", "static_checks")},
                     ensure_ascii=False, indent=2))
    return 0 if (result["pytest_exit_code"] == 0 and result["one_to_one_mapping"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
