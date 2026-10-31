#!/usr/bin/env python3
"""Build and verify the internal-rehearsal submission package for one run.

Layout (``docs/CONTRACTS.md`` §5)::

    submission/RUN-X/
      test-cases.xlsx
      test-code/
      screenshots/            + index.csv
      reports/                report.md/html/json, junit.xml, junit-summary.json, pytest-console.log
      manifest.json
      submission.zip

``manifest.json`` is schema 1.0, records ``path/sha256/size_bytes/case_id/source``
per file and always declares ``official_format_confirmed: false``: the 2026
official submission format has not been confirmed, so this package is an
internal rehearsal artefact only.

The zip is reproducible: entries are sorted, timestamps are pinned to
1980-01-01, and every payload file is byte-stable across rebuilds. Rebuilding
the same run twice must yield the same zip sha256.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import report_schema as rs  # noqa: E402

ROOT = rs.ROOT
PACKAGE_VERSION = "1.0"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
FIXED_XLSX_TIME = datetime(2000, 1, 1, 0, 0, 0)
REQUIRED_DIRS = ("test-code", "screenshots", "reports")
REPORT_FILES = ("report.md", "report.html", "report.json")
NOT_IMPLEMENTED_MARKER = "未实现"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _sha256(path: Path) -> str:
    return rs.sha256_file(path)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _rel(path: Path) -> str:
    return rs.rel_posix(path, ROOT)


def _clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _copy_file(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _iter_files(base: Path, exclude_dirs: tuple[str, ...] = ("__pycache__",)) -> list[Path]:
    out = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in exclude_dirs for part in path.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        out.append(path)
    return out


def _normalise_zip(path: Path, pin_core_properties: bool = False) -> None:
    """Rewrite a zip with pinned timestamps so its bytes are reproducible."""
    with zipfile.ZipFile(path) as zf:
        entries = [(info.filename, zf.read(info.filename), info.compress_type)
                   for info in zf.infolist()]
    fixed_stamp = b"2000-01-01T00:00:00Z"
    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data, compress_type in sorted(entries, key=lambda item: item[0]):
            if pin_core_properties and name == "docProps/core.xml":
                text = data.decode("utf-8")
                for tag in ("created", "modified"):
                    text = re.sub(
                        rf"(<dcterms:{tag}[^>]*>)[^<]*(</dcterms:{tag}>)",
                        lambda m: m.group(1).encode().decode() + fixed_stamp.decode() + m.group(2),
                        text)
                data = text.encode("utf-8")
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.compress_type = compress_type if compress_type else zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0o644 << 16
            info.internal_attr = 0
            zf.writestr(info, data)
    os.replace(tmp, path)


def _build_stable_zip(root: Path, rel_paths: list[str], zip_path: Path) -> None:
    tmp = zip_path.with_name(zip_path.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(rel_paths):
            data = (root / rel).read_bytes()
            info = zipfile.ZipInfo(rel, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0o644 << 16
            info.internal_attr = 0
            zf.writestr(info, data)
    os.replace(tmp, zip_path)


def _display_width(value: Any) -> int:
    text = "" if value is None else str(value)
    width = 0
    for ch in text:
        width += 2 if ord(ch) > 127 else 1
    return width


# --------------------------------------------------------------------------- #
# case table resolution
# --------------------------------------------------------------------------- #
def _steps_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"{i}. {s}" for i, s in enumerate(value, 1))
    return str(value or "")


def _synthesised_rows(data: dict[str, Any], run: dict[str, Any], run_id: str,
                      junit: dict[str, Any] | None) -> list[dict[str, str]]:
    junit_by_name = {c.get("name"): c for c in (junit or {}).get("cases", []) if c.get("name")}
    rows: list[dict[str, str]] = []
    for cid, case in sorted((run.get("cases") or {}).items()):
        meta = dict(case.get("meta") or {})
        assertions = list(case.get("assertions") or [])
        expected = rs.classify_case_expected(case.get("expected"), len(assertions))
        actual = rs.classify_case_actual(case.get("actual"), assertions)
        junit_entry = junit_by_name.get(case.get("title") or "")
        automation = ""
        if junit_entry:
            classname = str(junit_entry.get("classname") or "").replace(".", "/")
            if classname and junit_entry.get("name"):
                automation = f"{classname}.py::{junit_entry['name']}"
        row = {
            "case_id": cid,
            "title": str(case.get("title") or cid),
            "priority": str(meta.get("priority") or ""),
            "requirement_ids": str(meta.get("requirement_ids") or ""),
            "case_type": str(meta.get("case_type") or ""),
            "method": str(meta.get("method") or ""),
            "preconditions": "",
            "test_data": "",
            "steps": _steps_text(case.get("steps") or []),
            "expected": expected["value"] or (f"见断言明细（{len(assertions)} 条断言）" if assertions else ""),
            "actual": actual["value"] or (f"见断言明细（{len(assertions)} 条断言）" if assertions else ""),
            "status": str(case.get("status") or "not-run"),
            "automation": automation,
            "evidence_required": "",
            "executed_in_run": run_id,
            "notes": "用例表由 manifest 合成：本运行没有 executed_in_run 匹配的 CSV",
        }
        rows.append(row)
    return rows


def _resolve_case_table(run_id: str, data: dict[str, Any], run: dict[str, Any],
                        cases_path: Path | None, reports_root: Path) -> dict[str, Any]:
    if cases_path is not None:
        rows = rs.read_case_csv(cases_path)
        return {"rows": rows, "path": cases_path, "source": "explicit"}
    found = rs.find_run_case_table(run_id, reports_root)
    if found["found"]:
        return {"rows": found["rows"], "path": found["path"], "source": "run-scoped"}
    junit = None
    summary = reports_root / "executions" / run_id / "junit-summary.json"
    if summary.is_file():
        try:
            junit = rs.json_load(summary)
        except Exception:
            junit = None
    return {"rows": _synthesised_rows(data, run, run_id, junit), "path": None,
            "source": "synthesised-from-manifest"}


# --------------------------------------------------------------------------- #
# xlsx
# --------------------------------------------------------------------------- #
def _write_xlsx(path: Path, rows: list[dict[str, str]], info: dict[str, str]) -> None:
    from openpyxl import Workbook
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.properties.creator = "mooctest-web-testing package_submission"
    wb.properties.lastModifiedBy = "mooctest-web-testing package_submission"
    wb.properties.created = FIXED_XLSX_TIME
    wb.properties.modified = FIXED_XLSX_TIME

    ws = wb.active
    ws.title = "test-cases"
    columns = list(rs.CANONICAL_CASE_COLUMNS)
    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="D9E1F2")
    for idx, name in enumerate(columns, 1):
        cell = ws.cell(row=1, column=idx, value=name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for r_idx, row in enumerate(rows, 2):
        for c_idx, name in enumerate(columns, 1):
            value = row.get(name, "")
            cell = ws.cell(row=r_idx, column=c_idx, value=value if value != "" else None)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{max(len(rows) + 1, 1)}"
    for c_idx, name in enumerate(columns, 1):
        longest = _display_width(name)
        for row in rows:
            longest = max(longest, min(_display_width(row.get(name, "")), 120))
        ws.column_dimensions[get_column_letter(c_idx)].width = min(max(10, longest + 2), 60)

    status_col = get_column_letter(columns.index("status") + 1)
    last_row = max(len(rows) + 1, 2)
    rng = f"{status_col}2:{status_col}{last_row}"
    green = PatternFill("solid", fgColor="C6EFCE")
    red = PatternFill("solid", fgColor="FFC7CE")
    gray = PatternFill("solid", fgColor="D9D9D9")
    amber = PatternFill("solid", fgColor="FFEB9C")
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'ISNUMBER(SEARCH("passed",{status_col}2))'], fill=green, stopIfTrue=False))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'ISNUMBER(SEARCH("failed",{status_col}2))'], fill=red, stopIfTrue=False))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'ISNUMBER(SEARCH("xfailed",{status_col}2))'], fill=amber, stopIfTrue=False))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'OR(ISNUMBER(SEARCH("未执行",{status_col}2)),'
                 f'ISNUMBER(SEARCH("not-run",{status_col}2)),'
                 f'ISNUMBER(SEARCH("skipped",{status_col}2)))'], fill=gray, stopIfTrue=False))

    info_ws = wb.create_sheet("run-info")
    info_ws.cell(row=1, column=1, value="field").font = header_font
    info_ws.cell(row=1, column=2, value="value").font = header_font
    for r_idx, (key, value) in enumerate(info.items(), 2):
        info_ws.cell(row=r_idx, column=1, value=key)
        info_ws.cell(row=r_idx, column=2, value=value)
    info_ws.column_dimensions["A"].width = 32
    info_ws.column_dimensions["B"].width = 90

    wb.save(path)
    _normalise_zip(path, pin_core_properties=True)


def _read_xlsx(path: Path) -> dict[str, Any]:
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return {"header": [], "rows": 0, "case_ids": []}
    header = [str(x) if x is not None else "" for x in rows[0]]
    if "case_id" not in header:
        return {"header": header, "rows": max(len(rows) - 1, 0), "case_ids": []}
    idx = header.index("case_id")
    case_ids = [str(r[idx]) for r in rows[1:] if len(r) > idx and r[idx] not in (None, "")]
    return {"header": header, "rows": len(case_ids), "case_ids": case_ids}


# --------------------------------------------------------------------------- #
# package build
# --------------------------------------------------------------------------- #
def _automation_path(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    file_part = text.split("::", 1)[0].strip()
    if not file_part:
        return ""
    if file_part.endswith(".py"):
        return file_part.replace("\\", "/")
    return (file_part.replace(".", "/") + ".py").lstrip("/")


def _copy_test_code(pkg: Path, automation_values: list[str], project_root: Path) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    base = pkg / "test-code"
    base.mkdir(parents=True, exist_ok=True)

    sources: list[Path] = []
    tests_conftest = project_root / "tests" / "conftest.py"
    if tests_conftest.is_file():
        sources.append(tests_conftest)
    pages = project_root / "tests" / "pages"
    if pages.is_dir():
        sources.extend(_iter_files(pages))
    for name in ("pytest.ini", "requirements.txt"):
        candidate = project_root / name
        if candidate.is_file():
            sources.append(candidate)
    # `tests/conftest.py` imports the evidence manager from `tools/`. Shipping
    # those two modules keeps the package's test code runnable outside the
    # repository.
    for name in ("evidence.py", "versioning.py"):
        candidate = project_root / "tools" / name
        if candidate.is_file():
            sources.append(candidate)
    for value in automation_values:
        rel = _automation_path(value)
        if not rel:
            continue
        candidate = project_root / rel
        if candidate.is_file():
            sources.append(candidate)
            # A generated suite is self-contained: the test module imports a
            # sibling Page Object (page_*.py) from the same directory. Packaging
            # only the test file would produce code that cannot run on its own.
            try:
                parent_rel = candidate.parent.relative_to(project_root)
            except ValueError:
                continue
            if any(part == "generated" for part in parent_rel.parts):
                sources.extend(p for p in _iter_files(candidate.parent) if p.suffix == ".py")

    seen: set[str] = set()
    for src in sources:
        try:
            rel = src.relative_to(project_root)
        except ValueError:
            continue
        rel_posix = rel.as_posix()
        if rel_posix in seen or "__pycache__" in rel.parts or src.suffix == ".pyc":
            continue
        seen.add(rel_posix)
        dst = base / rel
        _copy_file(src, dst)
        copied.append({"path": rel_posix, "source": f"project:{rel_posix}"})
    return copied


def _copy_screenshots(pkg: Path, evidence_entries: list[dict[str, Any]],
                      project_root: Path = ROOT) -> list[dict[str, str]]:
    folder = pkg / "screenshots"
    folder.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, str]] = []
    used: set[str] = set()
    for item in sorted(evidence_entries, key=lambda e: (str(e.get("case_id")), str(e.get("evidence_id")))):
        src = Path(project_root) / item["path"]
        if not src.is_file():
            continue
        name = Path(item["path"]).name
        if name in used:
            name = f"{Path(name).stem}__{item['evidence_id']}{Path(name).suffix}"
        used.add(name)
        dst = folder / name
        _copy_file(src, dst)
        index.append({
            "case_id": str(item.get("case_id") or ""),
            "evidence_id": str(item.get("evidence_id") or ""),
            "kind": str(item.get("kind") or ""),
            "file": name,
            "sha256": _sha256(dst),
            "caption": str(item.get("caption") or ""),
        })
    with (folder / "index.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "evidence_id", "kind", "file", "sha256", "caption"])
        writer.writeheader()
        writer.writerows(index)
    return index


def _copy_reports(pkg: Path, report_dir: Path, exec_dir: Path, run_id: str, project_root: Path,
                  force: bool = False) -> dict[str, Any]:
    """Populate ``reports/`` without silently overwriting a freshly generated report.

    Rule: a report file already present in the package wins; missing files are
    copied from ``--report-dir`` first, then from ``reports/executions/<run>``.
    """
    folder = pkg / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    sources: dict[str, str] = {}
    search_dirs = [report_dir]
    if exec_dir.resolve() != report_dir.resolve():
        search_dirs.append(exec_dir)

    for name in REPORT_FILES:
        dst = folder / name
        if dst.is_file() and not force:
            copied.append(name)
            sources[name] = "package"
            continue
        for base in search_dirs:
            src = base / name
            if src.is_file() and src.resolve() != dst.resolve():
                _copy_file(src, dst)
                copied.append(name)
                sources[name] = str(base)
                break

    junit_summary = folder / "junit-summary.json"
    if not junit_summary.is_file():
        for base in search_dirs:
            src = base / "junit-summary.json"
            if src.is_file():
                _copy_file(src, junit_summary)
                sources["junit-summary.json"] = str(base)
                break
    junit_data: dict[str, Any] = {}
    if junit_summary.is_file():
        copied.append("junit-summary.json")
        sources.setdefault("junit-summary.json", "package")
        try:
            junit_data = rs.json_load(junit_summary)
        except Exception:
            junit_data = {}

    for key, fallback in (("junit", "junit.xml"), ("console_log", "pytest-console.log")):
        dst = folder / fallback
        if dst.is_file():
            copied.append(fallback)
            sources.setdefault(fallback, "package")
            continue
        candidate: Path | None = None
        raw = junit_data.get(key)
        if raw:
            p = Path(str(raw))
            candidate = p if p.is_absolute() else project_root / p
        if candidate is None or not candidate.is_file():
            for base in search_dirs:
                alt = base / fallback
                if alt.is_file():
                    candidate = alt
                    break
        if candidate is not None and candidate.is_file():
            _copy_file(candidate, dst)
            copied.append(fallback)
            sources[fallback] = str(candidate)

    return {"copied": sorted(set(copied)), "sources": sources,
            "report_dir": str(report_dir), "exec_dir": str(exec_dir)}


def _readme_text(run_id: str, info: dict[str, str], case_count: int) -> str:
    return "\n".join([
        f"# {run_id} 测试交付包",
        "",
        f"**{rs.OFFICIAL_FORMAT_NOTE}。**",
        "",
        "本目录由 `tools/package_submission.py` 生成，用于内部演练与交叉复核，"
        "不声明符合任何官方提交格式（`official_format_confirmed: false`）。",
        "",
        "## 目录",
        "",
        "- `test-cases.xlsx`：用例表（sheet `test-cases` 为契约列；sheet `run-info` 为运行信息）",
        "- `test-code/`：执行本批用例所需的最小代码（conftest、页面对象、被引用测试文件、pytest.ini、requirements.txt）",
        "- `screenshots/`：本运行登记的全部图片证据，`index.csv` 记录 case_id/evidence_id/kind/文件/sha256/说明",
        "- `reports/`：report.md、report.html、report.json、junit.xml、junit-summary.json、pytest-console.log",
        "- `manifest.json`：逐文件 sha256 与大小（schema 1.0）",
        "- `submission.zip`：上述载荷的稳定压缩包（条目排序、时间戳固定 1980-01-01）",
        "",
        "## 运行信息",
        "",
        f"- 目标：{info.get('target', '')}",
        f"- 用例数：{case_count}",
        f"- 用例表来源：{info.get('case_table_source', '')}",
        "",
        "## 校验",
        "",
        "```text",
        f"python tools/package_submission.py --verify submission/{run_id} --json",
        "```",
        "",
        "## 限制",
        "",
        "- 官方提交格式未确认；目录名、文件命名与 xlsx 列定义均为本项目内部约定。",
        "- 报告中的图片链接指向项目树（`evidence/…`）；包内独立截图见 `screenshots/`。",
        "- zip 只包含载荷文件，`manifest.json` 与 `submission.zip` 同级存放，压缩包内不含二者。",
        "",
    ])


def build_package(run_id: str, *, cases_path: Path | None = None, report_dir: Path | None = None,
                  out_root: Path | None = None, project_root: Path = ROOT,
                  manifest_path: Path | None = None, force_reports: bool = False) -> dict[str, Any]:
    manifest_path = manifest_path or project_root / "evidence" / "manifest.json"
    reports_root = project_root / "reports"
    out_root = out_root or project_root / "submission"
    report_dir = report_dir or reports_root / "executions" / run_id

    data = rs.json_load(manifest_path)
    if run_id not in data.get("runs", {}):
        raise KeyError(f"run not found: {run_id}")
    run = data["runs"][run_id]

    pkg = out_root / run_id
    pkg.mkdir(parents=True, exist_ok=True)
    for name in ("test-code", "screenshots"):
        if (pkg / name).exists():
            shutil.rmtree(pkg / name)
    for name in ("manifest.json", "submission.zip"):
        (pkg / name).unlink(missing_ok=True)

    table = _resolve_case_table(run_id, data, run, cases_path, reports_root)
    rows = table["rows"]
    automation_values = [str(r.get("automation") or "") for r in rows]

    report_info = _copy_reports(pkg, report_dir, reports_root / "executions" / run_id, run_id,
                                project_root, force=force_reports)
    copied_code = _copy_test_code(pkg, automation_values, project_root)

    evidence_entries = [e for e in data.get("evidence", []) if e.get("run_id") == run_id]
    image_entries = [e for e in evidence_entries
                     if rs.is_image_evidence(e.get("kind"), e.get("path"))]
    screenshot_index = _copy_screenshots(pkg, image_entries, project_root)

    generated_at = _now_iso()
    tool_versions = rs.local_tool_versions()
    tool_versions["package_submission"] = PACKAGE_VERSION
    info = {
        "run_id": run_id,
        "target": str(run.get("target") or ""),
        "case_table_source": table["source"],
        "case_table_path": str(table["path"]) if table["path"] else "",
        "official_format_confirmed": "false",
        "official_format_note": rs.OFFICIAL_FORMAT_NOTE,
        "run_status": str(run.get("status") or ""),
    }
    _write_xlsx(pkg / "test-cases.xlsx", rows, info)
    (pkg / "README.md").write_text(_readme_text(run_id, info, len(rows)), encoding="utf-8")

    files: list[dict[str, Any]] = []
    code_case_ids: dict[str, str | None] = {}
    for row in rows:
        rel = _automation_path(row.get("automation") or "")
        if rel:
            code_case_ids[f"test-code/{rel}"] = str(row.get("case_id") or "")
    screenshot_by_name = {item["file"]: item for item in screenshot_index}

    for path in _iter_files(pkg):
        rel = path.relative_to(pkg).as_posix()
        if rel in {"manifest.json", "submission.zip"}:
            continue
        case_id: str | None = None
        source = "generated"
        if rel.startswith("screenshots/"):
            source = "evidence"
            case_id = screenshot_by_name.get(path.name, {}).get("case_id")
        elif rel.startswith("test-code/"):
            source = "project"
            case_id = code_case_ids.get(rel)
        elif rel.startswith("reports/"):
            source = "reports"
        files.append({
            "path": rel,
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
            "case_id": case_id,
            "source": source,
        })
    files.sort(key=lambda item: item["path"])

    manifest = {
        "schema_version": rs.PACKAGE_SCHEMA_VERSION,
        "package_kind": rs.PACKAGE_KIND,
        "official_format_confirmed": rs.OFFICIAL_FORMAT_CONFIRMED,
        "official_format_note": rs.OFFICIAL_FORMAT_NOTE,
        "generator": {"tool": "tools/package_submission.py", "version": PACKAGE_VERSION},
        "run_id": run_id,
        "generated_at": generated_at,
        "target": info["target"],
        "tool_versions": tool_versions,
        "case_count": len(rows),
        "case_table": {"source": table["source"],
                       "path": str(table["path"]) if table["path"] else None},
        "counts": {
            "files": len(files),
            "test_code": len(copied_code),
            "screenshots": len(screenshot_index),
            "reports": len(report_info["copied"]),
        },
        "files": files,
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")

    _build_stable_zip(pkg, [item["path"] for item in files], pkg / "submission.zip")
    zip_path = pkg / "submission.zip"
    manifest["zip"] = {"path": "submission.zip", "sha256": _sha256(zip_path),
                       "size_bytes": zip_path.stat().st_size,
                       "entries": len(files), "entry_time": "1980-01-01T00:00:00"}
    (pkg / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")

    return {
        "run_id": run_id,
        "package_dir": str(pkg),
        "official_format_confirmed": rs.OFFICIAL_FORMAT_CONFIRMED,
        "official_format_note": rs.OFFICIAL_FORMAT_NOTE,
        "case_count": len(rows),
        "case_table": {"source": table["source"],
                       "path": str(table["path"]) if table["path"] else None},
        "counts": manifest["counts"],
        "test_code_files": [item["path"] for item in copied_code],
        "screenshots": len(screenshot_index),
        "reports": report_info,
        "manifest": str(pkg / "manifest.json"),
        "zip": {"path": str(zip_path), "sha256": manifest["zip"]["sha256"],
                "size_bytes": manifest["zip"]["size_bytes"], "entries": len(files)},
        "generated_at": generated_at,
        "exit_code": 0,
    }


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #
def verify_package(pkg: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    checks: list[dict[str, Any]] = []
    pkg = pkg.resolve()

    def add(code: str, severity: str, message: str, detail: str = "") -> None:
        findings.append({"code": code, "severity": severity, "message": message, "detail": detail})

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    for name in REQUIRED_DIRS:
        exists = (pkg / name).is_dir()
        check(f"dir:{name}", exists)
        if not exists:
            add("DIR_MISSING", "FAIL", f"缺少目录 {name}/")
    for name in ("test-cases.xlsx", "manifest.json", "submission.zip"):
        exists = (pkg / name).is_file()
        check(f"file:{name}", exists)
        if not exists:
            add("FILE_MISSING", "FAIL", f"缺少文件 {name}")

    manifest_path = pkg / "manifest.json"
    if not manifest_path.is_file():
        return _verify_result(findings, checks, {})
    try:
        manifest = rs.json_load(manifest_path)
    except Exception as exc:
        add("MANIFEST_UNREADABLE", "FAIL", f"manifest.json 无法解析：{exc}")
        return _verify_result(findings, checks, {})

    check("manifest:schema", manifest.get("schema_version") == "1.0",
          str(manifest.get("schema_version")))
    if manifest.get("schema_version") != "1.0":
        add("MANIFEST_SCHEMA", "FAIL", f"manifest schema_version 应为 1.0，实际 {manifest.get('schema_version')}")
    official = manifest.get("official_format_confirmed")
    check("manifest:official_format_confirmed_false", official is False, str(official))
    if official is not False:
        add("OFFICIAL_FORMAT_CLAIMED", "FAIL",
            "manifest 未声明 official_format_confirmed=false，不得声称符合官方格式")

    listed = manifest.get("files") or []
    check("manifest:files_nonempty", bool(listed), f"{len(listed)} files")
    missing, mismatched = [], []
    for item in listed:
        path = pkg / item["path"]
        if not path.is_file():
            missing.append(item["path"])
            continue
        if path.stat().st_size != item.get("size_bytes") or _sha256(path) != item.get("sha256"):
            mismatched.append(item["path"])
    check("files:present", not missing, "; ".join(missing))
    check("files:hash_match", not mismatched, "; ".join(mismatched))
    if missing:
        add("PAYLOAD_MISSING", "FAIL", f"{len(missing)} 个载荷文件缺失", "; ".join(missing))
    if mismatched:
        add("PAYLOAD_HASH_MISMATCH", "FAIL", f"{len(mismatched)} 个载荷文件哈希不一致",
            "; ".join(mismatched))

    listed_paths = {item["path"] for item in listed}
    on_disk = {p.relative_to(pkg).as_posix() for p in _iter_files(pkg)}
    unlisted = sorted(on_disk - listed_paths - {"manifest.json", "submission.zip"})
    check("files:no_unlisted", not unlisted, "; ".join(unlisted))
    if unlisted:
        add("UNLISTED_FILE", "WARNING", f"{len(unlisted)} 个文件未登记在 manifest",
            "; ".join(unlisted))

    zip_path = pkg / "submission.zip"
    if zip_path.is_file():
        actual_zip_hash = _sha256(zip_path)
        expected_zip_hash = (manifest.get("zip") or {}).get("sha256")
        check("zip:hash", actual_zip_hash == expected_zip_hash,
              f"{actual_zip_hash[:16]}… vs {str(expected_zip_hash)[:16]}…")
        if actual_zip_hash != expected_zip_hash:
            add("ZIP_HASH_MISMATCH", "FAIL", "submission.zip 的 sha256 与 manifest 不一致",
                f"actual={actual_zip_hash} expected={expected_zip_hash}")
        try:
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                check("zip:sorted", names == sorted(names))
                if names != sorted(names):
                    add("ZIP_UNSORTED", "WARNING", "zip 条目未按路径排序")
                entry_set = set(names)
                check("zip:entries_match_manifest", entry_set == listed_paths,
                      f"zip={len(entry_set)} manifest={len(listed_paths)}")
                if entry_set != listed_paths:
                    add("ZIP_ENTRY_SET", "FAIL", "zip 条目与 manifest 不一致",
                        f"only_zip={sorted(entry_set - listed_paths)} only_manifest={sorted(listed_paths - entry_set)}")
                bad = []
                with tempfile.TemporaryDirectory(prefix="pkgverify-") as tmp:
                    zf.extractall(tmp)
                    for item in listed:
                        extracted = Path(tmp) / item["path"]
                        if not extracted.is_file() or _sha256(extracted) != item.get("sha256"):
                            bad.append(item["path"])
                check("zip:extracted_hashes", not bad, "; ".join(bad))
                if bad:
                    add("ZIP_CONTENT_MISMATCH", "FAIL", f"{len(bad)} 个解压文件哈希不一致", "; ".join(bad))
        except zipfile.BadZipFile as exc:
            add("ZIP_UNREADABLE", "FAIL", f"submission.zip 无法解压：{exc}")
            check("zip:readable", False)

    xlsx = pkg / "test-cases.xlsx"
    xlsx_info: dict[str, Any] = {}
    if xlsx.is_file():
        try:
            xlsx_info = _read_xlsx(xlsx)
            expected_rows = int(manifest.get("case_count") or 0)
            check("xlsx:opens", True, f"{xlsx_info['rows']} data rows")
            check("xlsx:header", xlsx_info["header"][:len(rs.CANONICAL_CASE_COLUMNS)]
                  == rs.CANONICAL_CASE_COLUMNS, str(xlsx_info["header"]))
            if xlsx_info["header"][:len(rs.CANONICAL_CASE_COLUMNS)] != rs.CANONICAL_CASE_COLUMNS:
                add("XLSX_HEADER", "FAIL", "xlsx 首表表头与契约列不一致",
                    str(xlsx_info["header"]))
            check("xlsx:row_count", xlsx_info["rows"] == expected_rows,
                  f"rows={xlsx_info['rows']} manifest={expected_rows}")
            if xlsx_info["rows"] != expected_rows:
                add("XLSX_ROW_COUNT", "FAIL",
                    f"xlsx 数据行 {xlsx_info['rows']} 与 manifest case_count {expected_rows} 不一致")
            dupes = {cid for cid in xlsx_info["case_ids"] if xlsx_info["case_ids"].count(cid) > 1}
            if dupes:
                add("XLSX_DUPLICATE_CASE", "FAIL", "xlsx 存在重复 case_id", "; ".join(sorted(dupes)))
        except Exception as exc:
            add("XLSX_UNREADABLE", "FAIL", f"xlsx 无法打开：{exc}")
            check("xlsx:opens", False)

    index_path = pkg / "screenshots" / "index.csv"
    screenshot_rows: list[dict[str, str]] = []
    if index_path.is_file():
        with index_path.open("r", encoding="utf-8-sig", newline="") as f:
            screenshot_rows = [dict(r) for r in csv.DictReader(f)]
        check("screenshots:index_rows", len(screenshot_rows) > 0, str(len(screenshot_rows)))
        bad_files = [r["file"] for r in screenshot_rows
                     if not (pkg / "screenshots" / r.get("file", "")).is_file()]
        check("screenshots:files_present", not bad_files, "; ".join(bad_files))
        if bad_files:
            add("SCREENSHOT_MISSING", "FAIL", f"{len(bad_files)} 张截图缺失", "; ".join(bad_files))
        bad_hash = []
        for row in screenshot_rows:
            p = pkg / "screenshots" / row.get("file", "")
            if p.is_file() and _sha256(p) != row.get("sha256"):
                bad_hash.append(row.get("file", ""))
        check("screenshots:hash_match", not bad_hash, "; ".join(bad_hash))
        if bad_hash:
            add("SCREENSHOT_HASH_MISMATCH", "FAIL", f"{len(bad_hash)} 张截图哈希不一致",
                "; ".join(bad_hash))
    else:
        add("SCREENSHOTS_INDEX_MISSING", "FAIL", "缺少 screenshots/index.csv")

    code_root = pkg / "test-code"
    case_check: dict[str, Any] = {"implemented": [], "not_implemented": [], "broken": []}
    if xlsx.is_file() and code_root.is_dir():
        try:
            from openpyxl import load_workbook
            wb = load_workbook(xlsx, read_only=True, data_only=True)
            ws = wb[wb.sheetnames[0]]
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            header = [str(x) if x is not None else "" for x in rows[0]]
            idx = {name: header.index(name) for name in header if name}
            for row in rows[1:]:
                if not row or row[idx["case_id"]] in (None, ""):
                    continue
                cid = str(row[idx["case_id"]])
                automation = str(row[idx["automation"]] or "") if "automation" in idx else ""
                notes = str(row[idx["notes"]] or "") if "notes" in idx else ""
                status = str(row[idx["status"]] or "") if "status" in idx else ""
                if automation:
                    rel = _automation_path(automation)
                    func = automation.split("::", 1)[1] if "::" in automation else ""
                    target = code_root / rel
                    if not target.is_file():
                        case_check["broken"].append(f"{cid}: 缺少 {rel}")
                    elif func and not re.search(rf"def\s+{re.escape(func)}\s*\(", target.read_text(
                            encoding="utf-8", errors="replace")):
                        case_check["broken"].append(f"{cid}: {rel} 中找不到 def {func}")
                    else:
                        case_check["implemented"].append(cid)
                elif NOT_IMPLEMENTED_MARKER in notes:
                    case_check["not_implemented"].append(cid)
                else:
                    case_check["broken"].append(f"{cid}: 未关联测试函数且未标注「未实现」")
                if status == "passed":
                    shots = [r for r in screenshot_rows if r.get("case_id") == cid]
                    if not shots:
                        case_check.setdefault("passed_without_screenshot", []).append(cid)
        except Exception as exc:
            add("CASE_LINK_UNREADABLE", "FAIL", f"无法读取 xlsx 以校验用例关联：{exc}")
    if case_check["broken"]:
        add("CASE_LINK_BROKEN", "FAIL", f"{len(case_check['broken'])} 条用例的测试关联不成立",
            "; ".join(case_check["broken"]))
    check("cases:linked", not case_check["broken"],
          f"implemented={len(case_check['implemented'])} "
          f"not_implemented={len(case_check['not_implemented'])}")
    if case_check.get("passed_without_screenshot"):
        add("PASSED_CASE_WITHOUT_SCREENSHOT", "FAIL", "通过用例缺少截图",
            "; ".join(case_check["passed_without_screenshot"]))
    check("cases:passed_have_screenshot", not case_check.get("passed_without_screenshot"),
          "; ".join(case_check.get("passed_without_screenshot") or []))

    summary = {
        "run_id": manifest.get("run_id"),
        "case_count": manifest.get("case_count"),
        "files": len(listed),
        "screenshots": len(screenshot_rows),
        "zip_sha256": (manifest.get("zip") or {}).get("sha256"),
        "case_links": case_check,
        "checks_total": len(checks),
        "checks_ok": sum(1 for c in checks if c["ok"]),
    }
    return _verify_result(findings, checks, summary)


def _verify_result(findings: list[dict[str, str]], checks: list[dict[str, Any]],
                   summary: dict[str, Any]) -> dict[str, Any]:
    fails = [f for f in findings if f["severity"] == "FAIL"]
    warnings = [f for f in findings if f["severity"] == "WARNING"]
    return {
        "ok": not fails,
        "verdict": "PASS" if not fails else "FAIL",
        "exit_code": 0 if not fails else 1,
        "findings": findings,
        "finding_counts": {"FAIL": len(fails), "WARNING": len(warnings)},
        "checks": checks,
        "summary": summary,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build/verify the internal submission package")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--cases", default="", help="显式指定用例表 CSV")
    parser.add_argument("--report-dir", default="", help="报告目录（默认 reports/executions/<run>）")
    parser.add_argument("--out", default="submission", help="交付包根目录（默认 submission）")
    parser.add_argument("--manifest", default="", help="覆盖 evidence/manifest.json 路径")
    parser.add_argument("--force-reports", action="store_true", help="用 --report-dir 覆盖包内报告")
    parser.add_argument("--verify", default="", help="校验已存在的交付包目录")
    parser.add_argument("--json", action="store_true", help="兼容开关：标准输出始终为 JSON")
    args = parser.parse_args(argv)

    if args.verify:
        result = verify_package(Path(args.verify))
        result["package_dir"] = str(Path(args.verify))
        result["official_format_confirmed"] = rs.OFFICIAL_FORMAT_CONFIRMED
        result["official_format_note"] = rs.OFFICIAL_FORMAT_NOTE
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(result["exit_code"])

    if not args.run_id:
        parser.error("--run-id is required unless --verify is used")

    out_root = Path(args.out)
    if not out_root.is_absolute():
        out_root = ROOT / out_root
    report_dir = Path(args.report_dir) if args.report_dir else None
    if report_dir is not None and not report_dir.is_absolute():
        report_dir = ROOT / report_dir
    try:
        result = build_package(
            args.run_id,
            cases_path=Path(args.cases) if args.cases else None,
            report_dir=report_dir,
            out_root=out_root,
            manifest_path=Path(args.manifest) if args.manifest else None,
            force_reports=args.force_reports,
        )
    except KeyError as exc:
        message = str(exc.args[0]) if exc.args else str(exc)
        print(json.dumps({"error": message, "exit_code": 2}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
