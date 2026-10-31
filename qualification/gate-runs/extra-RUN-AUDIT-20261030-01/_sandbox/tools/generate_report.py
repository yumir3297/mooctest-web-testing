#!/usr/bin/env python3
"""Generate Markdown + HTML + JSON execution reports from the evidence manifest.

Design rules enforced here (see ``docs/REPORTING.md``):

* ``case.expected`` / ``case.actual`` are case-level oracles. Assertion detail is
  rendered separately and a bare assertion boolean is never promoted to a case
  expectation.
* every environment field is rendered; a missing field shows ``未采集`` instead
  of disappearing from the table;
* the case table is *run scoped*: only a CSV whose ``executed_in_run`` contains
  this run id is used. There is no fallback, so a report never inherits another
  run's coverage gaps;
* a delivery gate runs by default and fails closed (exit 1 FAIL, 2 BLOCKED).
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import report_schema as rs  # noqa: E402

ROOT = rs.ROOT
IMAGE_KINDS = rs.IMAGE_KINDS
MISSING = rs.MISSING_VALUE
GENERATOR_VERSION = "2.0"

ENV_FIELDS = [
    ("os", "操作系统"),
    ("platform", "平台"),
    ("python", "Python"),
    ("selenium", "Selenium"),
    ("pytest", "pytest"),
    ("chrome", "Chrome"),
    ("chromedriver", "ChromeDriver"),
    ("node", "Node.js"),
    ("target", "目标 URL"),
]
ENV_EXTRA_LABELS = {
    "chrome_path": "Chrome 路径",
    "label": "运行标签",
    "driver_path": "ChromeDriver 路径",
}
SEVERITY_LABELS = {"blocker": "阻断", "critical": "严重", "major": "主要",
                   "minor": "次要", "trivial": "轻微"}
CATEGORY_LABELS = {"APP": "产品", "SCRIPT": "脚本", "ENV": "环境", "DATA": "数据",
                   "LOCATOR": "定位", "TIMING": "时序", "UNKNOWN": "未定"}
DEFECT_STATUS_LABELS = {"open": "待处理", "confirmed": "已确认", "suspected": "疑似",
                        "needs_review": "待复核", "not_a_defect": "非缺陷", "fixed": "已修复"}
REPRO_LABELS = {"not-reproduced": "未复现", "reproduced": "已复现",
                "intermittent": "偶现", "blocked": "阻塞，无法复现"}
UNCONFIRMED_DEFECT_STATES = {"suspected", "needs_review"}
GATE_EXIT_CODES = {"PASS": 0, "WARNING": 0, "FAIL": 1, "BLOCKED": 2, "DISABLED": 0}


def _mdd(value: Any, default: str = MISSING) -> str:
    if value is None or str(value).strip() == "":
        return default
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _text(value: Any, default: str = MISSING) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _status_label(status: str) -> str:
    return rs.status_label(status)


def _verdict_label(verdict: Any) -> str:
    v = str(verdict or "")
    if "no-diff" in v or "identical" in v:
        return f"{v}（未检测到超过阈值的像素差异）"
    if "change" in v or "diff" in v:
        return f"{v}（受控变化，待人工复核，不构成缺陷结论）"
    return f"{v}（待人工复核）"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# paths
# --------------------------------------------------------------------------- #
@dataclass
class Paths:
    project_root: Path
    manifest_path: Path
    reports_root: Path

    @property
    def evidence_root(self) -> Path:
        return self.manifest_path.parent

    @property
    def diff_root(self) -> Path:
        return self.evidence_root / "diff"

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.project_root.resolve()).as_posix()
        except Exception:
            return str(path)


def default_paths() -> Paths:
    return Paths(project_root=ROOT, manifest_path=ROOT / "evidence" / "manifest.json",
                 reports_root=ROOT / "reports")


# --------------------------------------------------------------------------- #
# manifest helpers
# --------------------------------------------------------------------------- #
def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")
    return rs.json_load(path)


def _run_cases(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return run.get("cases") or {}


def _case_evidence(data: dict[str, Any], case: dict[str, Any]) -> list[dict[str, Any]]:
    ids = set(case.get("evidence", []) or [])
    return [e for e in data.get("evidence", []) if e.get("evidence_id") in ids]


def _evidence_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {e["evidence_id"]: e for e in data.get("evidence", []) if e.get("evidence_id")}


def _verify_evidence(data: dict[str, Any], run_id: str, project_root: Path) -> dict[str, Any]:
    """Hash + path verification, mirroring ``tools/evidence.py verify``."""
    entries = [e for e in data.get("evidence", []) if e.get("run_id") == run_id]
    missing: list[str] = []
    mismatched: list[str] = []
    cross_run: list[str] = []
    unscoped: list[str] = []
    duplicates: list[str] = []
    ok = 0
    seen: set[tuple[str, str]] = set()
    for e in entries:
        rel = e.get("path", "")
        referenced = set(rs.RUN_ID_RE.findall(rel))
        if referenced and e.get("run_id") not in referenced:
            cross_run.append(rel)
        if not referenced:
            unscoped.append(rel)
        key = (str(e.get("run_id")), rel)
        if key in seen:
            duplicates.append(rel)
        seen.add(key)
        p = Path(rel)
        if not p.is_absolute():
            p = project_root / rel
        if not p.is_file():
            missing.append(rel)
            continue
        try:
            size_ok = p.stat().st_size == e.get("size_bytes")
            hash_ok = rs.sha256_file(p) == e.get("sha256")
        except OSError:
            missing.append(rel)
            continue
        if not size_ok or not hash_ok:
            mismatched.append(rel)
            continue
        ok += 1
    return {
        "checked": len(entries),
        "ok": ok,
        "missing": missing,
        "mismatched": mismatched,
        "cross_run": cross_run,
        "unscoped": unscoped,
        "duplicates": duplicates,
    }


def _run_summary(run: dict[str, Any], run_id: str, data: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for case in _run_cases(run).values():
        status = case.get("status", "not-run")
        counts[status] = counts.get(status, 0) + 1
    run_evidence = [e for e in data.get("evidence", []) if e.get("run_id") == run_id]
    defect_count = sum(len(c.get("defects") or []) for c in _run_cases(run).values())
    return {
        "run_id": run_id,
        "label": run.get("label", ""),
        "target": run.get("target", ""),
        "status": run.get("status", ""),
        "status_label": _status_label(run.get("status", "")),
        "stage": run.get("stage", ""),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "case_counts": counts,
        "case_total": sum(counts.values()),
        "evidence_count": len(run_evidence),
        "defect_count": defect_count,
    }


def _load_junit(out_dir: Path, override: Path | None = None) -> dict[str, Any] | None:
    path = override if override is not None else out_dir / "junit-summary.json"
    if not path.is_file():
        return None
    try:
        data = rs.json_load(path)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _junit_counts(junit: dict[str, Any] | None) -> dict[str, int]:
    out = {"total": 0, "passed": 0, "failed": 0, "xfailed": 0, "other": 0}
    if not junit:
        return out
    cases = junit.get("cases") or []
    if cases:
        out["total"] = len(cases)
        for c in cases:
            st = c.get("status")
            if st == "passed":
                out["passed"] += 1
            elif st == "failed":
                out["failed"] += 1
            elif st == "xfailed":
                out["xfailed"] += 1
            else:
                out["other"] += 1
    else:
        out["total"] = int(junit.get("tests") or 0)
        out["failed"] = int(junit.get("failures") or 0) + int(junit.get("errors") or 0)
        out["xfailed"] = int(junit.get("xfailed") or 0)
        out["passed"] = max(out["total"] - out["failed"] - out["xfailed"], 0)
    return out


def _visual_metrics(paths: Paths, run_id: str) -> list[dict[str, Any]]:
    base = paths.diff_root / run_id
    out: list[dict[str, Any]] = []
    if not base.is_dir():
        return out
    for p in sorted(base.rglob("metrics.json")):
        try:
            metrics = rs.json_load(p)
            metrics["_metrics_path"] = paths.rel(p)
            metrics["_dir"] = paths.rel(p.parent)
            out.append(metrics)
        except Exception:
            continue
    return out


def _design_doc(paths: Paths, run_id: str) -> Path | None:
    base = paths.reports_root / "test-cases"
    if not base.is_dir():
        return None
    for p in sorted(base.glob("*.md")):
        try:
            if run_id in p.read_text(encoding="utf-8-sig"):
                return p
        except Exception:
            continue
    return None


# --------------------------------------------------------------------------- #
# environment
# --------------------------------------------------------------------------- #
def _looks_placeholder(text: str) -> bool:
    return text.startswith("<")


def _build_environment(run: dict[str, Any], probe: dict[str, Any] | None) -> tuple[dict[str, str], dict[str, Any]]:
    recorded = dict(run.get("environment") or {})
    env: dict[str, str] = {}
    meta: dict[str, Any] = {}
    for key, label in ENV_FIELDS:
        raw = recorded.get(key)
        source = "run"
        if key == "os" and not str(raw or "").strip() and str(recorded.get("platform") or "").strip():
            raw = recorded.get("platform")
            source = "run(platform)"
        text = "" if raw is None else str(raw).strip()
        if not text:
            env[key] = MISSING
            meta[key] = {"label": label, "value": MISSING, "raw": "", "source": "missing"}
        elif _looks_placeholder(text):
            env[key] = f"{MISSING}（运行记录为 {text}）"
            meta[key] = {"label": label, "value": MISSING, "raw": text,
                         "source": "run-placeholder"}
        else:
            env[key] = text
            meta[key] = {"label": label, "value": text, "raw": text, "source": source}
    for key, value in recorded.items():
        if key in env:
            continue
        text = str(value or "").strip()
        if not text:
            continue
        label = ENV_EXTRA_LABELS.get(key, key)
        env[key] = text
        meta[key] = {"label": label, "value": text, "raw": text, "source": "run"}
    if probe:
        meta["__probe__"] = {
            "probed_at": probe.get("probed_at"),
            "note": probe.get("note"),
        }
    return env, meta


# --------------------------------------------------------------------------- #
# cases
# --------------------------------------------------------------------------- #
def _enrich_defect(defect: dict[str, Any], ev_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out = dict(defect)
    status = str(defect.get("status") or "open")
    out["severity_label"] = SEVERITY_LABELS.get(str(defect.get("severity") or ""), "")
    out["status_label"] = DEFECT_STATUS_LABELS.get(status, status)
    out["category_label"] = CATEGORY_LABELS.get(str(defect.get("category") or ""), "")
    out["repro_label"] = REPRO_LABELS.get(str(defect.get("repro_status") or ""), "")
    out["unconfirmed"] = status in UNCONFIRMED_DEFECT_STATES
    out["evidence_ids"] = list(defect.get("evidence") or [])
    out["evidence_paths"] = [ev_index[eid]["path"] for eid in out["evidence_ids"] if eid in ev_index]
    out["missing_fields"] = [
        field for field in ("severity_rationale", "category", "environment", "preconditions",
                            "repro_steps", "repro_status", "expected", "actual")
        if not defect.get(field)
    ]
    return out


def _build_cases(data: dict[str, Any], run: dict[str, Any], table_rows: list[dict[str, str]],
                 junit: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = rs.row_map(table_rows)
    ev_index = _evidence_index(data)
    junit_cases = (junit or {}).get("cases") or []
    junit_by_name = {c.get("name"): c for c in junit_cases if c.get("name")}
    cases: list[dict[str, Any]] = []
    defects: list[dict[str, Any]] = []
    for cid, case in sorted(_run_cases(run).items()):
        assertions = list(case.get("assertions") or [])
        evidence = [ev for ev in _case_evidence(data, case)]
        expected = rs.classify_case_expected(case.get("expected"), len(assertions))
        actual = rs.classify_case_actual(case.get("actual"), assertions)
        row = rows.get(cid)
        meta = dict(case.get("meta") or {})
        title = _text((row or {}).get("title"), "") or _text(case.get("title"), cid)
        title_source = "case-table" if (row or {}).get("title") else "manifest"
        case_defects = [_enrich_defect(d, ev_index) for d in (case.get("defects") or [])]
        defects.extend(case_defects)
        log_path = case.get("log_path")
        log_file = None
        if log_path:
            candidate = Path(log_path)
            log_file = candidate if candidate.is_absolute() else ROOT / log_path
        junit_entry = junit_by_name.get(case.get("title") or "") or junit_by_name.get(title)
        automation = (row or {}).get("automation") or ""
        if not automation and junit_entry:
            classname = str(junit_entry.get("classname") or "").replace(".", "/")
            func = junit_entry.get("name")
            if classname and func:
                automation = f"{classname}.py::{func}"
        cases.append({
            "case_id": cid,
            "title": title,
            "source_title": str(case.get("title") or ""),
            "title_source": title_source,
            "status": case.get("status", "not-run"),
            "status_label": _status_label(case.get("status", "not-run")),
            "expected": expected["value"],
            "expected_raw": expected["raw"],
            "expected_source": expected["source"],
            "expected_invalid": expected["invalid"],
            "expected_note": expected["reason"],
            "actual": actual["value"],
            "actual_raw": actual["raw"],
            "actual_source": actual["source"],
            "assertions": assertions,
            "assertion_count": len(assertions),
            "assertions_passed": sum(1 for a in assertions if a.get("passed")),
            "steps": list(case.get("steps") or []),
            "evidence": evidence,
            "evidence_count": len(evidence),
            "evidence_complete": len(evidence) > 0,
            "defects": case_defects,
            "log_path": log_path,
            "log_exists": bool(log_file and log_file.is_file()),
            "duration_ms": case.get("duration_ms"),
            "meta": meta,
            "requirement_ids": rs.split_ids(meta.get("requirement_ids")
                                            or (row or {}).get("requirement_ids")),
            "priority": (row or {}).get("priority") or meta.get("priority") or "",
            "case_type": (row or {}).get("case_type") or meta.get("case_type") or "",
            "method": (row or {}).get("method") or meta.get("method") or "",
            "preconditions": _split_blocks((row or {}).get("preconditions")),
            "test_data": _text((row or {}).get("test_data"), ""),
            "design_status": rs.design_status(row),
            "in_case_table": bool(row),
            "automation": automation,
            "junit": junit_entry,
            "needs_review": (case.get("status") == "xfailed"
                             or any(d["unconfirmed"] for d in case_defects)),
        })
    return cases, defects


def _split_blocks(value: Any) -> list[str]:
    text = _text(value, "")
    if not text:
        return []
    parts = [p.strip() for p in text.replace("；", "\n").replace(";", "\n").split("\n")]
    return [p for p in parts if p]


def _build_strategy(cases: list[dict[str, Any]], table_found: bool) -> dict[str, Any]:
    methods: dict[str, list[str]] = {}
    types: dict[str, list[str]] = {}
    priorities: dict[str, list[str]] = {}
    source = "none"
    for case in cases:
        if case["method"]:
            methods.setdefault(case["method"], []).append(case["case_id"])
        if case["case_type"]:
            types.setdefault(case["case_type"], []).append(case["case_id"])
        if case["priority"]:
            priorities.setdefault(case["priority"], []).append(case["case_id"])
    missing_method = [c["case_id"] for c in cases if not c["method"]]
    if methods:
        from_table = [c for c in cases if c["method"] and c["in_case_table"]]
        source = "case-table" if from_table else "manifest-meta"
    elif table_found:
        source = "case-table-empty"
    else:
        source = "none"
    note = ""
    if not methods:
        if not table_found:
            note = "未找到本运行的用例表，无法从 method 列聚合设计方法分布。"
        else:
            note = "本运行的用例表没有 method 列取值，无法聚合设计方法分布。"
    return {
        "design_source": source,
        "methods": [{"method": k, "count": len(v), "case_ids": v} for k, v in sorted(
            methods.items(), key=lambda kv: (-len(kv[1]), kv[0]))],
        "case_types": [{"case_type": k, "count": len(v), "case_ids": v} for k, v in sorted(
            types.items(), key=lambda kv: (-len(kv[1]), kv[0]))],
        "priorities": [{"priority": k, "count": len(v), "case_ids": v} for k, v in sorted(
            priorities.items())],
        "missing_method_cases": missing_method,
        "note": note,
    }


def _build_coverage(cases: list[dict[str, Any]], table_rows: list[dict[str, str]],
                    table_found: bool, run_id: str) -> dict[str, Any]:
    by_case = {c["case_id"]: c for c in cases}
    requirements: dict[str, dict[str, Any]] = {}
    for row in table_rows:
        cid = row["case_id"]
        for req in rs.split_ids(row.get("requirement_ids")):
            entry = requirements.setdefault(req, {"requirement_id": req, "case_ids": [],
                                                  "executed_case_ids": [], "status_counts": {}})
            if cid not in entry["case_ids"]:
                entry["case_ids"].append(cid)
    for case in cases:
        for req in case["requirement_ids"]:
            entry = requirements.setdefault(req, {"requirement_id": req, "case_ids": [],
                                                  "executed_case_ids": [], "status_counts": {}})
            if case["case_id"] not in entry["case_ids"]:
                entry["case_ids"].append(case["case_id"])
    executed_states = {"passed", "failed", "xfailed", "blocked", "skipped"}
    for req, entry in requirements.items():
        for cid in entry["case_ids"]:
            case = by_case.get(cid)
            status = case["status"] if case else "not-run"
            entry["status_counts"][status] = entry["status_counts"].get(status, 0) + 1
            if case and status in executed_states:
                entry["executed_case_ids"].append(cid)
    items = []
    for req in sorted(requirements):
        entry = requirements[req]
        items.append({
            **entry,
            "covered_by_design": bool(entry["case_ids"]),
            "executed": bool(entry["executed_case_ids"]),
            "case_total": len(entry["case_ids"]),
            "executed_total": len(entry["executed_case_ids"]),
        })
    unmapped = [c["case_id"] for c in cases if not c["requirement_ids"]]
    not_run: list[dict[str, str]] = []
    partial: list[dict[str, str]] = []
    for row in table_rows:
        cid = row["case_id"]
        design = rs.design_status(row)
        item = {"case_id": cid, "title": row.get("title", ""), "design_status": design}
        if cid in by_case and by_case[cid]["status"] in executed_states:
            if "部分覆盖" in design:
                partial.append(item)
            continue
        if design.startswith("未执行") or design.startswith("未覆盖"):
            not_run.append(item)
        elif "部分覆盖" in design:
            partial.append(item)
        elif not design and cid not in by_case:
            not_run.append({**item, "design_status": "未执行（设计状态未登记）"})
    return {
        "case_table_found": table_found,
        "run_id": run_id,
        "requirements": items,
        "requirements_without_execution": [i["requirement_id"] for i in items if not i["executed"]],
        "unmapped_cases": unmapped,
        "not_run": not_run,
        "partial": partial,
        "note": "" if table_found else "未找到本运行的用例表，需求覆盖只能依据 manifest 中登记的 meta.requirement_ids。",
    }


def _quality_gate(paths: Paths, run_id: str) -> dict[str, Any]:
    gate_path = paths.project_root / "qualification" / "gate-runs" / run_id / "gate-report.json"
    if not gate_path.is_file():
        return {
            "found": False,
            "path": None,
            "message": "本次未运行质量门禁",
            "searched": paths.rel(gate_path),
            "delivery_verdict": None,
            "test_verdict": None,
            "gate_status": {},
            "fail_findings": [],
        }
    try:
        data = rs.json_load(gate_path)
    except Exception as exc:
        return {"found": True, "path": paths.rel(gate_path), "error": f"{type(exc).__name__}: {exc}",
                "message": "质量门禁报告无法解析", "gate_status": {}, "fail_findings": []}
    findings = data.get("findings") or []
    fail_findings = [
        {"gate": f.get("gate"), "code": f.get("code"), "severity": f.get("severity"),
         "subject": f.get("subject"), "message": f.get("message"), "evidence": f.get("evidence")}
        for f in findings if str(f.get("severity") or "").upper() in {"FAIL", "BLOCKED"}
    ]
    return {
        "found": True,
        "path": paths.rel(gate_path),
        "generated_at": data.get("generated_at"),
        "delivery_verdict": data.get("delivery_verdict"),
        "test_verdict": data.get("test_verdict"),
        "gate_status": data.get("gate_status") or {},
        "summary": data.get("summary") or {},
        "finding_total": len(findings),
        "fail_findings": fail_findings,
        "message": "",
    }


# --------------------------------------------------------------------------- #
# gate
# --------------------------------------------------------------------------- #
def _finding(code: str, severity: str, subject: str, message: str, evidence: str = "") -> dict[str, str]:
    return {"code": code, "severity": severity, "subject": subject,
            "message": message, "evidence": evidence}


def evaluate_gate(report: dict[str, Any], require_cases: int | None = None,
                  enabled: bool = True) -> dict[str, Any]:
    if not enabled:
        return {"enabled": False, "verdict": "DISABLED", "exit_code": 0,
                "findings": [], "counts": {}, "require_cases": require_cases}
    findings: list[dict[str, str]] = []
    run = report["run"]
    cases = report["cases"]
    junit = report.get("junit")
    if str(run.get("status")) in {"blocked", "aborted"}:
        findings.append(_finding("RUN_NOT_EXECUTED", "BLOCKED", run["run_id"],
                                 f"运行状态为 {run.get('status')}，不能作为交付证据"))
    if not cases:
        findings.append(_finding("NO_CASES", "BLOCKED", run["run_id"],
                                 "manifest 未登记任何用例，报告没有可复核的结论"))
    executed = [c for c in cases if c["status"] in {"passed", "failed", "xfailed"}]
    if cases and not executed:
        findings.append(_finding("NO_EXECUTED_CASES", "FAIL", run["run_id"],
                                 f"{len(cases)} 条用例全部未执行/阻塞，不能声明测试通过"))
    if not junit:
        findings.append(_finding("JUNIT_MISSING", "FAIL", run["run_id"],
                                 "未找到 junit-summary.json，执行结果不可复核"))
    else:
        junit_xml = junit.get("junit")
        if junit_xml:
            p = Path(str(junit_xml))
            if not p.is_absolute():
                p = report["_project_root"] / p
            if not p.is_file():
                findings.append(_finding("JUNIT_XML_MISSING", "FAIL", run["run_id"],
                                         f"junit.xml 不存在：{junit_xml}"))
    for case in cases:
        if case["expected_source"] == "missing":
            findings.append(_finding("CASE_EXPECTED_MISSING", "FAIL", case["case_id"],
                                     "用例级预期缺失，且没有断言明细可回溯"))
        elif case["expected_source"] == "assertions":
            findings.append(_finding("CASE_EXPECTED_FROM_ASSERTIONS", "WARNING", case["case_id"],
                                     "用例级预期缺失或为历史断言取值，报告已回退到断言明细",
                                     case["expected_note"]))
        if case["status"] == "passed" and case["evidence_count"] == 0:
            findings.append(_finding("PASSED_CASE_WITHOUT_EVIDENCE", "WARNING", case["case_id"],
                                     "通过用例没有登记任何证据"))
        if report["case_table"]["found"] and not case["in_case_table"]:
            findings.append(_finding("CASE_NOT_IN_CASE_TABLE", "WARNING", case["case_id"],
                                     "用例不在本运行的用例表中，需求/方法字段只能来自 manifest"))
    verify = report["evidence"]
    if verify["missing"]:
        findings.append(_finding("MANIFEST_EVIDENCE_MISSING", "FAIL", run["run_id"],
                                 f"{len(verify['missing'])} 个证据文件缺失",
                                 "; ".join(verify["missing"])))
    if verify["mismatched"]:
        findings.append(_finding("MANIFEST_HASH_MISMATCH", "FAIL", run["run_id"],
                                 f"{len(verify['mismatched'])} 个证据哈希与 manifest 不一致",
                                 "; ".join(verify["mismatched"])))
    if verify["cross_run"]:
        findings.append(_finding("EVIDENCE_CROSS_RUN", "WARNING", run["run_id"],
                                 f"{len(verify['cross_run'])} 个证据路径引用了其他 run",
                                 "; ".join(verify["cross_run"])))
    if verify["unscoped"]:
        findings.append(_finding("EVIDENCE_UNSCOPED", "WARNING", run["run_id"],
                                 f"{len(verify['unscoped'])} 个证据路径不含 run id",
                                 "; ".join(verify["unscoped"])))
    if not report["case_table"]["found"]:
        findings.append(_finding("CASE_TABLE_MISSING", "WARNING", run["run_id"],
                                 report["case_table"]["reason"]))
    if require_cases is not None and len(cases) < require_cases:
        findings.append(_finding("REQUIRE_CASES_SHORTFALL", "FAIL", run["run_id"],
                                 f"用例数 {len(cases)} 少于要求的 {require_cases}"))
    if not report["quality_gate"]["found"]:
        findings.append(_finding("QUALITY_GATE_NOT_RUN", "WARNING", run["run_id"],
                                 "未找到质量门禁报告，交付结论只依赖本报告的门禁"))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    if counts.get("BLOCKED"):
        verdict = "BLOCKED"
    elif counts.get("FAIL"):
        verdict = "FAIL"
    elif counts.get("WARNING"):
        verdict = "WARNING"
    else:
        verdict = "PASS"
    return {
        "enabled": True,
        "verdict": verdict,
        "exit_code": GATE_EXIT_CODES[verdict],
        "findings": findings,
        "counts": counts,
        "require_cases": require_cases,
        "fail_findings": [f for f in findings if f["severity"] == "FAIL"],
        "blocked_findings": [f for f in findings if f["severity"] == "BLOCKED"],
        "warning_findings": [f for f in findings if f["severity"] == "WARNING"],
    }


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
def build(run_id: str, out_dir: Path, title: str, *, paths: Paths | None = None,
          cases_path: Path | None = None, require_cases: int | None = None,
          gate_enabled: bool = True, probe_env: bool = True,
          junit_summary: Path | None = None) -> dict[str, Any]:
    paths = paths or default_paths()
    data = _load_manifest(paths.manifest_path)
    if run_id not in data.get("runs", {}):
        raise KeyError(f"run not found: {run_id}")
    run = data["runs"][run_id]

    if cases_path is not None:
        rows = rs.read_case_csv(cases_path)
        case_table = {
            "found": bool(rows),
            "path": str(cases_path),
            "rows": rows,
            "reason": "" if rows else f"指定的用例表为空：{cases_path}",
            "inspected": [],
            "source": "explicit",
        }
    else:
        case_table = {**rs.find_run_case_table(run_id, paths.reports_root), "source": "run-scoped"}
    table_rows = case_table["rows"]

    summary = _run_summary(run, run_id, data)
    verify = _verify_evidence(data, run_id, paths.project_root)
    junit = _load_junit(out_dir, junit_summary)
    cases, defects = _build_cases(data, run, table_rows, junit)
    junit_names = {c.get("name") for c in (junit or {}).get("cases", []) if c.get("name")}

    probe = rs.probe_environment(paths.project_root, str(run.get("target") or "")) if probe_env else None
    if probe:
        probe["probed_at"] = _now_iso()
    environment, environment_meta = _build_environment(run, probe)

    status_counts: dict[str, int] = {}
    for case in cases:
        status_counts[case["status"]] = status_counts.get(case["status"], 0) + 1
    executed = status_counts.get("passed", 0) + status_counts.get("failed", 0)
    pass_rate = round(status_counts.get("passed", 0) / executed, 4) if executed else None

    table_found = bool(table_rows)
    design_doc = _design_doc(paths, run_id)
    report: dict[str, Any] = {
        "schema_version": rs.REPORT_SCHEMA_VERSION,
        "generator": {"tool": "tools/generate_report.py", "version": GENERATOR_VERSION,
                      "generated_at": _now_iso()},
        "generated_at": _now_iso(),
        "title": title,
        "run": {
            **summary,
            "environment": run.get("environment", {}),
            "notes": run.get("notes", []),
        },
        "scope": {
            "target": run.get("target", ""),
            "scope": run.get("scope") or "未声明",
            "scope_source": "run.scope" if run.get("scope") else "missing",
            "requirement_source": _requirement_source(table_found, design_doc, cases_path),
            "case_table": str(case_table["path"]) if case_table["path"] else None,
            "design_doc": paths.rel(design_doc) if design_doc else None,
            "product": run.get("label") or "",
        },
        "environment": environment,
        "environment_meta": environment_meta,
        "environment_probe": probe,
        "case_table": {
            "found": table_found,
            "path": paths.rel(Path(case_table["path"])) if case_table["path"] else None,
            "reason": case_table["reason"],
            "row_count": len(table_rows),
            "source": case_table["source"],
            "inspected": [{"path": paths.rel(Path(i["path"])), "rows": i["rows"],
                           "run_tokens": i["run_tokens"]} for i in case_table.get("inspected", [])],
        },
        "strategy": _build_strategy(cases, table_found),
        "summary": {
            "case_total": len(cases),
            "status_counts": status_counts,
            "executed": executed,
            "passed": status_counts.get("passed", 0),
            "failed": status_counts.get("failed", 0),
            "xfailed": status_counts.get("xfailed", 0),
            "skipped": status_counts.get("skipped", 0),
            "not_run": status_counts.get("not-run", 0),
            "blocked": status_counts.get("blocked", 0),
            "pass_rate": pass_rate,
            "pass_rate_note": "通过率 = passed / (passed + failed)；xfailed、skipped、not-run 不计入分母",
        },
        "cases": cases,
        "defects": defects,
        "coverage": _build_coverage(cases, table_rows, table_found, run_id),
        "visual": _visual_metrics(paths, run_id),
        "evidence": verify,
        "junit": junit,
        "junit_summary_path": str(junit_summary) if junit_summary else str(out_dir / "junit-summary.json"),
        "junit_counts": _junit_counts(junit),
        "test_functions": {
            "junit_backed_cases": [c["case_id"] for c in cases if c["junit"] is not None],
            "non_junit_cases": [c["case_id"] for c in cases if c["junit"] is None],
            "junit_names": sorted(n for n in junit_names if n),
        },
        # compatibility aliases for consumers of the 1.x report schema
        "junit_backed_cases": [c["case_id"] for c in cases if c["junit"] is not None],
        "non_junit_cases": [c["case_id"] for c in cases if c["junit"] is None],
        "test_case_design": str(design_doc) if design_doc else None,
        "quality_gate": _quality_gate(paths, run_id),
        "artifacts": {
            "markdown": str(out_dir / "report.md"),
            "html": str(out_dir / "report.html"),
            "json": str(out_dir / "report.json"),
            "out_dir": str(out_dir),
        },
        "_project_root": paths.project_root,
        "_paths": paths,
    }
    report["limitations"] = _build_limitations(report)
    report["gate"] = evaluate_gate(report, require_cases, gate_enabled)
    report["exit_code"] = report["gate"]["exit_code"]
    return report


def _requirement_source(table_found: bool, design_doc: Path | None, cases_path: Path | None) -> str:
    if cases_path is not None:
        return "显式指定的用例表（--cases）"
    if table_found:
        return "本运行用例表的 requirement_ids 列"
    if design_doc:
        return "用例设计文档（未纳入机器聚合）"
    return "未找到本运行的用例表"


def _build_limitations(report: dict[str, Any]) -> list[str]:
    items: list[str] = []
    missing_env = [k for k, v in report["environment"].items() if str(v).startswith(MISSING)]
    if missing_env:
        items.append("运行环境缺少字段：" + "、".join(missing_env)
                     + "（报告显示为「未采集」，未用报告生成时的探测值冒充运行环境）")
    if not report["case_table"]["found"]:
        items.append(report["case_table"]["reason"] + "，设计方法与需求覆盖无法按用例表聚合。")
    if not report["quality_gate"]["found"]:
        items.append("本次未运行质量门禁（qualification/gate-runs/<run>/gate-report.json 不存在）。")
    sanitized = [c["case_id"] for c in report["cases"] if c["expected_invalid"]]
    if sanitized:
        items.append("以下用例的运行记录把断言取值写进了用例级预期，报告已剔除并回退到断言明细："
                     + "、".join(sanitized))
    if report["summary"]["xfailed"]:
        items.append(f"{report['summary']['xfailed']} 条 xfailed 用例只用于验证失败取证链路，"
                     "不计入通过率，也不等同于产品缺陷。")
    if report["summary"]["not_run"] or report["summary"]["skipped"]:
        items.append("未执行/跳过的用例不会标记为通过，见第 11 节。")
    if report["visual"]:
        items.append("视觉差异只作为复核信号，不单独据此判定产品缺陷。")
    items.append("比赛前需确认当届赛项对 AI 辅助工具的合规要求。")
    return items


# --------------------------------------------------------------------------- #
# markdown
# --------------------------------------------------------------------------- #
def _env_rows(report: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    rows = []
    meta = report["environment_meta"]
    for key, value in report["environment"].items():
        if key == "__probe__":
            continue
        info = meta.get(key, {})
        rows.append((info.get("label", key), str(value), _env_source_label(info), info.get("raw", "")))
    return rows


def _env_source_label(info: dict[str, Any]) -> str:
    source = info.get("source")
    return {
        "run": "运行记录",
        "run(platform)": "运行记录（platform 字段）",
        "run-placeholder": "运行记录为占位符",
        "missing": "未采集",
    }.get(str(source), str(source or MISSING))


def render_markdown(report: dict[str, Any], out_dir: Path, title: str) -> str:
    run = report["run"]
    summary = report["summary"]
    lines: list[str] = []
    push = lines.append
    push(f"# {title}")
    push("")
    push(f"- 生成时间：{report['generated_at']}")
    push(f"- 运行 ID：`{run['run_id']}`")
    push(f"- 目标：{_mdd(run.get('target'))}")
    push(f"- 状态：**{_status_label(run.get('status', ''))}**")
    push(f"- 阶段：{_mdd(run.get('stage'), '未登记')}")
    push(f"- 执行窗口：{_mdd(run.get('started_at'))} → {_mdd(run.get('finished_at'))}")
    push(f"- 交付门禁：**{report['gate']['verdict']}**（exit {report['gate']['exit_code']}）")
    push("")

    # 1
    scope = report["scope"]
    push("## 1. 测试目标与范围")
    push("")
    push("| 项目 | 内容 |")
    push("|---|---|")
    push(f"| 目标 URL | {_mdd(scope['target'])} |")
    push(f"| 测试范围 | {_mdd(scope['scope'])}（来源：{_mdd(scope['scope_source'])}） |")
    push(f"| 需求来源 | {_mdd(scope['requirement_source'])} |")
    push(f"| 用例表 | {('`' + scope['case_table'] + '`') if scope['case_table'] else MISSING} |")
    push(f"| 用例设计文档 | {('`' + scope['design_doc'] + '`') if scope['design_doc'] else MISSING} |")
    push(f"| 用例数 | {summary['case_total']} |")
    push(f"| 通过率 | {_pass_rate_text(summary)} |")
    push("")
    push(f"本报告只陈述运行 `{run['run_id']}` 在 `evidence/manifest.json` 中登记、"
         "且能在 JUnit 与证据文件中追溯的结果。未执行、被跳过、受控预期失败的结果单独统计，"
         "不并入通过率。")
    push("")

    # 2
    push("## 2. 测试环境")
    push("")
    push("| 项目 | 值 | 来源 | 运行记录原值 |")
    push("|---|---|---|---|")
    for label, value, source, raw in _env_rows(report):
        push(f"| {_md_escape(label)} | {_md_escape(value)} | {_md_escape(source)} | "
             f"{_md_escape(raw) if raw else '—'} |")
    push("")
    notes = run.get("notes", [])
    if notes:
        push("### 运行备注")
        push("")
        for n in notes:
            push(f"- {n.get('at', '')}：{n.get('note', '')}")
        push("")
    probe = report.get("environment_probe")
    push("### 环境补充探测")
    push("")
    if not probe:
        push("本次未执行环境探测（`--no-env-probe`）。")
    else:
        push(f"> {probe.get('note', '')}（探测时间 {probe.get('probed_at')}）。"
             "这些值不覆盖上表的运行记录。")
        push("")
        push("| 项目 | 探测值 |")
        push("|---|---|")
        for key in ("python", "platform", "os", "pytest", "selenium", "chrome", "chrome_path",
                    "chromedriver", "node", "openpyxl", "pillow"):
            if key in probe:
                push(f"| {_md_escape(key)} | {_md_escape(probe[key])} |")
    push("")
    push("| 项目 | 值 |")
    push("|---|---|")
    push("| 证据清单 | `evidence/manifest.json` |")
    push(f"| 证据校验 | 登记 {report['evidence']['checked']} / 通过 {report['evidence']['ok']} |")
    push("")

    # 3
    strategy = report["strategy"]
    push("## 3. 测试策略与设计方法")
    push("")
    push("设计方法分布按用例表 `method` 列聚合（无法聚合时明确标注，不做推测）：")
    push("")
    if strategy["methods"]:
        push("| 设计方法 | 用例数 | 用例 |")
        push("|---|---:|---|")
        for item in strategy["methods"]:
            push(f"| {_md_escape(item['method'])} | {item['count']} | "
                 f"{_md_escape('、'.join(item['case_ids']))} |")
    else:
        push(f"- {strategy['note'] or '没有可聚合的 method 取值。'}")
    push("")
    if strategy["case_types"]:
        push("| 用例类型 | 用例数 |")
        push("|---|---:|")
        for item in strategy["case_types"]:
            push(f"| {_md_escape(item['case_type'])} | {item['count']} |")
        push("")
    if strategy["priorities"]:
        push("| 优先级 | 用例数 |")
        push("|---|---:|")
        for item in strategy["priorities"]:
            push(f"| {_md_escape(item['priority'])} | {item['count']} |")
        push("")
    if strategy["missing_method_cases"]:
        push(f"- method 未登记：{_md_escape('、'.join(strategy['missing_method_cases']))}")
        push("")
    push("执行策略：")
    push("")
    push("- 浏览器探索优先使用 DOM/无障碍快照，截图只用于视觉证据。")
    push("- 功能用例使用 Selenium + pytest + 显式等待，断言直接绑定可观察状态。")
    push("- 失败与受控预期失败自动保存视口/整页截图、页面源码和浏览器日志。")
    push("- 视觉差异只作为复核信号，不单独据此判定产品缺陷。")
    push("")

    # 4
    push("## 4. 用例与执行结果")
    push("")
    jc = report.get("junit_counts") or {}
    push(f"计数口径：manifest 登记用例 {summary['case_total']} 条"
         f"（通过 {summary['passed']}、受控预期失败 {summary['xfailed']}、失败 {summary['failed']}、"
         f"未执行 {summary['not_run']}、跳过 {summary['skipped']}、阻塞 {summary['blocked']}）；"
         f"JUnit：tests={jc.get('total')}、passed={jc.get('passed')}、failed={jc.get('failed')}、"
         f"xfailed={jc.get('xfailed')}。xfailed 不计入通过率（{_pass_rate_text(summary)}）。")
    push("")
    push("| 用例 ID | 标题 | 类型 | 优先级 | 方法与需求 | 状态 | 证据数 | 日志 |")
    push("|---|---|---|---|---|---|---:|---|")
    for c in report["cases"]:
        method_req = " / ".join(x for x in (
            c["method"] or "方法未登记",
            "、".join(c["requirement_ids"]) if c["requirement_ids"] else "需求未登记") if x)
        log = f"`{c['log_path']}`" if c.get("log_path") else "未登记"
        push(f"| {c['case_id']} | {_md_escape(c['title'])} | {_md_escape(c['case_type'] or '未登记')} | "
             f"{_md_escape(c['priority'] or '未登记')} | {_md_escape(method_req)} | "
             f"{_status_label(c['status'])} | {c['evidence_count']} | {log} |")
    if not report["cases"]:
        push(f"| {MISSING} | manifest 未登记任何用例 | — | — | — | — | 0 | — |")
    push("")

    # 5
    push("## 5. 用例明细")
    push("")
    for c in report["cases"]:
        push(f"### {c['case_id']} {c['title']}")
        push("")
        push("| 字段 | 值 |")
        push("|---|---|")
        push(f"| 状态 | **{_status_label(c['status'])}** |")
        push(f"| 用例类型 | {_mdd(c['case_type'], '未登记')} |")
        push(f"| 优先级 | {_mdd(c['priority'], '未登记')} |")
        push(f"| 设计方法 | {_mdd(c['method'], '未登记')} |")
        push(f"| 需求 | {_mdd('、'.join(c['requirement_ids']), '未登记')} |")
        push(f"| 自动化 | {_md_escape(c['automation']) if c['automation'] else '未登记（手工或未实现）'} |")
        if c.get("duration_ms") is not None:
            push(f"| 耗时 | {c['duration_ms']} ms |")
        push(f"| 执行日志 | {('`' + c['log_path'] + '`') if c.get('log_path') else '未登记'}"
             f"{'' if c['log_exists'] else '（文件缺失）'} |")
        push("")
        push("**前置条件**")
        if c["preconditions"]:
            for i, item in enumerate(c["preconditions"], 1):
                push(f"{i}. {item}")
        else:
            push("未登记")
        push("")
        push("**测试数据**")
        push("")
        push(c["test_data"] or "未登记")
        push("")
        push("**步骤**")
        if c["steps"]:
            for i, step in enumerate(c["steps"], 1):
                push(f"{i}. {step}")
        else:
            push("未登记")
        push("")
        push("**用例级预期**")
        push("")
        push(_expected_text(c))
        push("")
        if c["expected_note"]:
            push(f"> {c['expected_note']}"
                 + (f"（运行记录原值：`{c['expected_raw']}`）" if c["expected_raw"] else ""))
            push("")
        push("**用例级实际**")
        push("")
        push(_actual_text(c))
        push("")
        if c["assertions"]:
            push(f"**断言（{c['assertion_count']} 条，通过 {c['assertions_passed']}）**")
            push("")
            push("| # | 断言 | 预期 | 实际 | 结果 |")
            push("|---:|---|---|---|---|")
            for i, a in enumerate(c["assertions"], 1):
                push(f"| {i} | {_md_escape(a.get('name', ''))} | {_md_escape(a.get('expected', ''))} | "
                     f"{_md_escape(a.get('actual', ''))} | {'通过' if a.get('passed') else '失败'} |")
            push("")
        else:
            push("**断言**")
            push("")
            push("未登记断言。")
            push("")
        push(f"**证据（{c['evidence_count']}）**")
        push("")
        if c["evidence"]:
            for ev in c["evidence"]:
                p = Path(report["_project_root"]) / ev["path"]
                rel = rs.rel_posix(p, out_dir)
                dim = f" {ev.get('width')}x{ev.get('height')}" if ev.get("width") else ""
                push(f"- `{ev['evidence_id']}` [{ev['kind']}]{dim} `{ev['path']}`")
                if ev["kind"] in IMAGE_KINDS:
                    push("")
                    push(f"  ![{_md_escape(ev.get('caption') or 'evidence')}]({rel})")
                    push("")
        else:
            push("> 证据完整性警告：该用例没有登记任何证据文件。")
            push("")
        if c["defects"]:
            push("**缺陷**")
            push("")
            for d in c["defects"]:
                flag = "（疑似/待复核，未确认为产品缺陷）" if d["unconfirmed"] else ""
                push(f"- `{d['defect_id']}` [{d['severity_label'] or d['severity']}] {d['title']}{flag}")
            push("")

    # 6
    push("## 6. 缺陷")
    push("")
    defects = report["defects"]
    if not defects:
        push("本轮未登记产品缺陷。若存在 `xfailed` 用例，它只用于验证失败取证链路，不等同于产品缺陷。")
        push("")
    else:
        unconfirmed = [d for d in defects if d["unconfirmed"]]
        if unconfirmed:
            push("> **疑似/待复核，未确认为产品缺陷**："
                 + "、".join(f"{d['defect_id']}（{d['status']}）" for d in unconfirmed)
                 + "。这些记录不得作为缺陷结论引用。")
            push("")
        push("| 缺陷 ID | 标题 | 严重度 | 严重度依据 | 分类 | 状态 | 复现状态 | 复现次数 | 环境 |")
        push("|---|---|---|---|---|---|---|---:|---|")
        for d in defects:
            push(f"| {d['defect_id']} | {_md_escape(d['title'])} | "
                 f"{_md_escape(d['severity_label'] + '（' + d['severity'] + '）')} | "
                 f"{_mdd(d.get('severity_rationale'), '未登记')} | "
                 f"{_md_escape((d['category_label'] + '（' + d['category'] + '）') if d.get('category') else '未登记')} | "
                 f"{_md_escape(d['status_label'] + '（' + d['status'] + '）')} | "
                 f"{_mdd(d.get('repro_label'), '未登记')} | {_mdd(d.get('repro_count'), '未登记')} | "
                 f"{_mdd(d.get('environment'), '未登记')} |")
        push("")
        for d in defects:
            push(f"### {d['defect_id']} {d['title']}")
            push("")
            if d["unconfirmed"]:
                push("> **疑似/待复核，未确认为产品缺陷**（status="
                     f"`{d['status']}`）。在复核完成前不得作为产品缺陷结论。")
                push("")
            push(f"- 严重度：{d['severity_label'] or '未登记'}（`{d.get('severity')}`）")
            push(f"- 严重度依据：{_mdd(d.get('severity_rationale'), '未登记')}")
            push(f"- 分类：{_mdd((d['category_label'] + ' / ' + d['category']) if d.get('category') else '', '未登记')}")
            push(f"- 状态：{d['status_label']}（`{d.get('status')}`）")
            push(f"- 复现状态：{_mdd(d.get('repro_label'), '未登记')}；复现次数：{_mdd(d.get('repro_count'), '未登记')}")
            push(f"- 复现环境：{_mdd(d.get('environment'), '未登记')}")
            push(f"- 描述：{_mdd(d.get('description'), '未登记')}")
            push(f"- 预期：{_mdd(d.get('expected'), '未登记')}")
            push(f"- 实际：{_mdd(d.get('actual'), '未登记')}")
            push("")
            push("**前置条件**")
            push("")
            if d.get("preconditions"):
                for i, item in enumerate(d["preconditions"], 1):
                    push(f"{i}. {item}")
            else:
                push("未登记")
            push("")
            push("**复现步骤**")
            push("")
            if d.get("repro_steps"):
                for i, step in enumerate(d["repro_steps"], 1):
                    push(f"{i}. {step}")
            else:
                push("未登记（缺陷缺少可复现步骤）")
            push("")
            push("**证据**")
            push("")
            if d["evidence_ids"]:
                for eid, path in zip(d["evidence_ids"], d["evidence_paths"] + [MISSING] * max(
                        0, len(d["evidence_ids"]) - len(d["evidence_paths"]))):
                    push(f"- `{eid}` → `{path}`")
            else:
                push("未登记证据。")
            push("")

    # 7
    if report["visual"]:
        push("## 7. 视觉差异")
        push("")
        for m in report["visual"]:
            push(f"### {m.get('label', 'visual-check')}")
            push("")
            push(f"- 基准图：`{m.get('baseline')}`")
            push(f"- 实际图：`{m.get('actual')}`")
            push(f"- 判定：`{_verdict_label(m.get('verdict'))}`，差异像素 {m.get('changed_pixels')} / "
                 f"{m.get('total_pixels')}（{m.get('diff_ratio')}）")
            push(f"- 差异区域数：{m.get('region_count')}；PSNR：{m.get('psnr')}")
            push(f"- 指标文件：`{m.get('_metrics_path')}`")
            push(f"- 说明：{m.get('defect_note', '')}")
            if m.get("regions"):
                push("")
                push("| 区域 | x | y | w | h | 面积 | 平均差 |")
                push("|---|---:|---:|---:|---:|---:|---:|")
                for r in m["regions"]:
                    push(f"| {r.get('region_id')} | {r['x']} | {r['y']} | {r['w']} | {r['h']} | "
                         f"{r['area']} | {r.get('mean_abs_diff')} |")
            for name in ("annotated.png", "comparison.png", "heatmap.png"):
                p = Path(report["_project_root"]) / m["_dir"] / name
                if p.exists():
                    push("")
                    push(f"![{name}]({rs.rel_posix(p, out_dir)})")
            push("")
    else:
        push("## 7. 视觉差异")
        push("")
        push("本轮未生成差异图；有效截图证据见第 5 节。")
        push("")

    # 8
    v = report["evidence"]
    push("## 8. 证据完整性")
    push("")
    push("| 指标 | 数量 |")
    push("|---|---:|")
    push(f"| checked（登记） | {v['checked']} |")
    push(f"| ok（校验通过） | {v['ok']} |")
    push(f"| missing（文件缺失） | {len(v['missing'])} |")
    push(f"| mismatched（哈希不一致） | {len(v['mismatched'])} |")
    push(f"| cross_run（跨 run 引用） | {len(v['cross_run'])} |")
    push(f"| unscoped（路径无 run id） | {len(v['unscoped'])} |")
    push(f"| duplicates（重复登记） | {len(v['duplicates'])} |")
    push("")
    if v["missing"]:
        push(f"- 缺失：{', '.join(v['missing'])}")
    if v["mismatched"]:
        push(f"- 不一致：{', '.join(v['mismatched'])}")
    if v["cross_run"]:
        push(f"- 跨 run：{', '.join(v['cross_run'])}")
    if v["unscoped"]:
        push(f"- 无 run id：{', '.join(v['unscoped'])}")
    if v["duplicates"]:
        push(f"- 重复：{', '.join(v['duplicates'])}")
    without = [c["case_id"] for c in report["cases"] if not c["evidence_complete"]]
    if without:
        push(f"- 无用例级证据：{', '.join(without)}")
    push("")

    # 9
    push("## 9. 执行日志")
    push("")
    junit = report.get("junit")
    if junit:
        push(f"- JUnit 汇总：`{junit.get('junit')}`")
        push(f"- 控制台日志：`{junit.get('console_log')}`")
        push(f"- 统计：tests={junit.get('tests')} failures={junit.get('failures')} "
             f"errors={junit.get('errors')} skipped={junit.get('skipped')} xfailed={junit.get('xfailed')} "
             f"elapsed={junit.get('elapsed_seconds')}s exit={junit.get('exit_code')}")
        push("")
        if junit.get("cases"):
            push("| 测试函数 | 类 | 耗时(s) | 状态 | 信息 |")
            push("|---|---|---:|---|---|")
            for item in junit["cases"]:
                push(f"| {_md_escape(item.get('name', ''))} | {_md_escape(item.get('classname', ''))} | "
                     f"{item.get('time')} | {_md_escape(item.get('status', ''))} | "
                     f"{_md_escape(item.get('message', ''))} |")
            push("")
    else:
        push("- 未找到 JUnit 汇总文件，本次执行结果不可复核。")
        push("")
    push(f"- 用例日志目录：`evidence/logs/{run['run_id']}/`")
    for case in report["cases"]:
        if case.get("log_path"):
            push(f"  - {case['case_id']}：`{case['log_path']}`"
                 f"{'' if case['log_exists'] else '（文件缺失）'}")
    push("")

    # 10
    cov = report["coverage"]
    push("## 10. 需求覆盖情况")
    push("")
    if cov["requirements"]:
        push("| 需求 | 关联用例 | 已执行用例 | 状态分布 | 是否执行 |")
        push("|---|---|---|---|---|")
        for item in cov["requirements"]:
            dist = "、".join(f"{_status_label(k)} {n}" for k, n in sorted(item["status_counts"].items()))
            push(f"| {_md_escape(item['requirement_id'])} | {_md_escape('、'.join(item['case_ids']))} | "
                 f"{_md_escape('、'.join(item['executed_case_ids']) or '无')} | {_md_escape(dist)} | "
                 f"{'是' if item['executed'] else '否'} |")
        push("")
        if cov["requirements_without_execution"]:
            push(f"- 有用例但本轮未执行的需求：{_md_escape('、'.join(cov['requirements_without_execution']))}")
        else:
            push("- 所有登记需求在本轮都有执行记录。")
        if cov["unmapped_cases"]:
            push(f"- 未关联任何需求的用例：{_md_escape('、'.join(cov['unmapped_cases']))}")
        push("")
    else:
        push(cov["note"] or "没有可聚合的需求信息。")
        push("")

    # 11
    push("## 11. 未执行项与已知限制")
    push("")
    if cov["not_run"]:
        push("**未执行（设计完成但本轮未执行，不计入通过率）**")
        push("")
        for item in cov["not_run"]:
            push(f"- {item['case_id']} {item['title']}（{item['design_status'] or '状态未登记'}）")
        push("")
    if cov["partial"]:
        push("**部分覆盖**")
        push("")
        for item in cov["partial"]:
            push(f"- {item['case_id']} {item['title']}（{item['design_status']}）")
        push("")
    not_run_cases = [c for c in report["cases"] if c["status"] in {"not-run", "skipped", "blocked"}]
    if not_run_cases:
        push("**manifest 中未产生结果的用例**")
        push("")
        for c in not_run_cases:
            push(f"- {c['case_id']} {c['title']}：{_status_label(c['status'])}")
        push("")
    if not cov["not_run"] and not cov["partial"] and not not_run_cases:
        push("本轮没有登记未执行项。")
        push("")
    push("**已知限制**")
    push("")
    for item in report["limitations"]:
        push(f"- {item}")
    push("")

    # 12
    qg = report["quality_gate"]
    push("## 12. 质量门禁结果")
    push("")
    if not qg["found"]:
        push("本次未运行质量门禁（未找到 `qualification/gate-runs/"
             f"{run['run_id']}/gate-report.json`）。")
        push("")
    elif qg.get("error"):
        push(f"质量门禁报告无法解析：{qg['error']}")
        push("")
    else:
        push(f"- 门禁报告：`{qg['path']}`（生成于 {_mdd(qg.get('generated_at'))}）")
        push(f"- delivery_verdict：**{_mdd(qg.get('delivery_verdict'))}**")
        push(f"- test_verdict：**{_mdd(qg.get('test_verdict'))}**")
        push("")
        if qg["gate_status"]:
            push("| Gate | 状态 |")
            push("|---|---|")
            for gate, status in sorted(qg["gate_status"].items()):
                push(f"| {gate} | {status} |")
            push("")
        if qg.get("fail_findings"):
            push(f"**FAIL/BLOCKED findings（{len(qg['fail_findings'])}）**")
            push("")
            push("| Gate | 代码 | 级别 | 对象 | 说明 |")
            push("|---|---|---|---|---|")
            for f in qg["fail_findings"]:
                push(f"| {f.get('gate')} | {f.get('code')} | {f.get('severity')} | "
                     f"{_md_escape(f.get('subject') or '')} | {_md_escape(f.get('message') or '')} |")
            push("")
        else:
            push("质量门禁未报告 FAIL/BLOCKED findings。")
            push("")
    push("**报告交付门禁**")
    push("")
    push(f"- 结论：**{report['gate']['verdict']}**（退出码 {report['gate']['exit_code']}）")
    gate_counts = report["gate"].get("counts") or {}
    if gate_counts:
        push("- 分布：" + "、".join(f"{k} {v}" for k, v in sorted(gate_counts.items())))
    push("")
    if report["gate"]["findings"]:
        push("| 代码 | 级别 | 对象 | 说明 |")
        push("|---|---|---|---|")
        for f in report["gate"]["findings"]:
            push(f"| {f['code']} | {f['severity']} | {_md_escape(f['subject'])} | "
                 f"{_md_escape(f['message'])} |")
        push("")

    push("## 附录")
    push("")
    push(f"- 报告生成器：`tools/generate_report.py` v{GENERATOR_VERSION}")
    push(f"- 报告 schema：`{report['schema_version']}`")
    push(f"- 用例表来源：{('`' + report['case_table']['path'] + '`') if report['case_table']['path'] else MISSING}")
    if not report["case_table"]["found"]:
        push(f"- 用例表查找说明：{report['case_table']['reason']}")
        if report["case_table"]["inspected"]:
            push("- 已检查的用例表：")
            for item in report["case_table"]["inspected"]:
                tokens = "、".join(item["run_tokens"]) or "无 executed_in_run"
                push(f"  - `{item['path']}`（{item['rows']} 行；run 标记：{tokens}）")
    push("")
    return "\n".join(lines) + "\n"


def _pass_rate_text(summary: dict[str, Any]) -> str:
    rate = summary.get("pass_rate")
    if rate is None:
        return "不适用（没有已判定用例）"
    return f"{rate * 100:.1f}%（{summary['passed']}/{summary['executed']}）"


def _expected_text(case: dict[str, Any]) -> str:
    if case["expected"]:
        return case["expected"]
    if case["assertion_count"]:
        return f"见断言明细（{case['assertion_count']} 条断言）"
    return "未登记用例级预期，且没有断言明细"


def _actual_text(case: dict[str, Any]) -> str:
    if case["actual"]:
        return case["actual"]
    if case["assertion_count"]:
        return f"见断言明细（{case['assertion_count']} 条断言）"
    return "未登记"


# --------------------------------------------------------------------------- #
# html
# --------------------------------------------------------------------------- #
def render_html(report: dict[str, Any], out_dir: Path, title: str) -> str:
    e = html.escape
    run = report["run"]
    summary = report["summary"]

    def img(item: dict[str, Any]) -> str:
        rel = rs.rel_posix(ROOT / item["path"], out_dir)
        cap = e(item.get("caption") or item["kind"])
        return (f"<figure><a href=\"{e(rel)}\"><img src=\"{e(rel)}\" alt=\"{cap}\" loading=\"lazy\"></a>"
                f"<figcaption>{cap}<br><code>{e(item['path'])}</code></figcaption></figure>")

    def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
        head = "".join(f"<th>{e(h)}</th>" for h in headers)
        body = "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in row) + "</tr>" for row in rows)
        return f"<table class='{cls}'><tr>{head}</tr>{body}</table>"

    parts: list[str] = [
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
        f"<title>{e(title)}</title>",
        "<style>body{font-family:'Segoe UI','Microsoft YaHei',sans-serif;margin:32px;max-width:1200px;color:#1f2328}"
        "h1{border-bottom:2px solid #d0d7de;padding-bottom:8px}h2{margin-top:36px;border-bottom:1px solid #d0d7de;padding-bottom:4px}"
        "h3{margin-top:24px}table{border-collapse:collapse;width:100%;margin:12px 0}"
        "th,td{border:1px solid #d0d7de;padding:6px 8px;text-align:left;vertical-align:top}"
        "th{background:#f6f8fa}code{background:#f6f8fa;padding:1px 4px;border-radius:4px}"
        ".pass{color:#1a7f37;font-weight:600}.fail{color:#cf222e;font-weight:600}.xfail{color:#9a6700;font-weight:600}"
        ".none{color:#57606a;font-weight:600}"
        "figure{display:inline-block;margin:8px 12px 8px 0;max-width:48%;vertical-align:top}"
        "img{max-width:100%;border:1px solid #d0d7de;border-radius:6px}"
        "figcaption{font-size:12px;color:#57606a;word-break:break-all}"
        ".warn{background:#fff8c5;border-left:4px solid #d4a72c;padding:8px 12px;margin:12px 0}"
        ".ok{background:#dafbe1;border-left:4px solid #1a7f37;padding:8px 12px;margin:12px 0}"
        ".bad{background:#ffebe9;border-left:4px solid #cf222e;padding:8px 12px;margin:12px 0}"
        "</style></head><body>",
        f"<h1>{e(title)}</h1>",
        f"<p>生成时间：{e(report['generated_at'])}<br>运行 ID：<code>{e(run['run_id'])}</code><br>"
        f"目标：{e(run.get('target') or 'N/A')}<br>状态：{e(_status_label(run.get('status', '')))}<br>"
        f"交付门禁：<strong>{e(report['gate']['verdict'])}</strong>（exit {report['gate']['exit_code']}）</p>",
    ]

    scope = report["scope"]
    parts.append("<h2>1. 测试目标与范围</h2>")
    parts.append(table(["项目", "内容"], [
        ["目标 URL", scope["target"] or MISSING],
        ["测试范围", f"{scope['scope']}（来源：{scope['scope_source']}）"],
        ["需求来源", scope["requirement_source"]],
        ["用例表", scope["case_table"] or MISSING],
        ["用例设计文档", scope["design_doc"] or MISSING],
        ["用例数", str(summary["case_total"])],
        ["通过率", _pass_rate_text(summary)],
    ]))
    parts.append("<p>本报告只陈述 manifest 中登记且能在 JUnit 与证据文件中追溯的结果；"
                 "未执行、被跳过、受控预期失败的结果单独统计，不并入通过率。</p>")

    parts.append("<h2>2. 测试环境</h2>")
    parts.append(table(["项目", "值", "来源", "运行记录原值"],
                       [[label, value, source, raw or "—"]
                        for label, value, source, raw in _env_rows(report)]))
    if run.get("notes"):
        parts.append("<h3>运行备注</h3><ul>")
        for n in run["notes"]:
            parts.append(f"<li>{e(str(n.get('at', '')))}：{e(str(n.get('note', '')))}</li>")
        parts.append("</ul>")
    probe = report.get("environment_probe")
    parts.append("<h3>环境补充探测</h3>")
    if not probe:
        parts.append("<p>本次未执行环境探测（<code>--no-env-probe</code>）。</p>")
    else:
        parts.append(f"<p class='warn'>{e(probe.get('note', ''))}（探测时间 {e(str(probe.get('probed_at')))}）。"
                     "这些值不覆盖上表的运行记录。</p>")
        keys = ("python", "platform", "os", "pytest", "selenium", "chrome", "chrome_path",
                "chromedriver", "node", "openpyxl", "pillow")
        parts.append(table(["项目", "探测值"], [[k, str(probe[k])] for k in keys if k in probe]))

    strategy = report["strategy"]
    parts.append("<h2>3. 测试策略与设计方法</h2>")
    parts.append("<p>设计方法分布按用例表 <code>method</code> 列聚合；无法聚合时明确标注，不做推测。</p>")
    if strategy["methods"]:
        parts.append(table(["设计方法", "用例数", "用例"],
                           [[m["method"], str(m["count"]), "、".join(m["case_ids"])]
                            for m in strategy["methods"]]))
    else:
        parts.append(f"<p class='warn'>{e(strategy['note'] or '没有可聚合的 method 取值。')}</p>")
    if strategy["case_types"]:
        parts.append(table(["用例类型", "用例数"], [[t["case_type"], str(t["count"])]
                                                   for t in strategy["case_types"]]))
    if strategy["priorities"]:
        parts.append(table(["优先级", "用例数"], [[p["priority"], str(p["count"])]
                                                  for p in strategy["priorities"]]))
    parts.append("<ul><li>浏览器探索优先使用 DOM/无障碍快照，截图只用于视觉证据。</li>"
                 "<li>功能用例使用 Selenium + pytest + 显式等待，断言绑定可观察状态。</li>"
                 "<li>失败与受控预期失败自动保存视口/整页截图、页面源码和浏览器日志。</li>"
                 "<li>视觉差异只作为复核信号，不单独据此判定产品缺陷。</li></ul>")

    parts.append("<h2>4. 用例与执行结果</h2>")
    jc = report.get("junit_counts") or {}
    parts.append(f"<p>manifest 登记 {summary['case_total']} 条（通过 {summary['passed']}、"
                 f"受控预期失败 {summary['xfailed']}、失败 {summary['failed']}、未执行 {summary['not_run']}、"
                 f"跳过 {summary['skipped']}、阻塞 {summary['blocked']}）；JUnit tests={jc.get('total')}、"
                 f"passed={jc.get('passed')}、failed={jc.get('failed')}、xfailed={jc.get('xfailed')}。"
                 f"xfailed 不计入通过率（{e(_pass_rate_text(summary))}）。</p>")
    rows = []
    for c in report["cases"]:
        rows.append([c["case_id"], c["title"], c["case_type"] or "未登记", c["priority"] or "未登记",
                     f"{c['method'] or '方法未登记'} / "
                     f"{'、'.join(c['requirement_ids']) or '需求未登记'}",
                     _status_label(c["status"]), str(c["evidence_count"]), c["log_path"] or "未登记"])
    if not rows:
        rows.append([MISSING, "manifest 未登记任何用例", "—", "—", "—", "—", "0", "—"])
    parts.append(table(["用例 ID", "标题", "类型", "优先级", "方法与需求", "状态", "证据数", "日志"], rows))

    parts.append("<h2>5. 用例明细</h2>")
    for c in report["cases"]:
        cls = "pass" if c["status"] == "passed" else ("xfail" if c["status"] == "xfailed" else
                                                     ("none" if c["status"] in {"not-run", "skipped"} else "fail"))
        parts.append(f"<h3>{e(c['case_id'])} {e(c['title'])}</h3>")
        parts.append(f"<p>状态：<span class='{cls}'>{e(_status_label(c['status']))}</span><br>"
                     f"类型：{e(c['case_type'] or '未登记')}　优先级：{e(c['priority'] or '未登记')}　"
                     f"方法：{e(c['method'] or '未登记')}　需求：{e('、'.join(c['requirement_ids']) or '未登记')}<br>"
                     f"自动化：<code>{e(c['automation'] or '未登记')}</code><br>"
                     f"日志：<code>{e(c.get('log_path') or '未登记')}</code>"
                     f"{'' if c['log_exists'] else '（文件缺失）'}</p>")
        parts.append("<h4>前置条件</h4>")
        parts.append("<ol>" + "".join(f"<li>{e(s)}</li>" for s in c["preconditions"]) + "</ol>"
                     if c["preconditions"] else "<p>未登记</p>")
        parts.append(f"<h4>测试数据</h4><p>{e(c['test_data'] or '未登记')}</p>")
        parts.append("<h4>步骤</h4>")
        parts.append("<ol>" + "".join(f"<li>{e(s)}</li>" for s in c["steps"]) + "</ol>"
                     if c["steps"] else "<p>未登记</p>")
        parts.append(f"<h4>用例级预期</h4><p>{e(_expected_text(c))}</p>")
        if c["expected_note"]:
            parts.append(f"<p class='warn'>{e(c['expected_note'])}"
                         + (f"（运行记录原值：<code>{e(c['expected_raw'])}</code>）" if c["expected_raw"] else "")
                         + "</p>")
        parts.append(f"<h4>用例级实际</h4><p>{e(_actual_text(c))}</p>")
        if c["assertions"]:
            parts.append(f"<h4>断言（{c['assertion_count']} 条，通过 {c['assertions_passed']}）</h4>")
            parts.append(table(["#", "断言", "预期", "实际", "结果"],
                               [[str(i), a.get("name", ""), str(a.get("expected", "")),
                                 str(a.get("actual", "")), "通过" if a.get("passed") else "失败"]
                                for i, a in enumerate(c["assertions"], 1)]))
        else:
            parts.append("<h4>断言</h4><p>未登记断言。</p>")
        parts.append(f"<h4>证据（{c['evidence_count']}）</h4>")
        if c["evidence"]:
            parts.append("".join(img(ev) for ev in c["evidence"] if ev["kind"] in IMAGE_KINDS))
            parts.append("<ul>" + "".join(
                f"<li><code>{e(ev['evidence_id'])}</code> [{e(ev['kind'])}] <code>{e(ev['path'])}</code></li>"
                for ev in c["evidence"]) + "</ul>")
        else:
            parts.append("<p class='warn'>证据完整性警告：该用例没有登记任何证据文件。</p>")
        for d in c["defects"]:
            flag = "（疑似/待复核，未确认为产品缺陷）" if d["unconfirmed"] else ""
            parts.append(f"<p class='fail'>缺陷 <code>{e(d['defect_id'])}</code> "
                         f"[{e(d['severity_label'] or d['severity'])}] {e(d['title'])}{e(flag)}</p>")

    parts.append("<h2>6. 缺陷</h2>")
    defects = report["defects"]
    if not defects:
        parts.append("<p>本轮未登记产品缺陷。xfailed 用例只用于验证失败取证链路，不等同于产品缺陷。</p>")
    else:
        unconfirmed = [d for d in defects if d["unconfirmed"]]
        if unconfirmed:
            parts.append("<p class='warn'><strong>疑似/待复核，未确认为产品缺陷</strong>："
                         + e("、".join(f"{d['defect_id']}（{d['status']}）" for d in unconfirmed))
                         + "。这些记录不得作为缺陷结论引用。</p>")
        parts.append(table(
            ["缺陷 ID", "标题", "严重度", "严重度依据", "分类", "状态", "复现状态", "复现次数", "环境"],
            [[d["defect_id"], d["title"], f"{d['severity_label']}（{d['severity']}）",
              d.get("severity_rationale") or MISSING,
              f"{d['category_label']}（{d['category']}）" if d.get("category") else MISSING,
              f"{d['status_label']}（{d['status']}）", d.get("repro_label") or MISSING,
              str(d.get("repro_count") if d.get("repro_count") is not None else MISSING),
              d.get("environment") or MISSING] for d in defects]))
        for d in defects:
            parts.append(f"<h3>{e(d['defect_id'])} {e(d['title'])}</h3>")
            if d["unconfirmed"]:
                parts.append("<p class='bad'><strong>疑似/待复核，未确认为产品缺陷</strong>"
                             f"（status=<code>{e(str(d['status']))}</code>）。复核完成前不得作为产品缺陷结论。</p>")
            parts.append(table(["字段", "值"], [
                ["严重度", f"{d['severity_label'] or '未登记'}（{d.get('severity')}）"],
                ["严重度依据", d.get("severity_rationale") or MISSING],
                ["分类", f"{d['category_label']} / {d['category']}" if d.get("category") else MISSING],
                ["状态", f"{d['status_label']}（{d.get('status')}）"],
                ["复现状态", d.get("repro_label") or MISSING],
                ["复现次数", str(d.get("repro_count") if d.get("repro_count") is not None else MISSING)],
                ["复现环境", d.get("environment") or MISSING],
                ["描述", d.get("description") or MISSING],
                ["预期", d.get("expected") or MISSING],
                ["实际", d.get("actual") or MISSING],
            ]))
            parts.append("<h4>前置条件</h4>")
            parts.append("<ol>" + "".join(f"<li>{e(x)}</li>" for x in d.get("preconditions") or [])
                         + "</ol>" if d.get("preconditions") else "<p>未登记</p>")
            parts.append("<h4>复现步骤</h4>")
            parts.append("<ol>" + "".join(f"<li>{e(x)}</li>" for x in d.get("repro_steps") or [])
                         + "</ol>" if d.get("repro_steps") else "<p>未登记（缺陷缺少可复现步骤）</p>")
            if d["evidence_ids"]:
                parts.append("<h4>证据</h4><ul>" + "".join(
                    f"<li><code>{e(eid)}</code></li>" for eid in d["evidence_ids"]) + "</ul>")

    if report["visual"]:
        parts.append("<h2>7. 视觉差异</h2>")
        for m in report["visual"]:
            parts.append(f"<h3>{e(m.get('label', 'visual-check'))}</h3>")
            parts.append(f"<p>基准：<code>{e(str(m.get('baseline')))}</code><br>"
                         f"实际：<code>{e(str(m.get('actual')))}</code><br>"
                         f"判定：{e(_verdict_label(m.get('verdict')))}<br>"
                         f"差异像素：{m.get('changed_pixels')} / {m.get('total_pixels')}"
                         f"（{m.get('diff_ratio')}）<br>区域数：{m.get('region_count')}；"
                         f"PSNR：{m.get('psnr')}<br>指标：<code>{e(str(m.get('_metrics_path')))}</code></p>")
            if m.get("regions"):
                parts.append(table(["区域", "x", "y", "w", "h", "面积", "平均差"],
                                   [[str(r.get("region_id")), str(r["x"]), str(r["y"]), str(r["w"]),
                                     str(r["h"]), str(r["area"]), str(r.get("mean_abs_diff"))]
                                    for r in m["regions"]]))
            for name in ("annotated.png", "comparison.png", "heatmap.png"):
                p = Path(report["_project_root"]) / m["_dir"] / name
                if p.exists():
                    rel = rs.rel_posix(p, out_dir)
                    parts.append(f"<figure><a href='{e(rel)}'><img src='{e(rel)}' alt='{e(name)}'></a>"
                                 f"<figcaption>{e(name)}</figcaption></figure>")
    else:
        parts.append("<h2>7. 视觉差异</h2><p>本轮未生成差异图；有效截图证据见第 5 节。</p>")

    v = report["evidence"]
    parts.append("<h2>8. 证据完整性</h2>")
    parts.append(table(["指标", "数量"], [
        ["checked（登记）", str(v["checked"])], ["ok（校验通过）", str(v["ok"])],
        ["missing（文件缺失）", str(len(v["missing"]))],
        ["mismatched（哈希不一致）", str(len(v["mismatched"]))],
        ["cross_run（跨 run 引用）", str(len(v["cross_run"]))],
        ["unscoped（路径无 run id）", str(len(v["unscoped"]))],
        ["duplicates（重复登记）", str(len(v["duplicates"]))],
    ]))
    if v["missing"] or v["mismatched"] or v["cross_run"] or v["unscoped"]:
        parts.append("<p class='warn'>" + "<br>".join(filter(None, [
            f"缺失：{e(', '.join(v['missing']))}" if v["missing"] else "",
            f"不一致：{e(', '.join(v['mismatched']))}" if v["mismatched"] else "",
            f"跨 run：{e(', '.join(v['cross_run']))}" if v["cross_run"] else "",
            f"无 run id：{e(', '.join(v['unscoped']))}" if v["unscoped"] else "",
        ])) + "</p>")
    without = [c["case_id"] for c in report["cases"] if not c["evidence_complete"]]
    if without:
        parts.append(f"<p>无用例级证据：<code>{e(', '.join(without))}</code></p>")

    parts.append("<h2>9. 执行日志</h2>")
    junit = report.get("junit")
    if junit:
        parts.append(f"<p>JUnit：<code>{e(str(junit.get('junit')))}</code><br>"
                     f"摘要：<code>{e(str(junit.get('console_log')))}</code><br>"
                     f"tests={junit.get('tests')} failures={junit.get('failures')} "
                     f"errors={junit.get('errors')} skipped={junit.get('skipped')} "
                     f"xfailed={junit.get('xfailed')}</p>")
        if junit.get("cases"):
            parts.append(table(["测试函数", "类", "耗时(s)", "状态", "信息"],
                               [[c.get("name", ""), c.get("classname", ""), str(c.get("time")),
                                 c.get("status", ""), c.get("message", "")] for c in junit["cases"]]))
    else:
        parts.append("<p class='bad'>未找到 JUnit 汇总文件，本次执行结果不可复核。</p>")

    cov = report["coverage"]
    parts.append("<h2>10. 需求覆盖情况</h2>")
    if cov["requirements"]:
        parts.append(table(["需求", "关联用例", "已执行用例", "状态分布", "是否执行"],
                           [[i["requirement_id"], "、".join(i["case_ids"]),
                             "、".join(i["executed_case_ids"]) or "无",
                             "、".join(f"{_status_label(k)} {n}" for k, n in sorted(i["status_counts"].items())),
                             "是" if i["executed"] else "否"] for i in cov["requirements"]]))
        if cov["requirements_without_execution"]:
            parts.append("<p class='warn'>有用例但本轮未执行的需求："
                         + e("、".join(cov["requirements_without_execution"])) + "</p>")
        if cov["unmapped_cases"]:
            parts.append("<p>未关联任何需求的用例：<code>" + e("、".join(cov["unmapped_cases"]))
                         + "</code></p>")
    else:
        parts.append(f"<p class='warn'>{e(cov['note'] or '没有可聚合的需求信息。')}</p>")

    parts.append("<h2>11. 未执行项与已知限制</h2>")
    if cov["not_run"]:
        parts.append("<h3>未执行（不计入通过率）</h3><ul>" + "".join(
            f"<li>{e(i['case_id'])} {e(i['title'])}（{e(i['design_status'] or '状态未登记')}）</li>"
            for i in cov["not_run"]) + "</ul>")
    if cov["partial"]:
        parts.append("<h3>部分覆盖</h3><ul>" + "".join(
            f"<li>{e(i['case_id'])} {e(i['title'])}（{e(i['design_status'])}）</li>"
            for i in cov["partial"]) + "</ul>")
    not_run_cases = [c for c in report["cases"] if c["status"] in {"not-run", "skipped", "blocked"}]
    if not_run_cases:
        parts.append("<h3>manifest 中未产生结果的用例</h3><ul>" + "".join(
            f"<li>{e(c['case_id'])} {e(c['title'])}：{e(_status_label(c['status']))}</li>"
            for c in not_run_cases) + "</ul>")
    parts.append("<h3>已知限制</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in report["limitations"]) + "</ul>")

    qg = report["quality_gate"]
    parts.append("<h2>12. 质量门禁结果</h2>")
    if not qg["found"]:
        parts.append("<p>本次未运行质量门禁（未找到 "
                     f"<code>qualification/gate-runs/{e(run['run_id'])}/gate-report.json</code>）。</p>")
    elif qg.get("error"):
        parts.append(f"<p class='warn'>质量门禁报告无法解析：{e(qg['error'])}</p>")
    else:
        parts.append(f"<p>门禁报告：<code>{e(qg['path'])}</code><br>"
                     f"delivery_verdict：<strong>{e(str(qg.get('delivery_verdict')))}</strong><br>"
                     f"test_verdict：<strong>{e(str(qg.get('test_verdict')))}</strong></p>")
        if qg["gate_status"]:
            parts.append(table(["Gate", "状态"], [[k, v] for k, v in sorted(qg["gate_status"].items())]))
        if qg.get("fail_findings"):
            parts.append(table(["Gate", "代码", "级别", "对象", "说明"],
                               [[f.get("gate"), f.get("code"), f.get("severity"),
                                 f.get("subject") or "", f.get("message") or ""]
                                for f in qg["fail_findings"]]))
        else:
            parts.append("<p>质量门禁未报告 FAIL/BLOCKED findings。</p>")
    cls = "ok" if report["gate"]["verdict"] in {"PASS", "WARNING"} else "bad"
    parts.append(f"<h3>报告交付门禁</h3><p class='{cls}'>结论：<strong>{e(report['gate']['verdict'])}</strong>"
                 f"（退出码 {report['gate']['exit_code']}）</p>")
    if report["gate"]["findings"]:
        parts.append(table(["代码", "级别", "对象", "说明"],
                           [[f["code"], f["severity"], f["subject"], f["message"]]
                            for f in report["gate"]["findings"]]))

    parts.append("<h2>附录</h2><ul>")
    parts.append(f"<li>报告生成器：<code>tools/generate_report.py</code> v{GENERATOR_VERSION}</li>")
    parts.append(f"<li>报告 schema：<code>{e(report['schema_version'])}</code></li>")
    parts.append(f"<li>用例表来源：<code>{e(report['case_table']['path'] or MISSING)}</code></li>")
    if not report["case_table"]["found"]:
        parts.append(f"<li>用例表查找说明：{e(report['case_table']['reason'])}</li>")
    parts.append("</ul></body></html>")
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------- #
# defects markdown (written next to the report, never outside --out-dir)
# --------------------------------------------------------------------------- #
def render_defects(report: dict[str, Any]) -> str:
    lines = [f"# 缺陷清单 {report['run']['run_id']}", ""]
    if not report["defects"]:
        lines += ["未登记产品缺陷。受控预期失败仅用于验证失败取证链路，不计为产品缺陷。", ""]
        return "\n".join(lines) + "\n"
    for d in report["defects"]:
        lines.append(f"## {d['defect_id']} {d['title']}")
        lines.append("")
        if d["unconfirmed"]:
            lines += ["> 疑似/待复核，未确认为产品缺陷。", ""]
        lines += [
            f"- 严重度：{d['severity_label']}（{d.get('severity')}）",
            f"- 严重度依据：{d.get('severity_rationale') or MISSING}",
            f"- 分类：{d['category_label']}（{d.get('category')}）",
            f"- 状态：{d['status_label']}（{d.get('status')}）",
            f"- 复现状态：{d.get('repro_label') or MISSING}；复现次数：{d.get('repro_count')}",
            f"- 复现环境：{d.get('environment') or MISSING}",
            f"- 预期：{d.get('expected') or MISSING}",
            f"- 实际：{d.get('actual') or MISSING}",
            f"- 说明：{d.get('description') or MISSING}",
            "",
        ]
        if d.get("preconditions"):
            lines.append("**前置条件**")
            lines += [f"{i}. {x}" for i, x in enumerate(d["preconditions"], 1)]
            lines.append("")
        if d.get("repro_steps"):
            lines.append("**复现步骤**")
            lines += [f"{i}. {x}" for i, x in enumerate(d["repro_steps"], 1)]
            lines.append("")
        else:
            lines += ["**复现步骤**：未登记", ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="generate test report (markdown + html + json)")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--title", default="Web 应用测试执行报告")
    parser.add_argument("--cases", default="", help="显式指定用例表；默认只接受 executed_in_run 含本 run 的表")
    parser.add_argument("--manifest", default="", help="覆盖 manifest 路径（自测用）")
    parser.add_argument("--project-root", default="", help="覆盖项目根目录（自测用）")
    parser.add_argument("--reports-root", default="", help="覆盖 reports 目录（自测用）")
    parser.add_argument("--junit-summary", default="",
                        help="junit-summary.json 路径；默认读取 --out-dir/junit-summary.json")
    parser.add_argument("--require-cases", type=int, default=None)
    parser.add_argument("--gate", dest="gate", action="store_true", default=True,
                        help="生成后执行交付门禁（默认开启）")
    parser.add_argument("--no-gate", dest="gate", action="store_false")
    parser.add_argument("--no-env-probe", dest="env_probe", action="store_false", default=True)
    parser.add_argument("--json", action="store_true", help="兼容开关：标准输出始终为 JSON 摘要")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve() if args.project_root else ROOT
    manifest_path = Path(args.manifest) if args.manifest else project_root / "evidence" / "manifest.json"
    reports_root = Path(args.reports_root) if args.reports_root else project_root / "reports"
    paths = Paths(project_root=project_root, manifest_path=manifest_path, reports_root=reports_root)

    out_dir = Path(args.out_dir) if args.out_dir else reports_root / "executions" / args.run_id
    if not out_dir.is_absolute():
        out_dir = project_root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        report = build(args.run_id, out_dir, args.title, paths=paths,
                       cases_path=Path(args.cases) if args.cases else None,
                       require_cases=args.require_cases, gate_enabled=args.gate,
                       probe_env=args.env_probe,
                       junit_summary=Path(args.junit_summary) if args.junit_summary else None)
    except KeyError as exc:
        message = str(exc.args[0]) if exc.args else str(exc)
        print(json.dumps({"error": message, "run_id": args.run_id, "exit_code": 2},
                         ensure_ascii=False, indent=2))
        return 2
    except FileNotFoundError as exc:
        print(json.dumps({"error": str(exc), "run_id": args.run_id, "exit_code": 2},
                         ensure_ascii=False, indent=2))
        return 2

    (out_dir / "report.md").write_text(render_markdown(report, out_dir, args.title), encoding="utf-8")
    (out_dir / "report.html").write_text(render_html(report, out_dir, args.title), encoding="utf-8")
    (out_dir / "defects.md").write_text(render_defects(report), encoding="utf-8")
    public = {k: v for k, v in report.items() if not k.startswith("_")}
    (out_dir / "report.json").write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")

    exit_code = report["exit_code"]
    print(json.dumps({
        "run_id": args.run_id,
        "title": args.title,
        "out_dir": str(out_dir),
        "markdown": str(out_dir / "report.md"),
        "html": str(out_dir / "report.html"),
        "json": str(out_dir / "report.json"),
        "defects_md": str(out_dir / "defects.md"),
        "case_count": len(report["cases"]),
        "status_counts": report["summary"]["status_counts"],
        "pass_rate": report["summary"]["pass_rate"],
        "pass_rate_note": report["summary"]["pass_rate_note"],
        "case_table": {"found": report["case_table"]["found"],
                       "path": report["case_table"]["path"],
                       "reason": report["case_table"]["reason"]},
        "environment_missing": [k for k, v in report["environment"].items()
                                if str(v).startswith(MISSING)],
        "evidence": {k: report["evidence"][k] for k in
                     ("checked", "ok", "missing", "mismatched", "cross_run", "unscoped")},
        "expected_fallback_cases": [c["case_id"] for c in report["cases"]
                                    if c["expected_source"] == "assertions"],
        "gate": {k: report["gate"][k] for k in ("enabled", "verdict", "exit_code", "counts")},
        "findings": report["gate"]["findings"],
        "exit_code": exit_code,
    }, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
