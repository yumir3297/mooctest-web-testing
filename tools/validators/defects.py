"""G3 - defect object rules and failed-case triage.

A failing test is only *evidence of a product defect* when the defect record is
complete enough for somebody else to reproduce it.  The checks here separate
three situations that are usually conflated:

``confirmed``      ``status in {open, confirmed}`` and every mandatory field is
                   present: the failure may honestly be reported as a product
                   defect (``test_verdict=FAIL``) without making the whole
                   delivery untrustworthy.
``unconfirmed``    ``status in {suspected, needs_review}``: the failure is real
                   but not yet attributed.  Delivery is allowed with a WARNING;
                   the gate never upgrades the status by itself.
``invalid``        missing mandatory fields (reproduction steps, environment,
                   evidence, ...): the failure cannot be triaged, so the result
                   is untrustworthy.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .common import Report, as_list, truncate

GATE = "G3"

REQUIRED_TEXT = ("title", "severity_rationale", "environment", "expected", "actual")
REQUIRED_LISTS = ("preconditions", "repro_steps")

CONFIRMED_STATUSES = {"open", "confirmed"}
UNCONFIRMED_STATUSES = {"suspected", "needs_review"}
EXCLUDED_STATUSES = {"not_a_defect", "fixed"}
NON_PRODUCT_FAILURE_CLASSES = {"SCRIPT", "LOCATOR", "TIMING", "DATA", "ENV"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def missing_fields(defect: Mapping[str, Any]) -> list[str]:
    missing = [name for name in REQUIRED_TEXT if not _text(defect.get(name))]
    for name in REQUIRED_LISTS:
        if not [item for item in as_list(defect.get(name)) if _text(item)]:
            missing.append(name)
    if not [item for item in as_list(defect.get("evidence")) if _text(item)]:
        missing.append("evidence")
    return missing


def status_state(defect: Mapping[str, Any]) -> str:
    status = _text(defect.get("status")).lower()
    if status in CONFIRMED_STATUSES:
        return "confirmed"
    if status in UNCONFIRMED_STATUSES:
        return "unconfirmed"
    if status in EXCLUDED_STATUSES:
        return "excluded"
    return "invalid"


def validate_defect(report: Report, run_id: str, case_id: str, defect: Mapping[str, Any],
                    evidence_index: Mapping[str, Any], enums: Mapping[str, set[str]]) -> str:
    """Validate one defect record.  Returns its triage state."""
    defect_id = _text(defect.get("defect_id")) or f"{case_id}-defect"
    subject = f"{case_id}/{defect_id}"

    severity = _text(defect.get("severity"))
    category = _text(defect.get("category"))
    status = _text(defect.get("status"))
    repro_status = _text(defect.get("repro_status"))

    report.check(GATE, "DEFECT_ENUM_INVALID", severity in enums["severity"], subject,
                 f"severity `{severity}` 不在 {sorted(enums['severity'])} 中", "FAIL")
    report.check(GATE, "DEFECT_ENUM_INVALID", category in enums["category"], subject,
                 f"category `{category}` 不在 {sorted(enums['category'])} 中", "FAIL")
    report.check(GATE, "DEFECT_ENUM_INVALID", status in enums["status"], subject,
                 f"status `{status}` 不在 {sorted(enums['status'])} 中", "FAIL")
    report.check(GATE, "DEFECT_ENUM_INVALID", repro_status in enums["repro_status"], subject,
                 f"repro_status `{repro_status}` 不在 {sorted(enums['repro_status'])} 中", "FAIL")

    missing = missing_fields(defect)
    report.check(GATE, "DEFECT_FIELD_MISSING", not missing, subject,
                 f"缺陷缺少必填字段：{', '.join(missing)}", "FAIL")

    evidence_ids = [str(item) for item in as_list(defect.get("evidence")) if _text(item)]
    unresolved = [item for item in evidence_ids if item not in evidence_index]
    report.check(GATE, "DEFECT_EVIDENCE_UNRESOLVED", not unresolved, subject,
                 f"缺陷引用的证据未登记：{truncate(unresolved)}", "FAIL")

    state = status_state(defect)
    if state == "unconfirmed":
        report.add(GATE, "DEFECT_STATUS_UNCONFIRMED", "WARNING", subject,
                   f"缺陷状态为 `{status}`：允许交付，但报告中必须标注结论不确定")
    if state == "invalid":
        report.add(GATE, "DEFECT_STATUS_INVALID", "FAIL", subject,
                   f"缺陷状态 `{status}` 不属于任何可交付区间")
    return "invalid" if missing else state


def classify_failed_case(report: Report, run_id: str, case_id: str,
                         case: Mapping[str, Any]) -> tuple[str, str]:
    """Triage a ``failed`` case.  Returns ``(classification, detail)``.

    ``classification`` is one of ``confirmed`` / ``unconfirmed`` / ``untriaged``.
    """
    defect_states = [
        status_state(defect)
        for defect in (case.get("defects") or [])
        if isinstance(defect, Mapping)
    ]
    if "confirmed" in defect_states:
        return "confirmed", "已登记确认缺陷"

    if "unconfirmed" in defect_states:
        return "unconfirmed", "缺陷状态待复核"

    meta = case.get("meta") or {}
    failure_class = _text(meta.get("failure_class")).upper()
    if not failure_class:
        report.add(GATE, "FAILED_CASE_UNTRIAGED", "FAIL", case_id,
                   "用例 failed 既没有缺陷记录，也没有 failure_class：无法区分产品缺陷与脚本问题")
        return "untriaged", "无缺陷且无 failure_class"

    if failure_class in NON_PRODUCT_FAILURE_CLASSES:
        report.add(GATE, "FAILED_CASE_CAUSE_NOT_PRODUCT", "FAIL", case_id,
                   f"失败分类为 {failure_class}：属于脚本/定位/时序/环境问题，测试成果不可信")
        return "untriaged", f"failure_class={failure_class}（非产品原因）"

    report.add(GATE, "FAILED_CASE_WITHOUT_DEFECT", "FAIL", case_id,
               f"失败分类为 {failure_class}，但没有登记缺陷：结论不可复核")
    return "untriaged", f"failure_class={failure_class}（缺缺陷记录）"


def has_complete_confirmed_defect(case: Mapping[str, Any]) -> bool:
    for defect in case.get("defects") or []:
        if isinstance(defect, Mapping) and status_state(defect) == "confirmed" and not missing_fields(defect):
            return True
    return False
