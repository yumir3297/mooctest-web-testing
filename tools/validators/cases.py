"""G1 - requirement traceability and test case table checks.

Machine input is the CSV case table described by ``docs/CONTRACTS.md`` §3.  The
reader maps the documented aliases (``requirement`` / ``precondition`` /
``data`` / ``evidence``) plus a few legacy spellings, so old tables stay
readable without rewriting them.

Severity policy
---------------
* A missing *value* in a column that exists is a FAIL for the core oracle
  fields (``case_id`` / ``title`` / ``priority`` / ``requirement_ids`` /
  ``expected`` / ``status``) and a WARNING for hygiene fields
  (``preconditions`` / ``test_data`` / ``method`` / ``case_type``).
* A whole *column* that is absent means the table was written against an older
  contract.  That is reported as a WARNING so a historical table is not
  retro-actively declared invalid, but the gate says loudly that the check
  could not be performed.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

from .common import Report, slug, sort_key, truncate

GATE = "G1"

CASE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*-[A-Za-z0-9]+-\d{3}$")

CANONICAL_COLUMNS: tuple[str, ...] = (
    "case_id", "title", "priority", "requirement_ids", "case_type", "method",
    "preconditions", "test_data", "steps", "expected", "actual", "status",
    "automation", "evidence_required", "executed_in_run", "notes",
)

COLUMN_ALIASES: dict[str, str] = {
    # contract §3
    "requirement": "requirement_ids",
    "precondition": "preconditions",
    "data": "test_data",
    "evidence": "evidence_required",
    # common legacy / spelling variants
    "requirement_id": "requirement_ids",
    "requirements": "requirement_ids",
    "req": "requirement_ids",
    "req_ids": "requirement_ids",
    "pre_conditions": "preconditions",
    "pre-conditions": "preconditions",
    "testdata": "test_data",
    "input_data": "test_data",
    "test_steps": "steps",
    "step": "steps",
    "expected_result": "expected",
    "expect": "expected",
    "expectation": "expected",
    "actual_result": "actual",
    "caseid": "case_id",
    "case": "case_id",
    "id": "case_id",
    "类型": "case_type",
    "方法": "method",
    "优先级": "priority",
    "标题": "title",
    "预期结果": "expected",
    "预期": "expected",
    "步骤": "steps",
    "前置条件": "preconditions",
    "自动化": "automation",
    "状态": "status",
    "需求": "requirement_ids",
}

CASE_TYPES = {"positive", "negative", "boundary", "state", "combination", "nonfunctional"}
COVERAGE_TYPES = ("positive", "negative", "boundary")
PRIORITIES = {"P0", "P1", "P2", "P3"}

# Deliberately small: only phrases that cannot be judged by a third party.
DEFAULT_VAGUE_EXPECTED: tuple[str, ...] = (
    "正常显示", "显示正常", "功能正常", "正常", "正确", "成功", "无异常", "无错误",
    "符合预期", "工作正常", "正常返回", "一切正常",
    "ok", "works", "worksfine", "asexpected", "success", "valid", "pass", "fine",
)


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #
def canonical_column(name: str) -> str:
    key = str(name or "").strip().lower().replace(" ", "_").replace("-", "_")
    return COLUMN_ALIASES.get(key, key)


def load_case_files(paths: Sequence[Path]) -> tuple[list[dict[str, Any]], set[str], list[tuple[str, str, str]]]:
    """Read every CSV, returning ``(rows, columns_seen, file_errors)``."""
    rows: list[dict[str, Any]] = []
    columns: set[str] = set()
    errors: list[tuple[str, str, str]] = []
    for path in paths:
        path = Path(path)
        if not path.is_file():
            errors.append(("CASES_FILE_MISSING", str(path), "用例表文件不存在"))
            continue
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                header = [(h or "").strip() for h in (reader.fieldnames or [])]
                mapping = {h: canonical_column(h) for h in header}
                columns.update(mapping.values())
                for line_no, raw in enumerate(reader, start=2):
                    record: dict[str, Any] = {}
                    for key, value in raw.items():
                        if key is None:
                            continue
                        record[mapping.get(key, canonical_column(key))] = (value or "").strip()
                    if not any(str(v).strip() for v in record.values()):
                        continue
                    record["_source"] = str(path)
                    record["_line"] = line_no
                    rows.append(record)
        except (OSError, csv.Error) as exc:
            errors.append(("CASES_FILE_INVALID", str(path), f"{type(exc).__name__}: {exc}"))
    return rows, columns, errors


def split_requirements(text: str) -> list[str]:
    parts = re.split(r"[;,/|、>\n]+|\s{2,}", str(text or ""))
    return [p.strip() for p in parts if p.strip()]


def split_steps(text: str) -> list[str]:
    """Split a steps cell into individual steps.

    Recognises ``1.`` / ``2)`` style numbering, newlines and ``;`` ``；`` ``,``
    ``，`` separators.  Numbering markers are separators, not content.
    """
    value = str(text or "").strip()
    if not value:
        return []
    normalised = re.sub(r"(?:^|[\s;；,，])\(?(\d{1,2})[.、)．]\s*", "\n", value)
    parts = re.split(r"[\n;；,，]+", normalised)
    return [p.strip(" .-•*\t") for p in parts if p.strip(" .-•*\t")]


def _normalise_text(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", str(text or "")).lower()


def is_vague_expected(text: str, vague_words: Iterable[str] = DEFAULT_VAGUE_EXPECTED) -> bool:
    value = _normalise_text(text)
    if not value:
        return True
    return value in {_normalise_text(w) for w in vague_words}


def load_requirements(path: Path) -> tuple[set[str], list[str]]:
    """Read a requirement list (CSV / JSON / plain text)."""
    ids: set[str] = set()
    problems: list[str] = []
    if not path.is_file():
        return ids, [f"requirements file not found: {path}"]
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except Exception as exc:  # pragma: no cover - defensive
            return ids, [f"requirements JSON is not parseable: {exc}"]
        items = payload.get("requirements", []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return ids, ["requirements JSON must be a list or contain a 'requirements' list"]
        for item in items:
            if isinstance(item, str):
                value = item.strip()
            elif isinstance(item, dict):
                value = str(item.get("id") or item.get("requirement_id") or item.get("req_id") or "").strip()
            else:
                value = ""
            if value:
                ids.add(value)
        if not ids:
            problems.append("requirements JSON contains no requirement ids")
        return ids, problems
    if path.suffix.lower() == ".csv":
        reader = csv.DictReader(text.splitlines())
        header = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
        column = next((h for h in header if h in ("requirement_id", "id", "req_id", "requirement", "需求编号")), None)
        if column is None:
            problems.append("requirements CSV has no requirement_id column")
            return ids, problems
        for raw in reader:
            value = str(raw.get(column) or "").strip()
            if value:
                ids.add(value)
        return ids, problems
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = re.split(r"[,;\t ]", line)[0].strip()
        if token:
            ids.add(token)
    return ids, problems


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def validate(report: Report, rows: Sequence[dict[str, Any]], columns: set[str],
             file_errors: Sequence[tuple[str, str, str]] = (),
             requirements: set[str] | None = None,
             requirements_error: str | None = None,
             vague_words: Iterable[str] = DEFAULT_VAGUE_EXPECTED) -> None:
    for code, subject, message in file_errors:
        report.check(GATE, code, False, subject, message, severity="FAIL")

    report.check(GATE, "CASES_EMPTY", bool(rows), "cases", "用例集为空：没有任何用例行，无法证明覆盖", "FAIL")

    for column in ("case_type", "method"):
        if column not in columns:
            report.add(GATE, f"CASE_{column.upper()}_COLUMN_ABSENT", "WARNING", column,
                       f"用例表没有 `{column}` 列：该维度无法核验（旧版表结构）")
    if "requirement_ids" not in columns:
        report.add(GATE, "CASE_REQUIREMENT_COLUMN_ABSENT", "WARNING", "requirement_ids",
                   "用例表没有需求列：需求追溯无法核验")

    seen_ids: dict[str, dict[str, Any]] = {}
    seen_content: dict[tuple[str, str, str], str] = {}
    types_seen: set[str] = set()
    covered_requirements: set[str] = set()

    for row in rows:
        case_id = str(row.get("case_id") or "").strip()
        subject = case_id or f"{Path(str(row.get('_source'))).name}:{row.get('_line')}"

        # --- identity ------------------------------------------------------
        if not case_id:
            report.check(GATE, "CASE_ID_MISSING", False, subject, "缺少 case_id", "FAIL")
        else:
            report.check(GATE, "CASE_ID_INVALID", bool(CASE_ID_RE.match(case_id)), subject,
                         f"case_id `{case_id}` 不符合 ^[A-Za-z][A-Za-z0-9]*-[A-Za-z0-9]+-\\d{{3}}$", "FAIL")
            prior = seen_ids.get(case_id)
            if prior is None:
                seen_ids[case_id] = row
            else:
                same_file = prior.get("_source") == row.get("_source")
                report.check(GATE, "CASE_ID_DUPLICATE", False, case_id,
                             f"case_id 重复：{Path(str(row.get('_source'))).name}:{row.get('_line')} 与 "
                             f"{Path(str(prior.get('_source'))).name}:{prior.get('_line')}",
                             "FAIL" if same_file else "WARNING")

        # --- required values ----------------------------------------------
        report.check(GATE, "CASE_TITLE_MISSING", bool(str(row.get("title") or "").strip()),
                     subject, "缺少 title", "FAIL")

        priority = str(row.get("priority") or "").strip()
        report.check(GATE, "CASE_PRIORITY_INVALID", priority in PRIORITIES, subject,
                     f"priority `{priority}` 不在 {sorted(PRIORITIES)} 中", "FAIL")

        req_text = str(row.get("requirement_ids") or "").strip()
        req_ids = split_requirements(req_text)
        report.check(GATE, "CASE_REQUIREMENT_MISSING", bool(req_ids), subject,
                     "缺少 requirement_ids：用例没有需求追溯", "FAIL")
        covered_requirements.update(req_ids)

        case_type = str(row.get("case_type") or "").strip().lower()
        if "case_type" in columns:
            report.check(GATE, "CASE_CASE_TYPE_INVALID", case_type in CASE_TYPES, subject,
                         f"case_type `{case_type}` 不在 {sorted(CASE_TYPES)} 中", "FAIL")
            if case_type:
                types_seen.add(case_type)

        method = str(row.get("method") or "").strip()
        if "method" in columns:
            report.check(GATE, "CASE_METHOD_MISSING", bool(method), subject,
                         "缺少 test design method", "FAIL")

        preconditions = str(row.get("preconditions") or "").strip()
        if "preconditions" in columns:
            report.check(GATE, "CASE_PRECONDITION_MISSING", bool(preconditions), subject,
                         "缺少 preconditions", "WARNING")

        test_data = str(row.get("test_data") or "").strip()
        if "test_data" in columns:
            report.check(GATE, "CASE_TEST_DATA_EMPTY", bool(test_data), subject,
                         "test_data 为空（如确实无数据请输入“无”）", "WARNING")

        steps = split_steps(str(row.get("steps") or ""))
        report.check(GATE, "CASE_STEPS_TOO_FEW", len(steps) >= 2, subject,
                     f"steps 只拆出 {len(steps)} 步，至少需要 2 步", "WARNING")

        expected = str(row.get("expected") or "").strip()
        report.check(GATE, "CASE_EXPECTED_MISSING", bool(expected), subject,
                     "缺少 expected：没有可判定的预期结果", "FAIL")
        if expected:
            report.check(GATE, "CASE_EXPECTED_VAGUE", not is_vague_expected(expected, vague_words),
                         subject, f"expected `{expected}` 不可判定（只有“正常/成功”类描述）", "FAIL")

        status = str(row.get("status") or "").strip()
        report.check(GATE, "CASE_STATUS_MISSING", bool(status), subject, "缺少 status", "FAIL")

        # --- duplicate content --------------------------------------------
        signature = (sort_key(str(row.get("title") or "")),
                     sort_key(" ".join(steps)),
                     sort_key(expected))
        if all(signature):
            if signature in seen_content:
                report.check(GATE, "CASE_DUPLICATE_CONTENT", False, subject,
                             f"与 {seen_content[signature]} 的 title+steps+expected 完全相同", "FAIL")
            else:
                seen_content[signature] = subject

    # --- coverage ---------------------------------------------------------- #
    if "case_type" in columns and types_seen:
        missing = [t for t in COVERAGE_TYPES if t not in types_seen]
        report.check(GATE, "CASE_TYPE_COVERAGE_MISSING", not missing, "case_type",
                     f"缺少用例类型覆盖：{', '.join(missing)}", "FAIL")
        report.check(GATE, "CASE_TYPE_COVERAGE_UNKNOWN", True, "case_type", "已核验 positive/negative/boundary")

    # --- requirement traceability -----------------------------------------
    if requirements is None:
        report.add(GATE, "REQUIREMENTS_UNVERIFIED", "WARNING", "requirements",
                   "未提供 --requirements 需求清单：悬空需求与需求未覆盖检查已跳过"
                   + (f"（{requirements_error}）" if requirements_error else ""))
    else:
        dangling = sorted(covered_requirements - requirements)
        report.check(GATE, "REQUIREMENT_UNKNOWN", not dangling, "requirements",
                     f"用例引用的需求不在需求清单中：{truncate(dangling)}", "FAIL")
        uncovered = sorted(requirements - covered_requirements)
        report.check(GATE, "REQUIREMENT_NOT_COVERED", not uncovered, "requirements",
                     f"需求没有任何用例覆盖：{truncate(uncovered)}", "FAIL")

    # --- summary statistics ------------------------------------------------
    if rows:
        ids = [str(r.get("case_id") or "").strip() for r in rows]
        report.check(GATE, "CASE_COUNT_RECORDED", True, "cases",
                     f"读取 {len(rows)} 条用例（{len(set(ids))} 个唯一 ID，"
                     f"类型 {sorted(types_seen) or 'unknown'}）")


def summary_of(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    ids = [str(r.get("case_id") or "").strip() for r in rows]
    types: dict[str, int] = {}
    for row in rows:
        key = str(row.get("case_type") or "unknown").strip().lower() or "unknown"
        types[key] = types.get(key, 0) + 1
    return {
        "rows": len(rows),
        "unique_case_ids": len({i for i in ids if i}),
        "case_types": types,
        "sources": sorted({str(r.get("_source")) for r in rows}),
    }
