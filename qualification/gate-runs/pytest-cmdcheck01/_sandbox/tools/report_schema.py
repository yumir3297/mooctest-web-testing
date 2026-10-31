#!/usr/bin/env python3
"""Shared schema helpers for the report generator and the submission packager.

The module owns three things that both tools must agree on:

1. the canonical test-case table columns (``docs/CONTRACTS.md`` §3) and the
   alias mapping used when reading older tables;
2. the run-scoped lookup that decides *which* CSV belongs to a run;
3. the case-level expected/actual classification that keeps assertion booleans
   out of the case-level oracle.

It also exposes a small tool/environment probe. The probe deliberately reads the
Chrome PE version resource instead of running ``chrome.exe --version``: on
Windows that command does not reliably print a version and can launch a window.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

REPORT_SCHEMA_VERSION = "2.0"
PACKAGE_SCHEMA_VERSION = "1.0"
PACKAGE_KIND = "internal-rehearsal"
OFFICIAL_FORMAT_CONFIRMED = False
OFFICIAL_FORMAT_NOTE = "内部演练交付包，2026 官方提交格式未确认"

# docs/CONTRACTS.md §3 — order is fixed.
CANONICAL_CASE_COLUMNS = [
    "case_id", "title", "priority", "requirement_ids", "case_type", "method",
    "preconditions", "test_data", "steps", "expected", "actual", "status",
    "automation", "evidence_required", "executed_in_run", "notes",
]

COLUMN_ALIASES = {
    "id": "case_id",
    "case": "case_id",
    "caseid": "case_id",
    "requirement": "requirement_ids",
    "requirements": "requirement_ids",
    "requirement_id": "requirement_ids",
    "req": "requirement_ids",
    "precondition": "preconditions",
    "preconds": "preconditions",
    "data": "test_data",
    "testdata": "test_data",
    "evidence": "evidence_required",
    "evidence_req": "evidence_required",
    "executed_run": "executed_in_run",
    "run": "executed_in_run",
    "note": "notes",
}

IMAGE_KINDS = {
    "screenshot", "fullpage-screenshot", "element-screenshot", "annotation",
    "diff", "heatmap", "comparison", "crop",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}

STATUS_LABELS = {
    "passed": "通过",
    "failed": "失败",
    "xfailed": "受控预期失败",
    "blocked": "阻塞",
    "skipped": "跳过",
    "running": "执行中",
    "not-run": "未执行",
    "aborted": "中止",
}

# Bare assertion facts that must never be presented as a case-level oracle.
TRIVIAL_EXPECTED_VALUES = {"true", "false", "none"}

RUN_ID_RE = re.compile(r"RUN-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
MISSING_VALUE = "未采集"


# --------------------------------------------------------------------------- #
# generic helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_posix(path: Path, start: Path) -> str:
    try:
        return os.path.relpath(Path(path), Path(start)).replace("\\", "/")
    except ValueError:
        # different drives on Windows: fall back to an absolute POSIX path
        return Path(path).as_posix()


def status_label(status: Any) -> str:
    key = str(status or "")
    return STATUS_LABELS.get(key, key or "未知")


def is_image_evidence(kind: str | None, path: str | None = None) -> bool:
    if kind in IMAGE_KINDS:
        return True
    suffix = Path(path or "").suffix.lower()
    return bool(suffix) and suffix in IMAGE_SUFFIXES


def json_load(path: Path) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# case table
# --------------------------------------------------------------------------- #
def _normalise_row(row: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_key, raw_value in row.items():
        if raw_key is None:
            continue
        key = str(raw_key).strip()
        value = "" if raw_value is None else str(raw_value).strip()
        out[key] = value
    for alias, canonical in COLUMN_ALIASES.items():
        if alias in out and not out.get(canonical):
            out[canonical] = out[alias]
    return out


def read_case_csv(path: Path) -> list[dict[str, str]]:
    """Read a case table, mapping contract aliases. Never raises."""
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
            rows = [_normalise_row(r) for r in csv.DictReader(f)]
    except Exception:
        return []
    return [r for r in rows if (r.get("case_id") or "").strip()]


def split_runs(value: str | None) -> list[str]:
    tokens = [t.strip() for t in re.split(r"[,;\s/|]+", str(value or "")) if t.strip()]
    return [t for t in tokens if RUN_ID_RE.fullmatch(t)]


def row_runs(row: dict[str, str]) -> list[str]:
    return split_runs(row.get("executed_in_run"))


def row_belongs_to_run(row: dict[str, str], run_id: str) -> bool:
    """Exact token match so RUN-X never matches RUN-X-2."""
    return run_id in row_runs(row)


def find_run_case_table(run_id: str, reports_root: Path) -> dict[str, Any]:
    """Return the single case table whose ``executed_in_run`` contains ``run_id``.

    No fallback: borrowing another run's table is what produced bogus coverage
    gaps in earlier reports.
    """
    base = Path(reports_root) / "test-cases"
    candidates = sorted(base.glob("*.csv")) if base.is_dir() else []
    inspected = []
    for path in candidates:
        rows = read_case_csv(path)
        inspected.append({"path": str(path), "rows": len(rows),
                          "run_tokens": sorted({t for r in rows for t in row_runs(r)})})
        if any(row_belongs_to_run(r, run_id) for r in rows):
            return {
                "found": True,
                "path": path,
                "rows": rows,
                "reason": "",
                "inspected": inspected,
            }
    return {
        "found": False,
        "path": None,
        "rows": [],
        "reason": f"未找到本运行的用例表（没有 CSV 的 executed_in_run 包含 {run_id}）",
        "inspected": inspected,
    }


def row_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        cid = (row.get("case_id") or "").strip()
        if cid and cid not in out:
            out[cid] = row
    return out


def design_status(row: dict[str, str] | None) -> str:
    """Human readable design/execution status taken from the table itself."""
    if not row:
        return ""
    explicit = (row.get("status") or "").strip()
    if explicit:
        return explicit
    executed = (row.get("executed_in_run") or "").strip()
    if not executed:
        return ""
    if executed.startswith("未覆盖"):
        return "未执行（未覆盖）"
    if executed.startswith("未执行"):
        return "未执行（本轮 scope 外）"
    if RUN_ID_RE.fullmatch(executed):
        return "已执行"
    return executed


def split_ids(value: str | None) -> list[str]:
    return [t.strip() for t in re.split(r"[,;/\s|]+", str(value or "")) if t.strip()]


# --------------------------------------------------------------------------- #
# oracle classification
# --------------------------------------------------------------------------- #
def classify_case_expected(expected: Any, assertion_count: int) -> dict[str, Any]:
    """Decide whether ``case.expected`` can be used as a case-level oracle.

    ``conftest.CaseContext.check`` used to write the last assertion's boolean
    into ``case.expected``; those legacy values are retained as ``raw`` but are
    never rendered as the case expectation.
    """
    raw = "" if expected is None else str(expected)
    stripped = raw.strip()
    if not stripped:
        return {
            "value": "",
            "raw": raw,
            "source": "assertions" if assertion_count else "missing",
            "invalid": False,
            "reason": "运行记录未写入用例级预期",
        }
    if stripped.lower() in TRIVIAL_EXPECTED_VALUES:
        if assertion_count:
            return {
                "value": "",
                "raw": raw,
                "source": "assertions",
                "invalid": True,
                "reason": f"运行记录中的 {stripped!r} 是历史断言取值，不作为用例级预期",
            }
        return {
            "value": stripped,
            "raw": raw,
            "source": "case",
            "invalid": True,
            "reason": f"{stripped!r} 疑似断言取值，且没有断言明细可回溯",
        }
    return {"value": stripped, "raw": raw, "source": "case", "invalid": False, "reason": ""}


def classify_case_actual(actual: Any, assertions: list[dict[str, Any]]) -> dict[str, Any]:
    raw = "" if actual is None else str(actual)
    stripped = raw.strip()
    if stripped:
        return {"value": stripped, "raw": raw, "source": "case"}
    if assertions:
        return {"value": "", "raw": raw, "source": "assertions"}
    return {"value": "", "raw": raw, "source": "missing"}


# --------------------------------------------------------------------------- #
# environment probe (report-time only, clearly labelled)
# --------------------------------------------------------------------------- #
def _first_line(cmd: list[str], timeout: int = 20) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - probe must never crash a report
        return f"<error: {type(exc).__name__}: {exc}>"
    text = (proc.stdout or proc.stderr or "").strip()
    return text.splitlines()[0] if text else "<empty>"


def windows_file_version(path: Path) -> str | None:
    """Read the PE version resource; safer than ``chrome.exe --version``."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:  # pragma: no cover - ctypes ships with CPython
        return None

    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [
            ("dwSignature", wintypes.DWORD), ("dwStrucVersion", wintypes.DWORD),
            ("dwFileVersionMS", wintypes.DWORD), ("dwFileVersionLS", wintypes.DWORD),
            ("dwProductVersionMS", wintypes.DWORD), ("dwProductVersionLS", wintypes.DWORD),
            ("dwFileFlagsMask", wintypes.DWORD), ("dwFileFlags", wintypes.DWORD),
            ("dwFileOS", wintypes.DWORD), ("dwFileType", wintypes.DWORD),
            ("dwFileSubtype", wintypes.DWORD), ("dwFileDateMS", wintypes.DWORD),
            ("dwFileDateLS", wintypes.DWORD),
        ]

    try:
        version = ctypes.WinDLL("version")
        target = str(path)
        size = version.GetFileVersionInfoSizeW(target, None)
        if not size:
            return None
        buffer = ctypes.create_string_buffer(size)
        if not version.GetFileVersionInfoW(target, 0, size, buffer):
            return None
        pointer = ctypes.c_void_p()
        length = wintypes.UINT()
        if not version.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)):
            return None
        info = ctypes.cast(pointer, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        if not info.dwSignature:
            return None
        parts = [info.dwFileVersionMS >> 16, info.dwFileVersionMS & 0xFFFF,
                 info.dwFileVersionLS >> 16, info.dwFileVersionLS & 0xFFFF]
        return ".".join(str(p) for p in parts)
    except Exception:  # noqa: BLE001
        return None


def _chrome_candidates() -> list[Path]:
    candidates = []
    for env_name in ("MOOCTEST_CHROME", "CHROME_BINARY", "CHROME_PATH"):
        if os.environ.get(env_name):
            candidates.append(Path(os.environ[env_name]))
    for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                 os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                 os.environ.get("LOCALAPPDATA", "")):
        if base:
            candidates.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")
    candidates.append(Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
    return [p for p in candidates if str(p)]


def probe_environment(project_root: Path = ROOT, target: str = "") -> dict[str, Any]:
    """Best-effort snapshot of *the machine running the report*, not the run."""
    out: dict[str, Any] = {
        "probe_kind": "report-time",
        "note": "报告生成时探测，不是运行时刻记录；只作参考，不覆盖 manifest 中的运行环境",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "os": platform.release(),
        "target": target,
    }
    for name, key in (("pytest", "pytest"), ("selenium", "selenium"),
                      ("openpyxl", "openpyxl"), ("pillow", "Pillow"),
                      ("numpy", "numpy"), ("opencv-python", "cv2")):
        try:
            out[name] = importlib_metadata.version(key)
        except Exception:  # noqa: BLE001
            out[name] = "<not installed>"
    chrome_path = next((p for p in _chrome_candidates() if p.is_file()), None)
    if chrome_path:
        out["chrome_path"] = str(chrome_path)
        out["chrome"] = windows_file_version(chrome_path) or "<unknown>"
    else:
        out["chrome"] = "<not found>"
    driver = Path(project_root) / "tools" / "driver" / "chromedriver.exe"
    out["chromedriver"] = _first_line([str(driver), "--version"]) if driver.is_file() else "<not found>"
    out["node"] = _first_line(["node", "--version"], timeout=10)
    return out


def local_tool_versions() -> dict[str, Any]:
    versions: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    for name, key in (("pytest", "pytest"), ("selenium", "selenium"),
                      ("openpyxl", "openpyxl"), ("pillow", "Pillow")):
        try:
            versions[name] = importlib_metadata.version(key)
        except Exception:  # noqa: BLE001
            versions[name] = "<not installed>"
    return versions
