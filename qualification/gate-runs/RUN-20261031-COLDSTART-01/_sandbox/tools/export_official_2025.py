#!/usr/bin/env python3
"""Export a finished run into the **2025 official competition layout**.

This is an *adapter*, not a replacement for the internal conventions. It reads the
internal run artefacts (manifest + case CSV) and writes a self-contained folder:

    official_2025/<RUN>/
        测试用例模版.xlsx          10 official columns, <App>_R<req>_<seq> ids
        screenshots/<11digit>_<id>.png
        screenshots.zip
        test-code/Test<App>.py     官方骨架：一个需求一个 test_<App>_R<req>()
        test-code/runner/          内部可运行实现（可选）
        manifest.json
        README.md

Official rules implemented here come from the 2025 赛题包
(`【测试用例】/【测试代码】/【测试截图】注意事项.docx` + `测试用例模版.xlsx`).
The 2026 rules are unknown; everything produced here is a 2025 baseline artefact.

Exit codes: 0 ok, 1 verification failed, 2 usage/precondition error.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
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

OFFICIAL_COLUMNS = [
    "测试用例编号",
    "模块名称",
    "需求编号",
    "用例说明",
    "前置条件",
    "执行步骤",
    "输入数据",
    "预期结果",
    "实际结果",
    "截图文件名",
]

# Verbatim from materials/赛题/2025-顺丰-省赛/test_SF.py — the rules state this
# function must not be modified, so it is copied as-is.
SCREENSHOT_FUNCTION = '''    @staticmethod
    def take_screenshot(driver, file_name):
        timestamp = datetime.now().strftime( "%H%M%S%d%f" )[:-3]
        timestamped_file_name = f"{timestamp}_{file_name}"
        screenshots_dir = "screenshots"
        if not os.path.exists( screenshots_dir ):
            os.makedirs( screenshots_dir )
        screenshot_file_path = os.path.join( screenshots_dir, timestamped_file_name )
        driver.save_screenshot( screenshot_file_path )
'''

CASE_ALIASES = {
    "case_id": ("case_id", "测试用例编号"),
    "title": ("title", "用例说明", "case_title"),
    "requirement": ("requirement_ids", "requirement", "需求编号", "req"),
    "preconditions": ("preconditions", "precondition", "前置条件"),
    "steps": ("steps", "执行步骤"),
    "data": ("test_data", "data", "输入数据"),
    "expected": ("expected", "预期结果"),
    "actual": ("actual", "实际结果"),
    "module": ("module", "模块名称"),
    "status": ("status",),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "gbk"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def load_cases(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(read_text(path).splitlines()))
    out: list[dict[str, str]] = []
    for raw in rows:
        item: dict[str, str] = {}
        for key, names in CASE_ALIASES.items():
            value = ""
            for name in names:
                if name in raw and raw[name] not in (None, ""):
                    value = str(raw[name]).strip()
                    break
            item[key] = value
        if item["case_id"]:
            out.append(item)
    return out


def normalise_requirement(value: str) -> str:
    """REQ-01 / REQ-1 / R1 / R001 / R001-R003 -> R001 (first token)."""
    token = re.split(r"[,;/|、\s]+", value.strip())[0] if value.strip() else ""
    token = token.upper()
    match = re.search(r"R(?:EQ)?[-_ ]?0*(\d+)", token)
    if match:
        return f"R{int(match.group(1)):03d}"
    digits = re.sub(r"\D", "", token)
    if digits:
        return f"R{int(digits):03d}"
    return "R999"


def normalise_app(value: str) -> str:
    app = re.sub(r"[^0-9A-Za-z]+", "", value or "")
    return app or "App"


def official_id(app: str, req: str, seq: int) -> str:
    return f"{app}_{req}_{seq:03d}"


def pick_image(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Official screenshots show the whole browser window: prefer viewport."""
    priority = {"screenshot": 0, "fullpage-screenshot": 1, "element-screenshot": 2}
    images = [e for e in entries if e.get("kind") in priority]
    if not images:
        return None
    images.sort(key=lambda e: (priority[e["kind"]], str(e.get("created_at") or "")))
    # latest among the best kind
    best_kind = priority[images[0]["kind"]]
    same = [e for e in images if priority[e["kind"]] == best_kind]
    return sorted(same, key=lambda e: str(e.get("created_at") or ""))[-1]


def official_timestamp(created_at: str, source_name: str = "") -> str:
    """HHMMSS + DD + FFF, mirroring the official take_screenshot().

    Evidence timestamps have second resolution, so the millisecond part is taken
    from the source file name when it carries one (`...-142.png`).
    """
    try:
        dt = datetime.fromisoformat(str(created_at))
    except Exception:
        dt = datetime.now()
    millis = dt.microsecond // 1000
    match = re.search(r"-(\d{3})(?:\.[A-Za-z]+)?$", source_name or "")
    if match:
        millis = int(match.group(1))
    return dt.strftime("%H%M%S") + dt.strftime("%d") + f"{millis:03d}"


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
    module_default = args.module or ""
    evidence_by_case: dict[str, list[dict[str, Any]]] = {}
    for e in manifest.get("evidence", []):
        if e.get("run_id") == args.run_id:
            evidence_by_case.setdefault(str(e.get("case_id")), []).append(e)

    # --- assign official ids -------------------------------------------------
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
            multi_req.append({"case_id": case["case_id"], "requirement_ids": case["requirement"],
                              "chosen": req})
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
        mapping.append({"case_id": case["case_id"], "official_id": cid,
                        "requirement": req, "screenshot": shot,
                        "source_evidence": image["evidence_id"] if image else ""})

    if pkg.exists():
        shutil.rmtree(pkg)
    (pkg / "screenshots").mkdir(parents=True, exist_ok=True)
    (pkg / "test-code").mkdir(parents=True, exist_ok=True)

    # --- screenshots ---------------------------------------------------------
    copied: list[dict[str, str]] = []
    for item in mapping:
        if not item["screenshot"]:
            continue
        src = None
        for e in evidence_by_case.get(item["case_id"], []):
            if e["evidence_id"] == item["source_evidence"]:
                src = ROOT / e["path"]
                break
        if src is None or not src.is_file():
            continue
        dst = pkg / "screenshots" / item["screenshot"]
        shutil.copy2(src, dst)
        copied.append({"file": item["screenshot"], "source": src.relative_to(ROOT).as_posix(),
                       "sha256": sha256(dst), "bytes": dst.stat().st_size})

    # --- xlsx ----------------------------------------------------------------
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(OFFICIAL_COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="F2F2F2")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in rows:
        ws.append([row[c] for c in OFFICIAL_COLUMNS])
    widths = [22, 18, 10, 34, 30, 44, 30, 34, 34, 30]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    for r in ws.iter_rows(min_row=2):
        for cell in r:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A2"
    xlsx_path = pkg / "测试用例模版.xlsx"
    wb.save(xlsx_path)
    wb.close()

    # --- official code skeleton ---------------------------------------------
    reqs: list[str] = []
    for row in rows:
        if row["需求编号"] not in reqs:
            reqs.append(row["需求编号"])
    by_req: dict[str, list[str]] = {r: [] for r in reqs}
    for row in rows:
        by_req[row["需求编号"]].append(row["测试用例编号"])

    body: list[str] = []
    for req in reqs:
        ids = by_req[req]
        examples = [m for m in mapping if m["requirement"] == req]
        body.append(f"    def test_{app}_{req}(self, driver):")
        body.append(f'        """需求 {req}：{len(ids)} 条用例 {", ".join(ids)}。"""')
        for item in examples:
            title = next((r["用例说明"] for r in rows if r["测试用例编号"] == item["official_id"]), "")
            body.append(f"        # 用例 {item['official_id']}：{title}")
            body.append(f'        # self.take_screenshot(driver, "{item["official_id"]}")')
        body.append("        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次")
        body.append(f"        #       self.take_screenshot(driver, \"{ids[0]}\")")
        body.append("        raise NotImplementedError(\"补全官方模板 test-code-start/end 之间的代码\")")
        body.append("")

    code = f'''import os
from datetime import datetime
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


@pytest.fixture( scope="function" )
def driver():
    # 提交最终代码脚本时，请将驱动路径换回官方路径"C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chromedriver.exe"
    service = Service(
        executable_path=r"C:\\Program Files\\Google\\Chrome\\Application\\chromedriver.exe" )
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=service, options=options)
    driver.get( "{args.target or run.get('target', '')}" )
    driver.maximize_window()
    driver.implicitly_wait( 10 )
    yield driver
    driver.quit()


class Test{app}:

    # test-code-start

{chr(10).join(body)}
    # test-code-end

{SCREENSHOT_FUNCTION}'''
    code_path = pkg / "test-code" / f"Test{app}.py"
    code_path.write_text(code, encoding="utf-8", newline="\n")

    # --- internal runnable code (optional) -----------------------------------
    if args.with_runner:
        runner = pkg / "test-code" / "runner"
        runner.mkdir(parents=True, exist_ok=True)
        tests_dir = runner / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        conftest = ROOT / "tests" / "conftest.py"
        if conftest.is_file():
            shutil.copy2(conftest, tests_dir / "conftest.py")
        for rel in ("tests/pages", "tests/generated"):
            src = ROOT / rel
            if src.is_dir():
                shutil.copytree(src, runner / rel, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for rel in ("pytest.ini", "requirements.txt", "tools/evidence.py", "tools/versioning.py"):
            src = ROOT / rel
            if src.is_file():
                dest = runner / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

    # --- screenshots.zip -----------------------------------------------------
    zip_path = pkg / "screenshots.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(p.name for p in (pkg / "screenshots").glob("*.png")):
            info = zipfile.ZipInfo(filename=f"screenshots/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, (pkg / "screenshots" / name).read_bytes())

    # --- README + manifest ---------------------------------------------------
    missing_shots = [m["official_id"] for m in mapping if not m["screenshot"]]
    readme = f"""# 2025 官方格式导出（{args.run_id}）

本目录按 **2025 赛项**官方材料导出：

- 用例表：`测试用例模版.xlsx`，10 列，编号 `<App>_R<需求号>_<序号>`
- 截图：`screenshots/`，命名 `<11位时间戳>_<用例编号>.png`，另附 `screenshots.zip`
- 代码骨架：`test-code/Test{app}.py`，`# test-code-start` / `# test-code-end` 之间按**需求**一个 `test_{app}_R<req>()`

## 边界声明

- 依据来自 2025 赛题包（`【测试用例】/【测试代码】/【测试截图】注意事项.docx` + `测试用例模版.xlsx`）。
- **2026 规则未获取**，本包不声称符合 2026 官方要求。
- 代码骨架中的 `take_screenshot` 与官方模板逐字一致（规则要求不得修改）。
- 每条用例对应的截图来自内部运行的真实证据，未重绘、未伪造；缺少证据的用例记为：{', '.join(missing_shots) if missing_shots else '无'}。

生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}
"""
    (pkg / "README.md").write_text(readme, encoding="utf-8")

    files = []
    for path in sorted(pkg.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append({"path": path.relative_to(pkg).as_posix(), "sha256": sha256(path),
                          "bytes": path.stat().st_size})
    payload = {
        "schema_version": "1.0",
        "profile": "official-2025",
        "official_format_confirmed": "2025-baseline-only",
        "official_format_note": "依据 2025 赛题包；2026 官方格式未确认",
        "run_id": args.run_id,
        "app": app,
        "target": run.get("target", ""),
        "case_count": len(rows),
        "requirement_count": len(reqs),
        "screenshot_count": len(copied),
        "cases_missing_screenshot": missing_shots,
        "cases_with_multiple_requirements": multi_req,
        "mapping": mapping,
        "files": files,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    (pkg / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({k: payload[k] for k in ("profile", "run_id", "app", "case_count",
                                              "requirement_count", "screenshot_count",
                                              "cases_missing_screenshot", "official_format_confirmed")},
                     ensure_ascii=False, indent=2))
    print(f"package: {pkg}")
    return 0


def verify(pkg: Path, emit: bool = True) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def add(code: str, severity: str, subject: str, message: str) -> None:
        findings.append({"code": code, "severity": severity, "subject": subject, "message": message})

    manifest_path = pkg / "manifest.json"
    if not manifest_path.is_file():
        result = {"ok": False, "verdict": "FAIL", "package": str(pkg),
                  "findings": [{"code": "MANIFEST_MISSING", "severity": "FAIL",
                                "subject": "manifest.json", "message": "manifest.json 缺失"}],
                  "finding_counts": {"FAIL": 1, "WARNING": 0},
                  "case_count": 0, "screenshot_count": 0}
        if emit:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = manifest.get("app", "")
    rows: list[dict[str, Any]] = []

    xlsx = pkg / "测试用例模版.xlsx"
    if not xlsx.is_file():
        add("XLSX_MISSING", "FAIL", "测试用例模版.xlsx", "官方用例表不存在")
    else:
        from openpyxl import load_workbook
        wb = load_workbook(xlsx)
        ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb.worksheets[0]
        header = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
        if header[:len(OFFICIAL_COLUMNS)] != OFFICIAL_COLUMNS:
            add("XLSX_HEADER", "FAIL", "测试用例模版.xlsx",
                f"列头不符合官方 10 列：{header[:10]}")
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] in (None, ""):
                continue
            rows.append(dict(zip(OFFICIAL_COLUMNS, [("" if v is None else str(v)) for v in row[:10]])))
        wb.close()
        if not rows:
            add("XLSX_EMPTY", "FAIL", "测试用例模版.xlsx", "用例表没有数据行")

    id_re = re.compile(rf"^{re.escape(app)}_R\d{{3}}_\d{{3}}$")
    seen: set[str] = set()
    for row in rows:
        cid = row["测试用例编号"]
        if not id_re.match(cid):
            add("CASE_ID_FORMAT", "FAIL", cid, f"编号不符合 {app}_R{{3位}}_{{3位}}")
        if cid in seen:
            add("CASE_ID_DUPLICATE", "FAIL", cid, "用例编号重复")
        seen.add(cid)
        if not row["需求编号"]:
            add("REQUIREMENT_EMPTY", "FAIL", cid, "需求编号为空")
        if not row["截图文件名"]:
            add("SCREENSHOT_FIELD_EMPTY", "FAIL", cid, "截图文件名为空")
            continue
        expected_name = re.compile(rf"^\d{{11}}_{re.escape(cid)}\.png$")
        if not expected_name.match(row["截图文件名"]):
            add("SCREENSHOT_NAME_FORMAT", "FAIL", cid,
                f"截图名不符合 <11位时间戳>_<用例编号>.png：{row['截图文件名']}")
        if not (pkg / "screenshots" / row["截图文件名"]).is_file():
            add("SCREENSHOT_MISSING", "FAIL", cid, f"截图文件不存在：{row['截图文件名']}")

    # one screenshot per case
    files = sorted(p.name for p in (pkg / "screenshots").glob("*.png"))
    owners: dict[str, int] = {}
    for name in files:
        owners[name] = owners.get(name, 0) + 1
        if name.rsplit("_", 2)[-2:] and not name.endswith(".png"):
            add("SCREENSHOT_GENERIC", "WARNING", name, "非 png")
    if len(files) != len(set(files)):
        add("SCREENSHOT_DUPLICATE_NAME", "FAIL", "screenshots", "截图文件名重复")
    if rows and len(files) != len(rows):
        add("SCREENSHOT_COUNT", "FAIL", "screenshots",
            f"截图数 {len(files)} 与用例数 {len(rows)} 不一致（官方要求一条用例一张）")

    zip_path = pkg / "screenshots.zip"
    if not zip_path.is_file():
        add("ZIP_MISSING", "FAIL", "screenshots.zip", "截图压缩包不存在")
    else:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
            bad = [n for n in names if not n.startswith("screenshots/")]
            if bad:
                add("ZIP_STRUCTURE", "FAIL", "screenshots.zip",
                    f"{len(bad)} 个条目不在 screenshots/ 下（官方要求直接打包该文件夹）")
            if len(names) != len(files):
                add("ZIP_COUNT", "FAIL", "screenshots.zip",
                    f"zip 条目 {len(names)} 与截图文件数 {len(files)} 不一致")
        except zipfile.BadZipFile:
            add("ZIP_CORRUPT", "FAIL", "screenshots.zip", "zip 无法解析")

    code = pkg / "test-code" / f"Test{app}.py"
    if not code.is_file():
        add("CODE_MISSING", "FAIL", f"Test{app}.py", "官方代码骨架不存在")
    else:
        try:
            text = code.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""
            add("CODE_ENCODING", "FAIL", f"Test{app}.py", "不是合法 UTF-8")
        if "# test-code-start" not in text or "# test-code-end" not in text:
            add("CODE_MARKERS", "FAIL", f"Test{app}.py", "缺少 test-code-start/end 标识")
        if "def take_screenshot(driver, file_name):" not in text:
            add("CODE_SCREENSHOT_FN", "FAIL", f"Test{app}.py", "缺少官方 take_screenshot")
        if 'datetime.now().strftime( "%H%M%S%d%f" )[:-3]' not in text:
            add("CODE_SCREENSHOT_BODY", "FAIL", f"Test{app}.py",
                "take_screenshot 与官方模板不一致（规则禁止修改）")
        reqs = []
        for row in rows:
            if row["需求编号"] not in reqs:
                reqs.append(row["需求编号"])
        funcs = re.findall(rf"def\s+(test_{re.escape(app)}_R\d{{3}})\s*\(", text)
        if sorted(funcs) != sorted(f"test_{app}_{r}" for r in reqs):
            add("CODE_FUNCTION_MAP", "FAIL", f"Test{app}.py",
                f"函数与需求不是一一对应：funcs={sorted(funcs)} reqs={reqs}")

    blocking = [f for f in findings if f["severity"] == "FAIL"]
    narrowed = manifest.get("cases_with_multiple_requirements") or []
    if narrowed:
        add("MULTI_REQUIREMENT_NARROWED", "WARNING", "需求编号",
            f"{len(narrowed)} 条内部用例回指多个需求，导出时只保留第一个；"
            "如需精确归属请提供 primary requirement")
        blocking = [f for f in findings if f["severity"] == "FAIL"]
    result = {
        "ok": not blocking,
        "verdict": "PASS" if not blocking else "FAIL",
        "profile": "official-2025",
        "package": str(pkg),
        "case_count": len(rows),
        "screenshot_count": len(files),
        "finding_counts": {"FAIL": len(blocking), "WARNING": len(findings) - len(blocking)},
        "findings": findings,
    }
    if emit:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="export / verify the 2025 official layout")
    parser.add_argument("--run-id")
    parser.add_argument("--app", default="")
    parser.add_argument("--cases", default="")
    parser.add_argument("--module", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--out", default="official_2025")
    parser.add_argument("--with-runner", action="store_true",
                        help="also copy the internal runnable test code into test-code/runner")
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
            parser.error("--app is required (official case id prefix, e.g. SF)")
        return build(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
