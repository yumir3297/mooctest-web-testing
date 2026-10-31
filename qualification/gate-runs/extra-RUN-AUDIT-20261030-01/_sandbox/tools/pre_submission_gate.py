#!/usr/bin/env python3
"""Pre-submission quality gate (contract §4).

    python tools/pre_submission_gate.py --run-id RUN-X [--cases PATH ...]
           [--junit-summary PATH] [--manifest PATH] [--submission PATH]
           [--out DIR] [--gates G0,G1,G2,G3,G4] [--json]

The gate answers two different questions and never mixes them up:

``test_verdict``
    Did the application under test pass?  A confirmed product defect makes this
    ``FAIL``.

``delivery_verdict``
    Is this batch of test work trustworthy and deliverable?  A confirmed,
    reproducible product defect does **not** make the work untrustworthy, so
    ``test_verdict=FAIL`` may coexist with ``delivery_verdict=PASS``.  An
    untriaged failure, a broken script or a forged JUnit summary does make it
    untrustworthy, and that is what fails the delivery.

Exit codes: 0 PASS/WARNING, 1 FAIL, 2 BLOCKED, 3 UNVERIFIED.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for candidate in (str(TOOLS), str(Path(__file__).resolve().parent)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from validators import cases as cases_mod          # noqa: E402
from validators import defects as defects_mod      # noqa: E402
from validators import env as env_mod              # noqa: E402
from validators import evidence_check             # noqa: E402
from validators import package as package_mod     # noqa: E402
from validators import scripts as scripts_mod     # noqa: E402
from validators.common import (                    # noqa: E402
    EXIT_CODE, GATES, Report, load_json, truncate,
)

DEFAULT_OUT = ROOT / "qualification" / "gate-runs"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def split_csv_args(values: Sequence[str] | None) -> list[str]:
    items: list[str] = []
    for value in values or []:
        items.extend(part.strip() for part in str(value).split(",") if part.strip())
    return items


def parse_gates(value: str | None) -> list[str]:
    if not value:
        return list(GATES)
    requested = [g.strip().upper() for g in value.split(",") if g.strip()]
    unknown = [g for g in requested if g not in GATES]
    if unknown:
        raise SystemExit(f"ERROR: unknown gate(s): {', '.join(unknown)}")
    return [g for g in GATES if g in set(requested)]


def manifest_root(manifest_path: Path) -> Path:
    """Project root that evidence paths in ``manifest_path`` are relative to."""
    if manifest_path.parent.name == "evidence":
        return manifest_path.parent.parent
    return manifest_path.parent


def resolve_cases(case_root: Path, values: Sequence[str]) -> list[Path]:
    if values:
        paths: list[Path] = []
        for value in values:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = (case_root / candidate) if not candidate.exists() else candidate
            paths.append(candidate)
        return paths
    default_dir = case_root / "reports" / "test-cases"
    if default_dir.is_dir():
        return sorted(default_dir.glob("*.csv"))
    return []


def resolve_junit(case_root: Path, run_id: str, value: str | None) -> Path:
    if value:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = (case_root / candidate) if not candidate.exists() else candidate
        return candidate
    standard = ROOT / "reports" / "executions" / run_id / "junit-summary.json"
    if standard.is_file():
        return standard
    local = case_root / "junit-summary.json"
    return local if local.is_file() else standard


def compute_test_verdict(run: Mapping[str, Any] | None, manifest_cases: Mapping[str, Mapping[str, Any]],
                         junit_summary_path: Path) -> tuple[str, str]:
    """Answer "did the app pass?" from manifest + JUnit, never from exit codes."""
    statuses = Counter(str(case.get("status") or "") for case in manifest_cases.values())
    junit_failures = 0
    junit_errors = 0
    if junit_summary_path.is_file():
        summary, _ = load_json(junit_summary_path)
        if isinstance(summary, Mapping):
            junit_failures = int(summary.get("failures") or 0)
            junit_errors = int(summary.get("errors") or 0)

    if statuses.get("failed") or junit_failures or junit_errors:
        return "FAIL", "存在失败用例或 JUnit 记录 failure/error"
    if str((run or {}).get("status") or "") == "blocked" or statuses.get("blocked"):
        return "BLOCKED", "运行被环境/夹具阻塞，未完成执行"
    executed = sum(statuses.get(s, 0) for s in ("passed", "xfailed", "skipped"))
    if executed == 0:
        return "UNVERIFIED", "没有任何已执行用例"
    return "PASS", f"{executed} 个用例已执行且无失败"


# --------------------------------------------------------------------------- #
# report rendering
# --------------------------------------------------------------------------- #
def render_human(report_json: Mapping[str, Any]) -> str:
    gates = report_json.get("gate_status") or {}
    lines = [f"== pre_submission_gate {report_json.get('run_id')} ==",
             "  ".join(f"{gate}={gates.get(gate, 'SKIP')}" for gate in GATES),
             f"delivery_verdict={report_json.get('delivery_verdict')}  "
             f"test_verdict={report_json.get('test_verdict')}  exit={report_json.get('exit_code')}",
             ""]
    findings = report_json.get("findings") or []
    if not findings:
        lines.append("no findings")
    for finding in findings:
        flag = " (advisory)" if finding.get("advisory") else ""
        lines.append(f"[{finding['severity']:<10}] {finding['gate']} {finding['code']}{flag} "
                     f"{finding.get('subject', '')}: {finding.get('message', '')}")
    summary = report_json.get("summary") or {}
    lines.append("")
    lines.append("summary: " + " ".join(f"{k}={v}" for k, v in summary.items()))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="pre-submission quality gate (delivery verdict vs test verdict)",
        epilog="exit codes: 0 PASS/WARNING, 1 FAIL, 2 BLOCKED, 3 UNVERIFIED",
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cases", action="append", default=None,
                        help="test case CSV path(s); comma separated or repeatable")
    parser.add_argument("--junit-summary", default=None)
    parser.add_argument("--manifest", default=None, help="default: evidence/manifest.json")
    parser.add_argument("--submission", default=None, help="submission/<RUN-X> directory (G4)")
    parser.add_argument("--out", default=None, help="report directory (default qualification/gate-runs/<run>)")
    parser.add_argument("--gates", default=None, help="subset, e.g. G0,G1,G3")
    parser.add_argument("--requirements", default=None, help="requirement list file for G1")
    parser.add_argument("--suite", action="append", default=None,
                        help="pytest collection path(s) relative to the case root")
    parser.add_argument("--official-submission", action="store_true",
                        help="strict compliance mode: UNVERIFIED compliance items become BLOCKED")
    parser.add_argument("--no-collect", action="store_true", help="skip pytest --collect-only")
    parser.add_argument("--no-env-check", action="store_true", help="skip the live env_check probe")
    parser.add_argument("--timeout", type=int, default=300, help="pytest collection timeout (s)")
    parser.add_argument("--vague-words", default=None,
                        help="extra comma separated non-decidable expected phrases")
    parser.add_argument("--json", action="store_true", help="print the machine readable report on stdout")
    args = parser.parse_args(argv)

    gates = parse_gates(args.gates)
    run_id = args.run_id.strip()
    project_root = ROOT

    manifest_path = Path(args.manifest) if args.manifest else (ROOT / "evidence" / "manifest.json")
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()
    case_root = manifest_root(manifest_path)

    out_dir = Path(args.out) if args.out else (DEFAULT_OUT / run_id)
    if not out_dir.is_absolute():
        out_dir = (ROOT / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    sandbox = out_dir / "_sandbox"

    manifest_data, manifest_error = load_json(manifest_path)
    if not isinstance(manifest_data, Mapping):
        manifest_data = None
    runs = (manifest_data or {}).get("runs") if isinstance(manifest_data, Mapping) else {}
    run = runs.get(run_id) if isinstance(runs, Mapping) else None
    evidence_entries = list((manifest_data or {}).get("evidence") or []) if manifest_data else []
    manifest_cases = dict((run or {}).get("cases") or {}) if isinstance(run, Mapping) else {}

    case_paths = resolve_cases(case_root, split_csv_args(args.cases))
    rows, columns, case_errors = cases_mod.load_case_files(case_paths)

    requirements: set[str] | None = None
    requirements_error: str | None = None
    if args.requirements:
        req_path = Path(args.requirements)
        if not req_path.is_absolute():
            req_path = (case_root / req_path) if not req_path.exists() else req_path
        requirements, problems = cases_mod.load_requirements(req_path)
        requirements_error = "; ".join(problems) if problems else None
        if not requirements:
            requirements = None

    junit_path = resolve_junit(case_root, run_id, args.junit_summary)

    vague_words = list(cases_mod.DEFAULT_VAGUE_EXPECTED)
    if args.vague_words:
        vague_words.extend(w.strip() for w in args.vague_words.split(",") if w.strip())

    automation_files = [scripts_mod.parse_automation(row.get("automation"))[0] for row in rows]
    suites = split_csv_args(args.suite) or scripts_mod.derive_suites(
        case_root, [f for f in automation_files if f])

    report = Report(run_id, gates)
    stats: dict[str, Any] = {}

    # --- G0 ---------------------------------------------------------------
    if "G0" in gates:
        env_check = None if args.no_env_check else env_mod.probe_env_check(
            project_root, timeout=max(30, min(args.timeout, 180)))
        stats["G0"] = env_mod.validate(report, run_id=run_id, run=run, env_check=env_check,
                                       official=args.official_submission,
                                       env_check_expected=not args.no_env_check)

    # --- G1 ---------------------------------------------------------------
    if "G1" in gates:
        if not case_paths:
            report.skip("G1", "no case table")
            report.add("G1", "CASES_NOT_PROVIDED", "WARNING", "cases",
                       "未提供用例表（--cases 或 reports/test-cases/*.csv）：用例质量无法核验")
        else:
            cases_mod.validate(report, rows, columns, case_errors, requirements,
                               requirements_error, vague_words)
            stats["G1"] = cases_mod.summary_of(rows)

    # --- G2 ---------------------------------------------------------------
    if "G2" in gates:
        stats["G2"] = scripts_mod.validate(
            report, run_id=run_id, run=run, manifest_cases=manifest_cases, case_rows=rows,
            junit_summary_path=junit_path, case_root=case_root, sandbox=sandbox,
            suites=suites, timeout=args.timeout, collect=not args.no_collect,
        )

    # --- G3 ---------------------------------------------------------------
    if "G3" in gates:
        stats["G3"] = evidence_check.validate(
            report, run_id=run_id, manifest_path=manifest_path, manifest_data=manifest_data,
            run=run, evidence_entries=evidence_entries, case_root=case_root,
            project_root=project_root, official=args.official_submission,
        )

    # --- G4 ---------------------------------------------------------------
    if "G4" in gates:
        if args.submission:
            submission = Path(args.submission)
            if not submission.is_absolute():
                submission = (ROOT / submission).resolve()
            stats["G4"] = package_mod.validate(report, submission)
        else:
            report.skip("G4", "no --submission")
            report.add("G4", "PACKAGE_SKIPPED", "WARNING", "submission",
                       "未提供 --submission：交付包结构与哈希未校验", advisory=True)

    # --- verdicts ----------------------------------------------------------
    delivery_verdict = report.delivery_verdict()
    if delivery_verdict == "PASS" and report.checks == 0:
        delivery_verdict = "UNVERIFIED"
    test_verdict, test_reason = compute_test_verdict(run, manifest_cases, junit_path)
    exit_code = EXIT_CODE[delivery_verdict]

    report_payload: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "generated_at": now_iso(),
        "gate_status": report.gate_status(),
        "delivery_verdict": delivery_verdict,
        "test_verdict": test_verdict,
        "findings": [finding.to_dict() for finding in report.findings],
        "summary": report.summary(),
        "advisory": {
            "count": sum(1 for f in report.findings if f.advisory),
            "codes": [f.code for f in report.findings if f.advisory],
            "note": "advisory findings 只记录不阻断本地演练；--official-submission 会把合规项升级为 BLOCKED",
        },
        "exit_code": exit_code,
        "verdict_notes": {
            "delivery": "测试成果是否可信、可交付（确认缺陷不会拉低该结论）",
            "test": test_reason,
        },
        "inputs": {
            "manifest": str(manifest_path),
            "manifest_schema": (manifest_data or {}).get("schema_version") if manifest_data else None,
            "manifest_error": manifest_error,
            "cases": [str(p) for p in case_paths],
            "junit_summary": str(junit_path),
            "requirements": args.requirements,
            "submission": args.submission,
            "official_submission": bool(args.official_submission),
            "gates": gates,
        },
        "execution": {
            "manifest_case_counts": stats.get("G2", {}).get("manifest_case_counts", {}),
            "junit_summary_passed": stats.get("G2", {}).get("junit_summary_passed"),
            "junit_summary_counts": stats.get("G2", {}).get("junit_summary_counts"),
            "junit_xml_counts": stats.get("G2", {}).get("junit_xml_counts"),
            "collected_nodes": stats.get("G2", {}).get("collected_nodes", []),
            "failed_case_triage": stats.get("G3", {}).get("failed_case_triage", {}),
        },
        "evidence": {
            "verify": stats.get("G3", {}).get("evidence_verify", {}),
            "manifest_audit": stats.get("G3", {}).get("manifest_audit", {}),
        },
        "compliance": {
            "ai_use_confirmed": stats.get("G0", {}).get("ai_use_confirmed"),
            "ai_status": "VERIFIED" if stats.get("G0", {}).get("ai_use_confirmed") else "UNVERIFIED",
            "official_submission": bool(args.official_submission),
            "env_check": stats.get("G0", {}).get("env_check"),
        },
        "stats": stats,
    }

    report_path = out_dir / "gate-report.json"
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    if args.json:
        sys.stdout.write(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render_human(report_payload) + "\n")
        sys.stdout.write(f"report: {report_path}\n")
    sys.stdout.flush()
    return exit_code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
