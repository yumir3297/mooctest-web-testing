#!/usr/bin/env python3
"""Evidence manager for the mooctest-web-testing workflow.

All evidence stays inside the project. Raw screenshots are treated as
immutable; annotations and diffs are written to separate directories.

Schema notes (v1.1):
- `case.expected` / `case.actual` are *case level* oracles. They are no longer
  overwritten by the last assertion; per-assertion detail lives in
  `case.assertions`.
- `case.meta` carries design metadata (requirement ids, method, priority).
- `defect` records environment, preconditions, reproduction steps and a
  reproduction status so a report can be reproduced without guessing.
- A `passed` case must have at least one assertion or at least one evidence
  file. Manual status flipping is rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "evidence"
REPORTS_DIR = ROOT / "reports"
MANIFEST_PATH = EVIDENCE_DIR / "manifest.json"
LOCK_PATH = EVIDENCE_DIR / ".manifest.lock"

RAW_DIR = EVIDENCE_DIR / "raw"
ANNOTATED_DIR = EVIDENCE_DIR / "annotated"
DIFF_DIR = EVIDENCE_DIR / "diff"
LOGS_DIR = EVIDENCE_DIR / "logs"

SCHEMA_VERSION = "1.1"

CASE_STATUSES = {"not-run", "running", "passed", "failed", "xfailed", "blocked", "skipped"}
RUN_STATUSES = {"running", "passed", "failed", "blocked", "aborted"}
BUCKETS = {"raw", "annotated", "diff", "logs"}
SEVERITIES = {"blocker", "critical", "major", "minor", "trivial"}
DEFECT_STATUSES = {"open", "confirmed", "suspected", "needs_review", "not_a_defect", "fixed"}
DEFECT_CATEGORIES = {"APP", "SCRIPT", "ENV", "DATA", "LOCATOR", "TIMING", "UNKNOWN"}

RUN_ID_RE = re.compile(r"RUN-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_layout() -> None:
    for p in (EVIDENCE_DIR, RAW_DIR, ANNOTATED_DIR, DIFF_DIR, LOGS_DIR,
              REPORTS_DIR, REPORTS_DIR / "test-cases", REPORTS_DIR / "executions",
              REPORTS_DIR / "defects"):
        p.mkdir(parents=True, exist_ok=True)
    if not MANIFEST_PATH.exists():
        tmp = MANIFEST_PATH.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(_new_manifest(), f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, MANIFEST_PATH)


def _new_manifest() -> dict[str, Any]:
    ts = now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "project": "mooctest-web-testing",
        "created_at": ts,
        "updated_at": ts,
        "runs": {},
        "evidence": [],
    }


class ManifestLock:
    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self.acquired = False

    def __enter__(self) -> "ManifestLock":
        ensure_layout()
        deadline = time.time() + self.timeout
        while True:
            try:
                fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("ascii"))
                os.close(fd)
                self.acquired = True
                return self
            except FileExistsError:
                try:
                    if time.time() - LOCK_PATH.stat().st_mtime > 120:
                        LOCK_PATH.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                if time.time() > deadline:
                    raise TimeoutError(f"manifest lock timeout: {LOCK_PATH}")
                time.sleep(0.1)

    def __exit__(self, *exc: object) -> None:
        if self.acquired:
            try:
                LOCK_PATH.unlink(missing_ok=True)
            except OSError:
                pass


def load_manifest() -> dict[str, Any]:
    ensure_layout()
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(data: dict[str, Any]) -> None:
    ensure_layout()
    data["updated_at"] = now_iso()
    data["schema_version"] = SCHEMA_VERSION
    tmp = MANIFEST_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, MANIFEST_PATH)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _image_info(path: Path) -> dict[str, Any] | None:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return {"width": im.width, "height": im.height, "mode": im.mode, "format": im.format}
    except Exception:
        return None


def _safe_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _resolve_in_project(value: str) -> Path:
    p = Path(value)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    try:
        p.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"path must stay inside project: {p}") from exc
    return p


def _bucket_dir(bucket: str) -> Path:
    mapping = {"raw": RAW_DIR, "annotated": ANNOTATED_DIR, "diff": DIFF_DIR, "logs": LOGS_DIR}
    return mapping[bucket]


def _find_run(data: dict[str, Any], run_id: str) -> dict[str, Any]:
    run = data["runs"].get(run_id)
    if run is None:
        raise KeyError(f"run not found: {run_id}")
    return run


def _new_case(case_id: str, title: str | None = None, status: str = "not-run") -> dict[str, Any]:
    return {
        "case_id": case_id,
        "title": title or case_id,
        "status": status,
        "started_at": now_iso(),
        "finished_at": None,
        "expected": "",
        "actual": "",
        "steps": [],
        "assertions": [],
        "evidence": [],
        "defects": [],
        "log_path": None,
        "notes": [],
        "meta": {},
    }


def start_run(run_id: str | None = None, target: str = "", label: str = "",
              environment: dict[str, str] | None = None, reuse: bool = False) -> str:
    ensure_layout()
    with ManifestLock():
        data = load_manifest()
        rid = run_id or f"RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        if rid in data["runs"] and not reuse:
            raise ValueError(f"run already exists: {rid} (use --reuse to update)")
        ts = now_iso()
        if rid in data["runs"]:
            run = data["runs"][rid]
            run.update({"target": target or run.get("target", ""), "label": label or run.get("label", "")})
            if environment:
                run.setdefault("environment", {}).update(environment)
            run.setdefault("started_at", ts)
        else:
            run = {
                "run_id": rid,
                "label": label,
                "target": target,
                "started_at": ts,
                "finished_at": None,
                "status": "running",
                "stage": "init",
                "environment": environment or {},
                "cases": {},
                "notes": [],
            }
            data["runs"][rid] = run
        run["updated_at"] = ts
        run.setdefault("schema_version", SCHEMA_VERSION)
        save_manifest(data)
        return rid


def update_run(run_id: str, status: str | None = None, stage: str | None = None,
               note: str | None = None, label: str | None = None,
               environment: dict[str, str] | None = None) -> dict[str, Any]:
    if status is not None and status not in RUN_STATUSES:
        raise ValueError(f"invalid run status: {status}")
    with ManifestLock():
        data = load_manifest()
        run = _find_run(data, run_id)
        if status:
            run["status"] = status
        if label:
            run["label"] = label
        if stage:
            run["stage"] = stage
        if environment:
            run.setdefault("environment", {}).update(environment)
        if note:
            run.setdefault("notes", []).append({"at": now_iso(), "note": note})
        if status in {"passed", "failed", "blocked", "aborted"}:
            run["finished_at"] = now_iso()
        run["updated_at"] = now_iso()
        save_manifest(data)
        return run


def update_case(run_id: str, case_id: str, title: str | None = None,
                status: str | None = None, expected: str | None = None,
                actual: str | None = None, steps: list[str] | None = None,
                assertions: list[dict[str, Any]] | None = None,
                log_path: str | None = None, notes: str | None = None,
                duration_ms: int | None = None,
                meta: dict[str, Any] | None = None) -> dict[str, Any]:
    if status is not None and status not in CASE_STATUSES:
        raise ValueError(f"invalid case status: {status}")
    with ManifestLock():
        data = load_manifest()
        run = _find_run(data, run_id)
        cases = run.setdefault("cases", {})
        case = cases.setdefault(case_id, _new_case(case_id, title))
        if title:
            case["title"] = title
        if expected is not None:
            case["expected"] = expected
        if actual is not None:
            case["actual"] = actual
        if steps is not None:
            case["steps"] = steps
        if assertions is not None:
            case["assertions"] = assertions
        if log_path:
            case["log_path"] = log_path
        if notes:
            case.setdefault("notes", []).append({"at": now_iso(), "note": notes})
        if duration_ms is not None:
            case["duration_ms"] = duration_ms
        if meta:
            case.setdefault("meta", {}).update(meta)
        if status:
            if status == "passed" and not case.get("assertions") and not case.get("evidence"):
                raise ValueError(
                    f"case {case_id}: refusing to record 'passed' without assertions or evidence "
                    "(manual status flipping is blocked)"
                )
            case["status"] = status
            if status in {"passed", "failed", "xfailed", "blocked", "skipped"}:
                case["finished_at"] = now_iso()
            elif status == "running":
                case["started_at"] = case.get("started_at") or now_iso()
        case["updated_at"] = now_iso()
        save_manifest(data)
        return case


def add_defect(run_id: str, case_id: str, title: str, severity: str,
               description: str, expected: str = "", actual: str = "",
               evidence: list[str] | None = None, status: str = "open",
               environment: str = "", preconditions: list[str] | None = None,
               repro_steps: list[str] | None = None, repro_status: str = "not-reproduced",
               repro_count: int = 0, category: str = "APP",
               severity_rationale: str = "") -> dict[str, Any]:
    if severity not in SEVERITIES:
        raise ValueError(f"invalid severity: {severity} (expected one of {sorted(SEVERITIES)})")
    if status not in DEFECT_STATUSES:
        raise ValueError(f"invalid defect status: {status} (expected one of {sorted(DEFECT_STATUSES)})")
    if category not in DEFECT_CATEGORIES:
        raise ValueError(f"invalid defect category: {category} (expected one of {sorted(DEFECT_CATEGORIES)})")
    with ManifestLock():
        data = load_manifest()
        run = _find_run(data, run_id)
        case = run.setdefault("cases", {}).setdefault(case_id, _new_case(case_id, status="failed"))
        existing = [d for c in run.get("cases", {}).values() for d in c.get("defects", [])]
        defect = {
            "defect_id": f"DEF-{len(existing) + 1:03d}",
            "title": title,
            "severity": severity,
            "severity_rationale": severity_rationale,
            "category": category,
            "status": status,
            "description": description,
            "environment": environment,
            "preconditions": preconditions or [],
            "repro_steps": repro_steps or [],
            "repro_status": repro_status,
            "repro_count": repro_count,
            "expected": expected,
            "actual": actual,
            "evidence": evidence or [],
            "created_at": now_iso(),
        }
        case.setdefault("defects", []).append(defect)
        save_manifest(data)
        return defect


def register_evidence(run_id: str, case_id: str, kind: str, path: str,
                      bucket: str = "raw", step: str = "", caption: str = "",
                      immutable: bool = True, meta: dict[str, str] | None = None) -> dict[str, Any]:
    if bucket not in BUCKETS:
        raise ValueError(f"invalid bucket: {bucket}")
    p = _resolve_in_project(path)
    if not p.is_file():
        raise FileNotFoundError(f"evidence file not found: {p}")
    expected_root = _bucket_dir(bucket).resolve()
    try:
        p.relative_to(expected_root)
    except ValueError as exc:
        raise ValueError(f"evidence file must be under evidence/{bucket}: {p}") from exc
    rel = _safe_relative(p)
    referenced_runs = set(RUN_ID_RE.findall(rel))
    if referenced_runs and run_id not in referenced_runs:
        raise ValueError(
            f"cross-run evidence rejected: path {rel} references {sorted(referenced_runs)} "
            f"but run_id is {run_id}"
        )
    entry_meta = dict(meta or {})
    if not referenced_runs:
        entry_meta.setdefault("unscoped", "true")
    info = _image_info(p) if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} else None
    entry = {
        "evidence_id": f"EV-{hashlib.sha256((rel + now_iso()).encode('utf-8')).hexdigest()[:10]}",
        "run_id": run_id,
        "case_id": case_id,
        "kind": kind,
        "path": rel,
        "bucket": bucket,
        "step": step,
        "caption": caption,
        "created_at": now_iso(),
        "size_bytes": p.stat().st_size,
        "sha256": _sha256(p),
        "immutable": immutable,
        "meta": entry_meta,
    }
    if info:
        entry.update(info)
    with ManifestLock():
        data = load_manifest()
        run = _find_run(data, run_id)
        for existing in data["evidence"]:
            if existing.get("run_id") == run_id and existing.get("path") == rel:
                raise ValueError(f"duplicate evidence registration: {rel} already registered for {run_id}")
        case = run.setdefault("cases", {}).setdefault(case_id, _new_case(case_id, status="running"))
        data["evidence"].append(entry)
        case.setdefault("evidence", []).append(entry["evidence_id"])
        case["updated_at"] = now_iso()
        save_manifest(data)
    return entry


def run_summary(run_id: str) -> dict[str, Any]:
    data = load_manifest()
    run = _find_run(data, run_id)
    counts: dict[str, int] = {}
    for case in run.get("cases", {}).values():
        counts[case.get("status", "not-run")] = counts.get(case.get("status", "not-run"), 0) + 1
    run_evidence = [e for e in data["evidence"] if e.get("run_id") == run_id]
    return {
        "run_id": run_id,
        "label": run.get("label", ""),
        "target": run.get("target", ""),
        "status": run.get("status", ""),
        "stage": run.get("stage", ""),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "case_counts": counts,
        "case_total": sum(counts.values()),
        "evidence_count": len(run_evidence),
        "defect_count": sum(len(c.get("defects", [])) for c in run.get("cases", {}).values()),
    }


def verify_evidence(run_id: str | None = None) -> dict[str, Any]:
    data = load_manifest()
    entries = data["evidence"]
    if run_id:
        entries = [e for e in entries if e.get("run_id") == run_id]
    missing, mismatched, cross_run, unscoped, duplicates = [], [], [], [], []
    seen: set[tuple[str, str]] = set()
    ok = 0
    for e in entries:
        rel = e.get("path", "")
        referenced = set(RUN_ID_RE.findall(rel))
        if referenced and e.get("run_id") not in referenced:
            cross_run.append(rel)
        if not referenced:
            unscoped.append(rel)
        key = (str(e.get("run_id")), rel)
        if key in seen:
            duplicates.append(rel)
        seen.add(key)
        p = ROOT / rel
        if not p.is_file():
            missing.append(rel)
            continue
        if p.stat().st_size != e.get("size_bytes") or _sha256(p) != e.get("sha256"):
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


def write_index() -> Path:
    data = load_manifest()
    lines = ["# 证据索引", "", f"更新时间：{now_iso()}", ""]
    for rid, run in sorted(data["runs"].items()):
        lines.append(f"## {rid} - {run.get('label') or run.get('target') or '未命名'}")
        lines.append("")
        lines.append(f"- 目标：{run.get('target') or 'N/A'}")
        lines.append(f"- 状态：{run.get('status')}")
        lines.append(f"- 阶段：{run.get('stage')}")
        lines.append("")
        cases = run.get("cases", {})
        if not cases:
            lines.append("（暂无用例）")
            lines.append("")
            continue
        for cid, case in sorted(cases.items()):
            lines.append(f"### {cid} {case.get('title','')}")
            lines.append("")
            lines.append(f"- 状态：{case.get('status')}")
            if case.get("expected"):
                lines.append(f"- 预期：{case['expected']}")
            if case.get("actual"):
                lines.append(f"- 实际：{case['actual']}")
            if case.get("log_path"):
                lines.append(f"- 日志：`{case['log_path']}`")
            ev_ids = set(case.get("evidence", []))
            evs = [e for e in data["evidence"] if e["evidence_id"] in ev_ids]
            if evs:
                lines.append("- 证据：")
                for e in evs:
                    lines.append(f"  - [{e['kind']}] `{e['path']}` - {e.get('caption','')}")
            if case.get("defects"):
                lines.append("- 缺陷：")
                for d in case["defects"]:
                    lines.append(f"  - {d['defect_id']} [{d['severity']}/{d.get('category','?')}] {d['title']}")
            lines.append("")
    out = EVIDENCE_DIR / "INDEX.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _parse_env(values: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise ValueError(f"environment must be key=value: {item}")
        k, v = item.split("=", 1)
        out[k] = v
    return out


def _parse_meta(values: list[str] | None) -> dict[str, str]:
    return _parse_env(values)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="mooctest evidence manager")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.set_defaults(func=lambda a: ensure_layout() or 0)

    p = sub.add_parser("start-run")
    p.add_argument("--run-id")
    p.add_argument("--target", default="")
    p.add_argument("--label", default="")
    p.add_argument("--env", action="append")
    p.add_argument("--reuse", action="store_true")
    p.set_defaults(func=lambda a: print(start_run(a.run_id, a.target, a.label, _parse_env(a.env), a.reuse)) or 0)

    p = sub.add_parser("update-run")
    p.add_argument("--run-id", required=True)
    p.add_argument("--status", choices=sorted(RUN_STATUSES))
    p.add_argument("--stage")
    p.add_argument("--note")
    p.add_argument("--label")
    p.add_argument("--env", action="append")
    p.set_defaults(func=lambda a: print(json.dumps(
        update_run(a.run_id, a.status, a.stage, a.note, a.label, _parse_env(a.env)),
        ensure_ascii=False, indent=2)) or 0)

    p = sub.add_parser("update-case")
    p.add_argument("--run-id", required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--title")
    p.add_argument("--status", choices=sorted(CASE_STATUSES))
    p.add_argument("--expected")
    p.add_argument("--actual")
    p.add_argument("--step", action="append")
    p.add_argument("--log-path")
    p.add_argument("--note")
    p.add_argument("--duration-ms", type=int)
    p.add_argument("--meta", action="append")
    p.set_defaults(func=lambda a: print(json.dumps(update_case(
        a.run_id, a.case_id, a.title, a.status, a.expected, a.actual, a.step,
        None, a.log_path, a.note, a.duration_ms, _parse_meta(a.meta)),
        ensure_ascii=False, indent=2)) or 0)

    p = sub.add_parser("add-defect")
    p.add_argument("--run-id", required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--severity", required=True, choices=sorted(SEVERITIES))
    p.add_argument("--severity-rationale", default="")
    p.add_argument("--category", default="APP", choices=sorted(DEFECT_CATEGORIES))
    p.add_argument("--description", required=True)
    p.add_argument("--expected", default="")
    p.add_argument("--actual", default="")
    p.add_argument("--environment", default="")
    p.add_argument("--precondition", action="append")
    p.add_argument("--repro-step", action="append")
    p.add_argument("--repro-status", default="not-reproduced")
    p.add_argument("--repro-count", type=int, default=0)
    p.add_argument("--status", default="open", choices=sorted(DEFECT_STATUSES))
    p.add_argument("--evidence", action="append")
    p.set_defaults(func=lambda a: print(json.dumps(add_defect(
        a.run_id, a.case_id, a.title, a.severity, a.description, a.expected, a.actual,
        a.evidence, a.status, a.environment, a.precondition, a.repro_step,
        a.repro_status, a.repro_count, a.category, a.severity_rationale),
        ensure_ascii=False, indent=2)) or 0)

    p = sub.add_parser("register")
    p.add_argument("--run-id", required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--bucket", choices=sorted(BUCKETS), default="raw")
    p.add_argument("--step", default="")
    p.add_argument("--caption", default="")
    p.add_argument("--mutable", action="store_true")
    p.add_argument("--meta", action="append")
    p.set_defaults(func=lambda a: print(json.dumps(register_evidence(
        a.run_id, a.case_id, a.kind, a.path, a.bucket, a.step, a.caption,
        not a.mutable, _parse_meta(a.meta)), ensure_ascii=False, indent=2)) or 0)

    p = sub.add_parser("summary")
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=lambda a: print(json.dumps(run_summary(a.run_id), ensure_ascii=False, indent=2)) or 0)

    p = sub.add_parser("verify")
    p.add_argument("--run-id")
    p.add_argument("--fail-on-error", action="store_true")
    def _verify(a: argparse.Namespace) -> int:
        result = verify_evidence(a.run_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if a.fail_on_error and (result["missing"] or result["mismatched"]):
            return 1
        return 0
    p.set_defaults(func=_verify)

    p = sub.add_parser("index")
    p.set_defaults(func=lambda a: print(write_index()) or 0)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
