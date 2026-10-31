"""G4 - submission package structure and file hashes.

Only runs when ``--submission`` is given, so the gate stays usable before the
packager exists.  The packager (``tools/package_submission.py``) is owned by
another module and is intentionally *not* imported: G4 validates the artefact
it produced (structure, openable xlsx/zip, per-file sha256), which is stronger
than trusting the producer.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .common import Report, load_json, sha256_file, truncate

GATE = "G4"

REQUIRED_ENTRIES = ("test-cases.xlsx", "test-code", "screenshots", "reports",
                    "manifest.json", "submission.zip")


def _entries(manifest: Any) -> list[Mapping[str, Any]]:
    if isinstance(manifest, list):
        return [item for item in manifest if isinstance(item, Mapping)]
    if not isinstance(manifest, Mapping):
        return []
    for key in ("files", "entries", "artifacts"):
        value = manifest.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
        if isinstance(value, Mapping):
            packed = []
            for path, meta in value.items():
                record = dict(meta) if isinstance(meta, Mapping) else {}
                record.setdefault("path", path)
                packed.append(record)
            return packed
    return []


def validate(report: Report, submission: Path) -> dict[str, Any]:
    submission = Path(submission)
    stats: dict[str, Any] = {"submission": str(submission)}

    report.check(GATE, "PACKAGE_DIR_MISSING", submission.is_dir(), str(submission),
                 "交付包目录不存在", "FAIL")
    if not submission.is_dir():
        return stats

    for name in REQUIRED_ENTRIES:
        report.check(GATE, "PACKAGE_ENTRY_MISSING", (submission / name).exists(), name,
                     f"交付包缺少 `{name}`", "FAIL")

    # --- xlsx --------------------------------------------------------------
    xlsx = submission / "test-cases.xlsx"
    if xlsx.is_file():
        try:
            from openpyxl import load_workbook  # noqa: PLC0415 - optional dependency
            workbook = load_workbook(xlsx, read_only=True, data_only=True)
            sheet = workbook.worksheets[0] if workbook.worksheets else None
            rows = 0
            if sheet is not None:
                for _ in sheet.iter_rows(values_only=True):
                    rows += 1
                    if rows > 1:
                        break
            workbook.close()
            stats["xlsx"] = {"sheets": len(workbook.sheetnames), "header_rows": rows}
            report.check(GATE, "PACKAGE_XLSX_UNREADABLE", True, "test-cases.xlsx",
                         "test-cases.xlsx 可被 openpyxl 打开")
            report.check(GATE, "PACKAGE_XLSX_EMPTY", rows >= 1, "test-cases.xlsx",
                         "test-cases.xlsx 首个工作表为空或只有表头都读不到", "FAIL")
        except Exception as exc:  # noqa: BLE001 - any load failure is a finding
            report.check(GATE, "PACKAGE_XLSX_UNREADABLE", False, "test-cases.xlsx",
                         f"openpyxl 无法打开 test-cases.xlsx：{type(exc).__name__}: {exc}", "FAIL")

    # --- zip ---------------------------------------------------------------
    archive = submission / "submission.zip"
    if archive.is_file():
        try:
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
                bad = zf.testzip()
            stats["zip"] = {"entries": len(names), "bad_member": bad}
            report.check(GATE, "PACKAGE_ZIP_INVALID", bad is None and bool(names), "submission.zip",
                         f"submission.zip 解压失败（member={bad!r}, entries={len(names)}）", "FAIL")
        except (zipfile.BadZipFile, OSError) as exc:
            report.check(GATE, "PACKAGE_ZIP_INVALID", False, "submission.zip",
                         f"submission.zip 无法解压：{type(exc).__name__}: {exc}", "FAIL")

    # --- package manifest --------------------------------------------------
    manifest_path = submission / "manifest.json"
    if manifest_path.is_file():
        data, error = load_json(manifest_path)
        if data is None:
            report.check(GATE, "PACKAGE_MANIFEST_INVALID", False, "manifest.json",
                         f"交付包 manifest.json 无法解析：{error}", "FAIL")
        else:
            entries = _entries(data)
            report.check(GATE, "PACKAGE_MANIFEST_EMPTY", bool(entries), "manifest.json",
                         "交付包 manifest.json 没有逐文件记录", "FAIL")
            mismatched: list[str] = []
            unlisted: list[str] = []
            for entry in entries:
                raw = entry.get("path") or entry.get("file") or ""
                path = Path(str(raw))
                if not path.is_absolute():
                    path = submission / path
                expected = str(entry.get("sha256") or "").strip().lower()
                if not path.is_file():
                    unlisted.append(str(raw))
                    continue
                if not expected:
                    continue
                if sha256_file(path) != expected:
                    mismatched.append(str(raw))
            report.check(GATE, "PACKAGE_FILE_MISSING", not unlisted, "manifest.json",
                         f"manifest 记录的文件不存在：{truncate(unlisted)}", "FAIL")
            report.check(GATE, "PACKAGE_HASH_MISMATCH", not mismatched, "manifest.json",
                         f"manifest 中的 sha256 与文件不一致：{truncate(mismatched)}", "FAIL")
            stats["package_manifest"] = {"entries": len(entries),
                                         "missing": len(unlisted),
                                         "mismatched": len(mismatched)}
    return stats
