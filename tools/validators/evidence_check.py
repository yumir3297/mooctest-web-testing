"""G3 - evidence registry, defect completeness and failure triage.

Hash/immutability logic is **not** re-implemented here: the gate imports
``tools/evidence.py`` and calls :func:`evidence.verify_evidence`.  Because the
gate has to verify *sample* manifests that live outside ``evidence/manifest.json``
(for the qualification suite), the module root and manifest path are temporarily
pointed at the manifest under test.  Nothing is written: verification is
read-only and the sample manifests always exist.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from . import defects as defects_mod
from .common import Report, as_list, truncate

GATE = "G3"

FALLBACK_ENUMS: dict[str, set[str]] = {
    "severity": {"blocker", "critical", "major", "minor", "trivial"},
    "status": {"open", "confirmed", "suspected", "needs_review", "not_a_defect", "fixed"},
    "category": {"APP", "SCRIPT", "ENV", "DATA", "LOCATOR", "TIMING", "UNKNOWN"},
    "repro_status": {"not-reproduced", "reproduced", "intermittent", "blocked"},
}


def load_evidence_module(project_root: Path):
    tools_dir = project_root / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import evidence  # noqa: PLC0415 - deliberately late, path set above

    return evidence


def enum_sets(evidence_module: Any | None) -> dict[str, set[str]]:
    if evidence_module is None:
        return {key: set(value) for key, value in FALLBACK_ENUMS.items()}
    return {
        "severity": set(getattr(evidence_module, "SEVERITIES", FALLBACK_ENUMS["severity"])),
        "status": set(getattr(evidence_module, "DEFECT_STATUSES", FALLBACK_ENUMS["status"])),
        "category": set(getattr(evidence_module, "DEFECT_CATEGORIES", FALLBACK_ENUMS["category"])),
        "repro_status": {"not-reproduced", "reproduced", "intermittent", "blocked"},
    }


@contextlib.contextmanager
def scoped_manifest(evidence_module: Any, root: Path, manifest: Path) -> Iterator[None]:
    """Point the evidence module at another project root / manifest path."""
    saved_root = evidence_module.ROOT
    saved_manifest = evidence_module.MANIFEST_PATH
    evidence_module.ROOT = Path(root)
    evidence_module.MANIFEST_PATH = Path(manifest)
    try:
        yield
    finally:
        evidence_module.ROOT = saved_root
        evidence_module.MANIFEST_PATH = saved_manifest


def _record_many(report: Report, code: str, severity: str, items: Sequence[str],
                 message: str, limit: int = 8) -> None:
    for item in list(items)[:limit]:
        report.add(GATE, code, severity, item, message, item)
    if len(items) > limit:
        report.add(GATE, code, severity, f"+{len(items) - limit} more",
                   f"{message}（其余 {len(items) - limit} 条同类问题省略）")


def validate(report: Report, *,
             run_id: str,
             manifest_path: Path,
             manifest_data: Mapping[str, Any] | None,
             run: Mapping[str, Any] | None,
             evidence_entries: Sequence[Mapping[str, Any]],
             case_root: Path,
             project_root: Path,
             official: bool = False) -> dict[str, Any]:
    stats: dict[str, Any] = {}

    report.check(GATE, "MANIFEST_PRESENT", manifest_data is not None, str(manifest_path),
                 "证据清单缺失或无法解析", "FAIL")
    report.check(GATE, "RUN_NOT_FOUND", run is not None, run_id,
                 f"manifest 中不存在 run `{run_id}`", "FAIL")
    if manifest_data is None or run is None:
        return stats

    evidence_module = None
    scoped: dict[str, Any] = {"checked": 0, "ok": 0, "missing": [], "mismatched": [],
                              "cross_run": [], "unscoped": [], "duplicates": []}
    global_result: dict[str, Any] | None = None
    try:
        evidence_module = load_evidence_module(project_root)
    except Exception as exc:  # pragma: no cover - defensive
        report.add(GATE, "EVIDENCE_MODULE_UNAVAILABLE", "FAIL", "tools/evidence.py",
                   f"无法导入证据管理器：{type(exc).__name__}: {exc}")
    if evidence_module is not None:
        with scoped_manifest(evidence_module, case_root, manifest_path):
            scoped = evidence_module.verify_evidence(run_id)
            global_result = evidence_module.verify_evidence(None)

    stats["evidence_verify"] = {
        "checked": scoped.get("checked", 0),
        "ok": scoped.get("ok", 0),
        "missing": len(scoped.get("missing") or []),
        "mismatched": len(scoped.get("mismatched") or []),
        "cross_run": len(scoped.get("cross_run") or []),
        "unscoped": len(scoped.get("unscoped") or []),
    }

    # --- integrity ---------------------------------------------------------
    missing = scoped.get("missing") or []
    mismatched = scoped.get("mismatched") or []
    if missing:
        _record_many(report, "EVIDENCE_MISSING", "FAIL", missing,
                     "登记的截图/日志文件不存在")
    else:
        report.check(GATE, "EVIDENCE_FILES_PRESENT", True, run_id,
                     f"{scoped.get('checked', 0)} 条登记证据的文件全部存在")
    if mismatched:
        _record_many(report, "EVIDENCE_HASH_MISMATCH", "FAIL", mismatched,
                     "证据文件哈希与 manifest 不一致（证据被替换/篡改）")
    else:
        report.check(GATE, "EVIDENCE_HASH_MATCH", True, run_id,
                     "所有登记证据的 sha256/size 与 manifest 一致")

    duplicates = scoped.get("duplicates") or []
    report.check(GATE, "EVIDENCE_DUPLICATE_PATH", not duplicates, run_id,
                 f"{len(duplicates)} 条证据路径被重复登记", "FAIL")

    # --- cross run scope ---------------------------------------------------
    # Only the target run's own registrations decide the verdict.  Historical
    # cross-run rows belong to other runs and must not fail this delivery.
    cross_run = scoped.get("cross_run") or []
    report.check(GATE, "EVIDENCE_CROSS_RUN", not cross_run, run_id,
                 f"{len(cross_run)} 条证据登记在别的 run 目录下（本 run 不可用）", "FAIL")
    if cross_run:
        _record_many(report, "EVIDENCE_CROSS_RUN", "FAIL", cross_run,
                     "跨 run 证据：路径中的 RUN-* 与登记 run_id 不一致")

    unscoped = scoped.get("unscoped") or []
    official_target = official or str(
        ((run or {}).get("meta") or {}).get("delivery_target")
        or (run or {}).get("delivery_target") or ""
    ).strip().lower() == "official"
    report.check(GATE, "EVIDENCE_UNSCOPED", not unscoped, run_id,
                 f"{len(unscoped)} 条证据路径不含 RUN-*，无法归属到具体 run",
                 "FAIL" if official_target else "WARNING")
    if unscoped:
        _record_many(report, "EVIDENCE_UNSCOPED", "FAIL" if official_target else "WARNING",
                     unscoped, "证据路径不含 run 归属")

    # --- whole-manifest audit (informational, never blocks this run) -------
    if global_result is not None:
        historical_cross = list(global_result.get("cross_run") or [])
        historical_unscoped = list(global_result.get("unscoped") or [])
        stats["manifest_audit"] = {
            "evidence_total": len(evidence_entries),
            "cross_run": len(historical_cross),
            "unscoped": len(historical_unscoped),
            "examples": (historical_cross + historical_unscoped)[:5],
        }
        if historical_cross or historical_unscoped:
            report.add(GATE, "HISTORICAL_EVIDENCE_ANOMALY", "WARNING", "*",
                       f"全量扫描：manifest 共 {len(historical_cross)} 条跨 run 登记、"
                       f"{len(historical_unscoped)} 条无 run 归属证据；历史事实只报告不修改，"
                       "不影响本 run 判定", truncate((historical_cross + historical_unscoped)[:3]),
                       advisory=True)

    # --- per case evidence -------------------------------------------------
    evidence_index = {str(e.get("evidence_id")): e for e in evidence_entries}
    run_cases: Mapping[str, Mapping[str, Any]] = run.get("cases") or {}
    enums = enum_sets(evidence_module)
    triage: dict[str, str] = {}

    for case_id, case in run_cases.items():
        ids = [str(item) for item in as_list(case.get("evidence")) if item]
        unresolved = [item for item in ids if item not in evidence_index]
        report.check(GATE, "CASE_EVIDENCE_UNREGISTERED", not unresolved, case_id,
                     f"用例引用的证据未登记：{truncate(unresolved)}", "FAIL")
        foreign = [item for item in ids
                   if item in evidence_index and str(evidence_index[item].get("run_id")) != run_id]
        if foreign:
            report.add(GATE, "CASE_EVIDENCE_FOREIGN_RUN", "WARNING", case_id,
                       f"用例引用了其它 run 的证据：{truncate(foreign)}")

        status = str(case.get("status") or "").strip()
        if status == "passed":
            report.check(GATE, "PASSED_CASE_WITHOUT_EVIDENCE", bool(ids), case_id,
                         "passed 用例没有任何已登记证据：无法复核通过结论", "FAIL")

        for defect in case.get("defects") or []:
            if not isinstance(defect, Mapping):
                report.add(GATE, "DEFECT_OBJECT_INVALID", "FAIL", case_id, "缺陷对象不是 JSON 对象")
                continue
            defects_mod.validate_defect(report, run_id, case_id, defect, evidence_index, enums)

        if status == "failed":
            classification, detail = defects_mod.classify_failed_case(report, run_id, case_id, case)
            triage[case_id] = classification
            stats.setdefault("failed_case_triage", {})[case_id] = detail

    stats["failed_case_triage"] = stats.get("failed_case_triage", {})
    stats["unconfirmed_defects"] = sum(
        1 for case in run_cases.values() for defect in (case.get("defects") or [])
        if isinstance(defect, Mapping) and defects_mod.status_state(defect) == "unconfirmed"
    )
    stats["confirmed_defects"] = sum(
        1 for case in run_cases.values() for defect in (case.get("defects") or [])
        if isinstance(defect, Mapping) and defects_mod.status_state(defect) == "confirmed"
    )
    if run_cases:
        report.check(GATE, "CASE_REGISTRY_SCANNED", True, run_id,
                     f"扫描 {len(run_cases)} 个用例、{len(evidence_entries)} 条证据")
    return stats
