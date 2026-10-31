#!/usr/bin/env python3
"""Export a finished run into the 2026 video-baseline submission layout.

The 2026 official competition package/template is not available yet. This tool
implements the three deliverables shown in the official training video:

    2026 official:  test case document (.docx, <=10 MB)
                    test script package (.zip, <=10 MB)
                    screenshot package (.zip, <=50 MB)

It deliberately labels the result ``2026-video-baseline`` and sets
``official_format_confirmed=false``. It must not be described as an official
2026 submission until the official package/notes are available and the profile
is re-verified.

Package layout::

    official_2026/<RUN>/
      测试用例文档.docx          10 columns, one row per case
      test-code.zip              runnable pytest suite + official-template reference
      screenshots.zip            screenshots/ + one PNG per case
      screenshots/               unpacked copy for review
      test-code/                 unpacked copy for review
      manifest.json              profile, sizes, hashes, mapping, warnings
      README.md                  scope and known limitations

Usage::

    python tools/export_official_2026.py --run-id RUN-X --app CartCheck \
      --cases reports/test-cases/cartcheck-test-cases.csv --slug cartcheck \
      --out official_2026

    python tools/export_official_2026.py --verify official_2026/RUN-X --json
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import evidence  # noqa: E402
from export_official_2025 import (  # noqa: E402
    OFFICIAL_COLUMNS,
    SCREENSHOT_FUNCTION,
    load_cases,
    normalise_app,
    normalise_requirement,
    official_id,
    official_timestamp,
    pick_image,
    read_text,
    sha256,
)

PROFILE = "2026-video-baseline"
DOCX_LIMIT = 10 * 1024 * 1024
SCRIPT_LIMIT = 10 * 1024 * 1024
SCREENSHOT_LIMIT = 50 * 1024 * 1024
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
LOCAL_PATH_RE = re.compile(r"C:\\Users\\[^\\\s]+|D:\\桌面\\|<user>")
TEXT_SUFFIX = {".py", ".ini", ".txt", ".md", ".cfg", ".toml", ".csv"}


def _rel(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def _write_zip(src: Path, dst: Path, prefix: str = "") -> None:
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            if not path.is_file():
                continue
            if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
                continue
            if path.suffix.lower() in {".pyc", ".pyd"}:
                continue
            rel = _rel(path, src)
            arc = f"{prefix}/{rel}" if prefix else rel
            info = zipfile.ZipInfo(filename=arc, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())


def _build_rows(
    cases: list[dict[str, str]],
    run: dict[str, Any],
    app: str,
    module_default: str,
    evidence_by_case: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    seq: dict[str, int] = {}
    rows: list[dict[str, str]] = []
    mapping: list[dict[str, str]] = []
    multi_req: list[dict[str, str]] = []
    for case in cases:
        req = normalise_requirement(case["requirement"])
        seq[req] = seq.get(req, 0) + 1
        cid = official_id(app, req, seq[req])
        status = case["status"] or run.get("cases", {}).get(case["case_id"], {}).get("status", "")
        actual = case["actual"]
        if not actual:
            actual = str(run.get("cases", {}).get(case["case_id"], {}).get("actual") or "")
        if not actual:
            actual = "未执行" if status.upper() in {"NOT_RUN", "NOT-RUN", ""} else status
        image = pick_image(evidence_by_case.get(case["case_id"], []))
        shot = ""
        if image:
            shot = f"{official_timestamp(image['created_at'], Path(image['path']).name)}_{cid}.png"
        if len([x for x in re.split(r"[,;/|、\s]+", case["requirement"]) if x.strip()]) > 1:
            multi_req.append({
                "case_id": case["case_id"],
                "requirement_ids": case["requirement"],
                "chosen": req,
            })
        rows.append({
            "测试用例编号": cid,
            "模块名称": case["module"] or module_default or req,
            "需求编号": req,
            "用例说明": case["title"],
            "前置条件": case["preconditions"].replace("；", "\n").replace(";", "\n"),
            "执行步骤": case["steps"],
            "输入数据": case["data"],
            "预期结果": case["expected"],
            "实际结果": actual,
            "截图文件名": shot,
        })
        mapping.append({
            "case_id": case["case_id"],
            "official_id": cid,
            "requirement": req,
            "screenshot": shot,
            "source_evidence": image["evidence_id"] if image else "",
        })
    return rows, mapping, multi_req


def _copy_screenshots(
    pkg: Path,
    mapping: list[dict[str, str]],
    evidence_by_case: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    shots = pkg / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    for item in mapping:
        if not item["screenshot"]:
            continue
        src = None
        for entry in evidence_by_case.get(item["case_id"], []):
            if entry["evidence_id"] == item["source_evidence"]:
                src = ROOT / entry["path"]
                break
        if src is None or not src.is_file():
            continue
        dst = shots / item["screenshot"]
        shutil.copy2(src, dst)
        copied.append({
            "case_id": item["case_id"],
            "file": item["screenshot"],
            "source": _rel(src, ROOT),
            "sha256": sha256(dst),
            "bytes": dst.stat().st_size,
        })
    return copied


def _write_docx(pkg: Path, rows: list[dict[str, str]], run: dict[str, Any], app: str) -> Path:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Cm(1.0)
    section.right_margin = Cm(1.0)
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(1.0)

    title = doc.add_paragraph()
    title.alignment = 1
    run_obj = title.add_run("2026 年全国大学生软件测试大赛 Web 应用测试用例文档")
    run_obj.bold = True
    run_obj.font.size = Pt(16)

    meta = doc.add_paragraph()
    meta.add_run(f"应用：{app}    运行：{run.get('run_id', '')}    目标：{run.get('target', '')}").font.size = Pt(9)
    meta.add_run(f"\n生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}").font.size = Pt(9)

    table = doc.add_table(rows=1, cols=len(OFFICIAL_COLUMNS))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header = table.rows[0].cells
    for idx, name in enumerate(OFFICIAL_COLUMNS):
        header[idx].text = name
        for paragraph in header[idx].paragraphs:
            for run_obj in paragraph.runs:
                run_obj.bold = True
                run_obj.font.size = Pt(9)

    for row in rows:
        cells = table.add_row().cells
        for idx, name in enumerate(OFFICIAL_COLUMNS):
            cells[idx].text = row[name]

    # Header repeats across pages.
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)

    widths = [2.5, 2.0, 1.2, 3.2, 2.8, 4.0, 2.8, 2.8, 2.8, 3.2]
    for row in table.rows:
        for idx, width in enumerate(widths):
            row.cells[idx].width = Cm(width)
            for paragraph in row.cells[idx].paragraphs:
                for run_obj in paragraph.runs:
                    run_obj.font.size = Pt(8)

    summary = doc.add_paragraph()
    summary.add_run(
        f"共 {len(rows)} 条用例；截图文件名字段 {sum(1 for r in rows if r['截图文件名'])} 条。"
    ).font.size = Pt(9)

    path = pkg / "测试用例文档.docx"
    doc.save(path)
    return path


def _official_skeleton(app: str, rows: list[dict[str, str]], target: str) -> str:
    reqs: list[str] = []
    for row in rows:
        if row["需求编号"] not in reqs:
            reqs.append(row["需求编号"])
    by_req: dict[str, list[str]] = {req: [] for req in reqs}
    for row in rows:
        by_req[row["需求编号"]].append(row["测试用例编号"])

    body: list[str] = []
    for req in reqs:
        ids = by_req[req]
        body.append(f"    def test_{app}_{req}(self, driver):")
        body.append(f'        """需求 {req}：{len(ids)} 条用例 {", ".join(ids)}。"""')
        body.append(f"        # 参考骨架；2026 官方模板未获取，运行实现见 tests/generated/。")
        body.append("        raise NotImplementedError(\"补全官方模板 test-code-start/end 之间的代码\")")
        body.append("")

    return f'''"""2026 视频基线：官方模板参考骨架（非运行入口）。

运行入口是 tests/generated/ 下的 pytest 套件；本文件只用于保留官方模板的
test-code-start/end 结构和按需求分组的函数名，等待官方 2026 模板后替换。
"""
import os
from datetime import datetime

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


@pytest.fixture(scope="function")
def driver():
    # 提交前使用官方路径；本地调试可通过 MOOCTEST_CHROMEDRIVER 覆盖。
    executable = os.environ.get(
        "MOOCTEST_CHROMEDRIVER",
        r"C:\\Program Files\\Google\\Chrome\\Application\\chromedriver.exe",
    )
    service = Service(executable_path=executable)
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("{target}")
    driver.maximize_window()
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


class Test{app}:

    # test-code-start

{chr(10).join(body)}
    # test-code-end

{SCREENSHOT_FUNCTION}'''


def _build_script_tree(
    pkg: Path,
    app: str,
    slug: str,
    rows: list[dict[str, str]],
    target: str,
) -> Path:
    root = pkg / "test-code"
    root.mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "official_template").mkdir(parents=True, exist_ok=True)

    for rel in ("pytest.ini", "requirements.txt", "tests/conftest.py", "tools/evidence.py", "tools/versioning.py"):
        src = ROOT / rel
        if src.is_file():
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    generated = ROOT / "tests" / "generated" / slug
    if generated.is_dir():
        shutil.copytree(
            generated,
            root / "tests" / "generated" / slug,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )

    (root / "official_template" / f"Test{app}.py").write_text(
        _official_skeleton(app, rows, target), encoding="utf-8", newline="\n"
    )

    readme = f"""# 2026 视频基线测试脚本包

- 运行入口：`tests/generated/{slug}/test_*.py`（pytest + Selenium）。
- 运行方式：

  ```powershell
  pip install -r requirements.txt
  pytest --target <被测站点 URL>
  ```

- `official_template/Test{app}.py` 是官方模板结构的参考骨架，保留
  `test-code-start` / `test-code-end`，但函数体未实现；2026 官方模板未获取。
- 本地调试时用 `MOOCTEST_CHROMEDRIVER` 指向本机驱动；提交到官方环境前，
  按模板要求使用官方驱动路径。
- 本包由 `tools/export_official_2026.py` 生成，profile=`2026-video-baseline`，
  不代表官方 2026 格式已确认。
"""
    (root / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    return root


def build(args: argparse.Namespace) -> int:
    out_root = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    pkg = out_root / args.run_id
    manifest = evidence.load_manifest()
    if args.run_id not in manifest.get("runs", {}):
        print(f"ERROR: run not found: {args.run_id}", file=sys.stderr)
        return 2
    run = manifest["runs"][args.run_id]
    cases_path = Path(args.cases) if args.cases else None
    if cases_path is None or not cases_path.is_file():
        print("ERROR: --cases is required (internal case table)", file=sys.stderr)
        return 2
    cases = load_cases(cases_path)
    if not cases:
        print("ERROR: case table is empty", file=sys.stderr)
        return 2

    app = normalise_app(args.app)
    slug = args.slug or cases_path.name.split("-test-cases")[0] or "target"
    module_default = args.module or ""
    evidence_by_case: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest.get("evidence", []):
        if entry.get("run_id") == args.run_id:
            evidence_by_case.setdefault(str(entry.get("case_id")), []).append(entry)

    rows, mapping, multi_req = _build_rows(cases, run, app, module_default, evidence_by_case)

    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True, exist_ok=True)

    copied = _copy_screenshots(pkg, mapping, evidence_by_case)
    docx_path = _write_docx(pkg, rows, run, app)
    target = args.target or str(run.get("target", ""))
    script_root = _build_script_tree(pkg, app, slug, rows, target)

    script_zip = pkg / "test-code.zip"
    _write_zip(script_root, script_zip)
    screenshots_zip = pkg / "screenshots.zip"
    _write_zip(pkg / "screenshots", screenshots_zip, prefix="screenshots")

    missing_shots = [m["official_id"] for m in mapping if not m["screenshot"]]
    deliverables = []
    for name in ("测试用例文档.docx", "test-code.zip", "screenshots.zip"):
        path = pkg / name
        deliverables.append({"name": name, "bytes": path.stat().st_size, "sha256": sha256(path)})

    readme = f"""# 2026 视频基线提交包（{args.run_id}）

依据 2026 官方培训视频整理，**不是已确认的官方 2026 模板**。

## 三项交付物

| 文件 | 格式 | 大小上限 | 本包大小 |
|---|---|---|---|
| 测试用例文档 | `.docx` | 10 MB | {deliverables[0]['bytes']} B |
| 测试脚本压缩包 | `.zip` | 10 MB | {deliverables[1]['bytes']} B |
| 测试截图压缩包 | `.zip` | 50 MB | {deliverables[2]['bytes']} B |

- 用例：{len(rows)} 条，10 列；截图：{len(copied)} 张，一条用例一张。
- 脚本 zip 的运行入口是 `tests/generated/{slug}/test_*.py`；`official_template/Test{app}.py`
  是保留 markers 的参考骨架。
- 截图来自 `evidence/` 中的真实运行，未重绘、未伪造。

## 边界

- 2026 官方 docx 模板、脚本包目录结构、赛题包《注意事项》尚未获取。
- 本包 profile=`{PROFILE}`、`official_format_confirmed=false`；不能声称官方 2026 合规。
- 缺截图的用例：{', '.join(missing_shots) if missing_shots else '无'}。

生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}
"""
    (pkg / "README.md").write_text(readme, encoding="utf-8")

    payload = {
        "schema_version": "1.0",
        "profile": PROFILE,
        "official_format_confirmed": False,
        "official_format_note": "依据 2026 官方培训视频；官方 2026 docx/脚本包模板未获取",
        "run_id": args.run_id,
        "app": app,
        "slug": slug,
        "target": target,
        "case_count": len(rows),
        "screenshot_count": len(copied),
        "cases_missing_screenshot": missing_shots,
        "cases_with_multiple_requirements": multi_req,
        "deliverables": deliverables,
        "mapping": mapping,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    (pkg / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "profile": PROFILE,
        "run_id": args.run_id,
        "app": app,
        "case_count": len(rows),
        "screenshot_count": len(copied),
        "deliverables": deliverables,
        "cases_missing_screenshot": missing_shots,
        "official_format_confirmed": False,
    }, ensure_ascii=False, indent=2))
    print(f"package: {pkg}")
    return 0


def _read_zip_text(zf: zipfile.ZipFile, name: str) -> str:
    try:
        return zf.read(name).decode("utf-8", errors="replace")
    except KeyError:
        return ""


def verify(pkg: Path, emit: bool = True) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def add(code: str, severity: str, subject: str, message: str) -> None:
        findings.append({"code": code, "severity": severity, "subject": subject, "message": message})

    manifest_path = pkg / "manifest.json"
    if not manifest_path.is_file():
        result = {
            "ok": False,
            "verdict": "FAIL",
            "profile": PROFILE,
            "package": str(pkg),
            "findings": [{"code": "MANIFEST_MISSING", "severity": "FAIL",
                          "subject": "manifest.json", "message": "manifest.json 缺失"}],
            "finding_counts": {"FAIL": 1, "WARNING": 0},
            "case_count": 0,
            "screenshot_count": 0,
        }
        if emit:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = str(manifest.get("app") or "App")

    docx_path = pkg / "测试用例文档.docx"
    script_zip = pkg / "test-code.zip"
    shots_zip = pkg / "screenshots.zip"
    for name, path, limit in (
        ("测试用例文档.docx", docx_path, DOCX_LIMIT),
        ("test-code.zip", script_zip, SCRIPT_LIMIT),
        ("screenshots.zip", shots_zip, SCREENSHOT_LIMIT),
    ):
        if not path.is_file():
            add("DELIVERABLE_MISSING", "FAIL", name, "交付物不存在")
        elif path.stat().st_size > limit:
            add("DELIVERABLE_TOO_LARGE", "FAIL", name,
                f"{path.stat().st_size} B 超过 {limit} B")

    rows: list[dict[str, str]] = []
    if docx_path.is_file():
        try:
            from docx import Document

            doc = Document(docx_path)
            if not doc.tables:
                add("DOCX_TABLE_MISSING", "FAIL", "测试用例文档.docx", "没有表格")
            else:
                table = doc.tables[0]
                header = [cell.text.strip() for cell in table.rows[0].cells]
                if header[:len(OFFICIAL_COLUMNS)] != OFFICIAL_COLUMNS:
                    add("DOCX_HEADER", "FAIL", "测试用例文档.docx",
                        f"列头不符合 10 列：{header[:10]}")
                for row in table.rows[1:]:
                    values = [cell.text.strip() for cell in row.cells]
                    if not values or not values[0]:
                        continue
                    rows.append(dict(zip(OFFICIAL_COLUMNS, values[:10])))
                if not rows:
                    add("DOCX_EMPTY", "FAIL", "测试用例文档.docx", "用例表没有数据行")
        except Exception as exc:  # noqa: BLE001
            add("DOCX_UNREADABLE", "FAIL", "测试用例文档.docx", f"docx 无法解析：{exc}")

    id_re = re.compile(rf"^{re.escape(app)}_R\d{{3}}_\d{{3}}$")
    seen: set[str] = set()
    shot_names: list[str] = []
    for row in rows:
        cid = row["测试用例编号"]
        if not id_re.match(cid):
            add("CASE_ID_FORMAT", "FAIL", cid, f"编号不符合 {app}_R{{3位}}_{{3位}}")
        if cid in seen:
            add("CASE_ID_DUPLICATE", "FAIL", cid, "用例编号重复")
        seen.add(cid)
        name = row["截图文件名"]
        shot_names.append(name)
        if not name:
            add("SCREENSHOT_FIELD_EMPTY", "FAIL", cid, "截图文件名为空")
        elif not re.match(rf"^\d{{11}}_{re.escape(cid)}\.png$", name):
            add("SCREENSHOT_NAME_FORMAT", "FAIL", cid, f"截图名不符合 <11位时间戳>_<编号>.png：{name}")

    zip_shots: list[str] = []
    if shots_zip.is_file():
        try:
            with zipfile.ZipFile(shots_zip) as zf:
                names = zf.namelist()
                zip_shots = [n for n in names if n.lower().endswith(".png")]
                bad = [n for n in names if not n.startswith("screenshots/")]
                if bad:
                    add("SHOT_ZIP_STRUCTURE", "FAIL", "screenshots.zip",
                        f"{len(bad)} 个条目不在 screenshots/ 下")
                if len(zip_shots) != len(set(zip_shots)):
                    add("SHOT_ZIP_DUPLICATE", "FAIL", "screenshots.zip", "截图条目重复")
                if len(zip_shots) != len(rows):
                    add("SHOT_ZIP_COUNT", "FAIL", "screenshots.zip",
                        f"zip 截图 {len(zip_shots)} 与 docx 用例 {len(rows)} 不一致")
                for name in shot_names:
                    if name and f"screenshots/{name}" not in names:
                        add("SHOT_ZIP_MISSING", "FAIL", name, "docx 中的截图不在 zip 内")
        except zipfile.BadZipFile:
            add("SHOT_ZIP_CORRUPT", "FAIL", "screenshots.zip", "zip 无法解析")

    if script_zip.is_file():
        try:
            with zipfile.ZipFile(script_zip) as zf:
                names = zf.namelist()
                required = ["pytest.ini", "requirements.txt", "tests/conftest.py",
                            "tools/evidence.py", "tools/versioning.py"]
                for name in required:
                    if name not in names:
                        add("SCRIPT_ENTRY_MISSING", "FAIL", name, "脚本 zip 缺少运行必需文件")
                test_files = [n for n in names if re.match(r"^tests/generated/.+/test_.+\.py$", n)]
                if not test_files:
                    add("SCRIPT_TEST_MISSING", "FAIL", "tests/generated", "脚本 zip 没有可运行测试文件")
                if any(n.lower().endswith(".exe") for n in names):
                    add("SCRIPT_EXE", "FAIL", "test-code.zip", "脚本 zip 不应包含 exe")
                template = f"official_template/Test{app}.py"
                if template not in names:
                    add("SCRIPT_TEMPLATE_MISSING", "FAIL", template, "缺少官方模板参考骨架")
                else:
                    text = _read_zip_text(zf, template)
                    if "# test-code-start" not in text or "# test-code-end" not in text:
                        add("SCRIPT_MARKERS", "FAIL", template, "缺少 test-code-start/end")
                    if "def take_screenshot(driver, file_name):" not in text:
                        add("SCRIPT_SCREENSHOT_FN", "FAIL", template, "缺少官方 take_screenshot")

                for name in names:
                    if Path(name).suffix.lower() not in TEXT_SUFFIX:
                        continue
                    text = _read_zip_text(zf, name)
                    if LOCAL_PATH_RE.search(text):
                        add("SCRIPT_LOCAL_PATH", "FAIL", name, "脚本包包含本机绝对路径/用户名")
                        break
        except zipfile.BadZipFile:
            add("SCRIPT_ZIP_CORRUPT", "FAIL", "test-code.zip", "zip 无法解析")

    add("OFFICIAL_TEMPLATE_UNCONFIRMED", "WARNING", "profile",
        "2026 官方 docx/脚本包模板未获取；本包仅为 2026 视频基线")
    add("SCRIPT_REFERENCE_ONLY", "WARNING", "official_template",
        "official_template 是保留 markers 的参考骨架；可运行入口是 tests/generated/")

    blocking = [f for f in findings if f["severity"] == "FAIL"]
    result = {
        "ok": not blocking,
        "verdict": "PASS" if not blocking else "FAIL",
        "profile": PROFILE,
        "package": str(pkg),
        "case_count": len(rows),
        "screenshot_count": len(zip_shots),
        "deliverables": manifest.get("deliverables", []),
        "finding_counts": {
            "FAIL": len(blocking),
            "WARNING": len(findings) - len(blocking),
        },
        "findings": findings,
    }
    if emit:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="export / verify the 2026 video-baseline layout")
    parser.add_argument("--run-id")
    parser.add_argument("--app", default="")
    parser.add_argument("--cases", default="")
    parser.add_argument("--module", default="")
    parser.add_argument("--slug", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--out", default="official_2026")
    parser.add_argument("--verify", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            result = verify(Path(args.verify))
            return 0 if result.get("ok") else 1
        if not args.run_id:
            parser.error("--run-id is required unless --verify is used")
        if not args.app:
            parser.error("--app is required (official case id prefix, e.g. CartCheck)")
        return build(args)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
