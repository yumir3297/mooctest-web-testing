#!/usr/bin/env python3
"""Generate the qualification samples for the pre-submission gate.

Every sample is a *self-contained* fake project under ``qualification/``:

    qualification/<polarity>/<name>/
        manifest.json          fake evidence manifest (schema 1.1)
        cases.csv              fake test case table
        requirements.csv       requirement list (only where useful)
        junit-summary.json     fake run_selenium summary
        junit.xml              fake JUnit report
        tests/test_sample.py   fake automation source
        evidence/...           real bytes, hashed for real (Pillow PNG + log)
        README.md              what is simulated + which gate must catch it

Nothing here touches ``evidence/manifest.json``: the real registry is only ever
read.  Run ``python qualification/make_samples.py`` to (re)build the samples.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
QUAL = ROOT / "qualification"

STAMP = "20261031T000000-000"


def iso(offset: int = 0) -> str:
    return datetime(2026, 10, 31, 0, 0, offset, tzinfo=timezone.utc).astimezone().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# low level writers
# --------------------------------------------------------------------------- #
def make_png(path: Path, label: str, color: tuple[int, int, int] = (230, 238, 248)) -> None:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (120, 72), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle([4, 4, 115, 30], outline=(40, 60, 90), width=2)
    draw.text((8, 40), label[:18], fill=(20, 20, 20))
    image.save(path)


def make_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def evidence_entry(sample_root: Path, run_id: str, case_id: str, path: Path, *,
                   kind: str = "screenshot", bucket: str = "raw",
                   caption: str = "样例证据", sha_override: str | None = None) -> dict:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    return {
        "evidence_id": "EV-" + hashlib.sha256(f"{run_id}|{path.name}".encode()).hexdigest()[:10],
        "run_id": run_id,
        "case_id": case_id,
        "kind": kind,
        "path": path.relative_to(sample_root).as_posix(),
        "bucket": bucket,
        "step": "final",
        "caption": caption,
        "created_at": iso(),
        "size_bytes": len(data),
        "sha256": sha_override or digest,
        "immutable": True,
        "meta": {},
    }


# --------------------------------------------------------------------------- #
# data builders
# --------------------------------------------------------------------------- #
CSV_HEADER = ("case_id,title,priority,requirement_ids,case_type,method,preconditions,"
              "test_data,steps,expected,actual,status,automation,evidence_required,"
              "executed_in_run,notes")


def csv_row(case_id: str, title: str, req: str, case_type: str, method: str,
            preconditions: str, data: str, steps: str, expected: str,
            automation: str = "", status: str = "待执行", run_id: str = "",
            evidence: str = "用例日志") -> str:
    fields = [case_id, title, "P0" if case_type == "positive" else "P1", req, case_type,
              method, preconditions, data, steps, expected, "", status, automation,
              evidence, run_id, "qualification sample"]
    escaped = []
    for field in fields:
        text = str(field)
        if any(ch in text for ch in ',"\n'):
            text = '"' + text.replace('"', '""') + '"'
        escaped.append(text)
    return ",".join(escaped)


def base_rows(prefix: str = "TC-SAMPLE", run_id: str = "") -> list[str]:
    return [
        csv_row(f"{prefix}-001", "新增一条合法待办", "R1", "positive", "等价类划分",
                "列表为空", "标题=Buy milk", "1. 打开页面;2. 输入 Buy milk 并回车",
                "列表只出现一条 Buy milk；计数为 1 item left",
                "tests/test_sample.py::test_add_valid", "已执行-通过", run_id, "元素截图"),
        csv_row(f"{prefix}-002", "拒绝空标题", "R2", "negative", "边界值分析",
                "列表为空", "标题=空字符串", "1. 打开页面;2. 不输入内容直接回车",
                "列表保持为空；不出现空标题条目", "", "待执行", run_id),
        csv_row(f"{prefix}-003", "拒绝纯空白标题", "R3", "boundary", "边界值分析",
                "列表为空", "标题=三个空格", "1. 打开页面;2. 输入三个空格;3. 回车",
                "列表保持为空；不产生空白条目", "", "待执行", run_id),
    ]


def base_manifest(run_id: str, cases: dict, *, status: str = "passed", meta: dict | None = None) -> dict:
    return {
        "schema_version": "1.1",
        "project": "mooctest-web-testing-qualification-sample",
        "created_at": iso(),
        "updated_at": iso(30),
        "runs": {
            run_id: {
                "run_id": run_id,
                "label": "qualification sample",
                "target": "https://example.invalid/qualification-sample",
                "started_at": iso(),
                "finished_at": iso(20) if status != "running" else None,
                "status": status,
                "stage": "executed" if status != "running" else "selenium",
                "environment": {
                    "python": "3.13.9",
                    "pytest": "9.1.1",
                    "selenium": "4.51.0",
                    "chrome": "Chrome 156.0.8078.74",
                    "chromedriver": "ChromeDriver 156.0.8078.80",
                    "target": "https://example.invalid/qualification-sample",
                },
                "notes": [{"at": iso(), "note": "synthetic qualification sample"}],
                "cases": cases,
                **({"meta": meta} if meta else {}),
            }
        },
        "evidence": [],
    }


def case_obj(case_id: str, title: str, status: str, *, evidence="auto",
             assertions=None, defects=None, expected: str = "", actual: str = "",
             meta: dict | None = None) -> dict:
    return {
        "case_id": case_id,
        "title": title,
        "status": status,
        "started_at": iso(),
        "finished_at": iso(10) if status in ("passed", "failed", "blocked", "skipped", "xfailed") else None,
        "expected": expected,
        "actual": actual,
        "steps": ["打开页面", "执行操作"],
        "assertions": assertions or ([{"name": "断言", "expected": "x", "actual": "x", "passed": True}]
                                     if status == "passed" else []),
        "evidence": evidence,
        "defects": defects or [],
        "log_path": None,
        "notes": [],
        "meta": meta or {},
    }


def junit_files(cases: list[tuple[str, str, str]]) -> tuple[str, dict]:
    """Return (xml text, summary dict) for ``[(name, status, message)]``."""
    failures = sum(1 for _, status, _ in cases if status == "failed")
    xfailed = sum(1 for _, status, _ in cases if status == "xfailed")
    skipped = sum(1 for _, status, _ in cases if status in ("skipped", "xfailed"))
    body = []
    for name, status, message in cases:
        if status == "passed":
            body.append(f'<testcase classname="tests.test_sample" name="{escape(name)}" time="0.10" />')
        elif status == "failed":
            body.append(
                f'<testcase classname="tests.test_sample" name="{escape(name)}" time="0.10">'
                f'<failure message="{escape(message)}">{escape(message)}</failure></testcase>')
        elif status == "xfailed":
            body.append(
                f'<testcase classname="tests.test_sample" name="{escape(name)}" time="0.10">'
                f'<skipped type="pytest.xfail" message="{escape(message)}" /></testcase>')
        else:
            body.append(
                f'<testcase classname="tests.test_sample" name="{escape(name)}" time="0.10">'
                f'<skipped message="{escape(message)}" /></testcase>')
    xml_text = ('<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests">'
                f'<testsuite name="pytest" errors="0" failures="{failures}" skipped="{skipped}" '
                f'tests="{len(cases)}" time="0.50" timestamp="2026-10-31T00:00:00">'
                + "".join(body) + "</testsuite></testsuites>")
    summary = {
        "run_id": "",
        "exit_code": 1 if failures else 0,
        "elapsed_seconds": 0.5,
        "timed_out": False,
        "junit": "junit.xml",
        "console_log": "console.log",
        "tests": len(cases),
        "failures": failures,
        "errors": 0,
        "skipped": skipped,
        "xfailed": xfailed,
        "cases": [
            {"name": name, "classname": "tests.test_sample", "time": 0.1,
             "status": status, "message": message}
            for name, status, message in cases
        ],
        "status": "failed" if failures else "passed",
    }
    return xml_text, summary


TEST_SOURCE_BASE = '''"""Qualification sample suite (synthetic, not a product test)."""


def test_add_valid():
    items = ["Buy milk"]
    assert items == ["Buy milk"]
'''

TEST_SOURCE_FIVE = '''"""Qualification sample suite with five automation functions."""


def test_case_1():
    assert 1 == 1


def test_case_2():
    assert 2 == 2


def test_case_3():
    assert 3 == 3


def test_case_4():
    assert 4 == 4


def test_case_5():
    assert 5 == 5
'''

TEST_SOURCE_NO_ASSERT = '''"""Qualification sample: a test that never asserts anything."""


def test_add_valid():
    print("executed without any assertion")
'''

TEST_SOURCE_POSITIVE = '''"""Qualification positive sample: one pass, one real product defect.

``_submit`` models the application: it keeps a whitespace-only title, which is
the defect reported in the manifest.
"""


def _submit(text):
    # product behaviour: only the empty string is rejected, whitespace is kept
    return [] if text == "" else [text]


def test_add_valid():
    assert _submit("Buy milk") == ["Buy milk"]


def test_reject_blank_title():
    assert _submit("   ") == []
'''


# --------------------------------------------------------------------------- #
# materialisation
# --------------------------------------------------------------------------- #
def materialize(polarity: str, name: str, spec: dict) -> Path:
    root = QUAL / polarity / name
    if root.exists():
        shutil.rmtree(root)
    (root / "tests").mkdir(parents=True)

    run_id = spec["run_id"]
    manifest = base_manifest(run_id, spec["cases"], status=spec.get("run_status", "passed"),
                             meta=spec.get("meta"))

    # --- evidence files ----------------------------------------------------
    entries = []
    for item in spec.get("evidence", []):
        bucket = item.get("bucket", "raw")
        case_id = item["case_id"]
        if bucket == "logs":
            path = root / "evidence" / "logs" / run_id / item["filename"]
            make_log(path, "sample log: case executed, assertion recorded\n")
        else:
            path = root / "evidence" / "raw" / run_id / case_id / item["filename"]
            make_png(path, item.get("label", case_id), item.get("color", (230, 238, 248)))
        entries.append(evidence_entry(root, run_id, case_id, path,
                                      kind=item.get("kind", "screenshot"),
                                      bucket=bucket,
                                      caption=item.get("caption", "样例证据"),
                                      sha_override=item.get("sha_override")))
    manifest["evidence"] = entries

    # --- case references ---------------------------------------------------
    for case in manifest["runs"][run_id]["cases"].values():
        if case.get("evidence") == "auto":
            case["evidence"] = [e["evidence_id"] for e in entries if e["case_id"] == case["case_id"]]
        for defect in case.get("defects") or []:
            if defect.get("evidence") == "auto":
                defect["evidence"] = [e["evidence_id"] for e in entries if e["case_id"] == case["case_id"]]

    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- cases.csv ---------------------------------------------------------
    rows = spec.get("csv_rows")
    csv_text = spec.get("csv_text")
    if csv_text is None:
        csv_text = CSV_HEADER + "\n" + "\n".join(rows or []) + ("\n" if rows else "")
    (root / "cases.csv").write_text(csv_text, encoding="utf-8-sig", newline="\n")

    if spec.get("requirements"):
        lines = ["requirement_id,title"] + [f"{rid},{title}" for rid, title in spec["requirements"]]
        (root / "requirements.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- junit -------------------------------------------------------------
    if spec.get("junit_cases"):
        xml_text, summary = junit_files(spec["junit_cases"])
        summary["run_id"] = run_id
        summary.update(spec.get("junit_overrides") or {})
        (root / "junit.xml").write_text(xml_text, encoding="utf-8", newline="\n")
        (root / "junit-summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- tests -------------------------------------------------------------
    (root / "tests" / "test_sample.py").write_text(
        spec.get("tests_source", TEST_SOURCE_BASE), encoding="utf-8", newline="\n")

    (root / "README.md").write_text(spec["readme"].strip() + "\n", encoding="utf-8", newline="\n")
    return root


# --------------------------------------------------------------------------- #
# samples
# --------------------------------------------------------------------------- #
def sample_specs() -> list[tuple[str, str, dict]]:
    samples: list[tuple[str, str, dict]] = []

    def base(run_id: str) -> dict:
        cases = {
            "TC-SAMPLE-001": case_obj(
                "TC-SAMPLE-001", "test_add_valid", "passed",
                expected="列表只出现一条 Buy milk；计数为 1 item left",
                actual="列表为 ['Buy milk']；计数 1 item left",
                meta={"requirement_ids": "R1", "case_type": "positive", "method": "等价类划分"}),
            "TC-SAMPLE-002": case_obj("TC-SAMPLE-002", "拒绝空标题", "not-run",
                                      evidence=[], expected="列表保持为空",
                                      meta={"requirement_ids": "R2", "case_type": "negative"}),
            "TC-SAMPLE-003": case_obj("TC-SAMPLE-003", "拒绝纯空白标题", "not-run",
                                      evidence=[], expected="列表保持为空",
                                      meta={"requirement_ids": "R3", "case_type": "boundary"}),
        }
        return {
            "run_id": run_id,
            "cases": cases,
            "csv_rows": base_rows(run_id=run_id),
            "requirements": [("R1", "新增待办"), ("R2", "空标题校验"), ("R3", "空白标题校验")],
            "evidence": [{"case_id": "TC-SAMPLE-001",
                          "filename": f"TC-SAMPLE-001__final__viewport__{STAMP}.png",
                          "label": "TC-SAMPLE-001 final"}],
            "junit_cases": [("test_add_valid", "passed", "")],
        }

    # 1 ---------------------------------------------------------------- empty
    spec = base("RUN-SAMPLE-EMPTYCASES")
    spec.update({
        "csv_rows": [],
        "readme": f"""
# empty-cases

模拟错误：执行记录看起来完整（1 个 passed 用例、JUnit 1 passed、证据齐全），
但用例表只有表头，没有任何用例。

预期拦截：**G1** `CASES_EMPTY`（delivery_verdict=FAIL，退出码 1）。
用例集为空时，“测试通过”无法被任何设计覆盖支撑。
""",
    })
    samples.append(("negative", "empty-cases", spec))

    # 2 -------------------------------------------------------- missing expected
    spec = base("RUN-SAMPLE-MISSINGEXPECTED")
    rows = base_rows(run_id=spec["run_id"])
    rows[0] = rows[0].replace("列表只出现一条 Buy milk；计数为 1 item left", "")
    spec.update({
        "csv_rows": rows,
        "readme": """
# missing-expected

模拟错误：TC-SAMPLE-001 的 `expected` 为空，用例没有可判定预期结果。

预期拦截：**G1** `CASE_EXPECTED_MISSING`（delivery_verdict=FAIL，退出码 1）。
""",
    })
    samples.append(("negative", "missing-expected", spec))

    # 3 ------------------------------------------------------- duplicate case id
    spec = base("RUN-SAMPLE-DUPLICATEID")
    rows = base_rows(run_id=spec["run_id"])
    rows.append(csv_row("TC-SAMPLE-001", "重复 ID 的另一条用例", "R2", "negative",
                        "等价类划分", "列表为空", "标题=空",
                        "1. 打开页面;2. 直接回车", "列表保持为空", "", "待执行"))
    spec.update({
        "csv_rows": rows,
        "readme": """
# duplicate-case-id

模拟错误：`TC-SAMPLE-001` 在同一个用例表中出现两次，用例身份不唯一，
证据与执行结果无法对应到唯一条目。

预期拦截：**G1** `CASE_ID_DUPLICATE`（delivery_verdict=FAIL，退出码 1）。
""",
    })
    samples.append(("negative", "duplicate-case-id", spec))

    # 4 ------------------------------------------------------------- no assert
    spec = base("RUN-SAMPLE-NOASSERTION")
    spec.update({
        "tests_source": TEST_SOURCE_NO_ASSERT,
        "readme": """
# no-assertion

模拟错误：`tests/test_sample.py::test_add_valid` 被执行了，但函数体只有 `print`，
没有任何 `assert` 或 `case_ctx.check(...)`。这个用例永远是“通过”。

预期拦截：**G2** `CASE_WITHOUT_ASSERTION`（delivery_verdict=FAIL，退出码 1）。
""",
    })
    samples.append(("negative", "no-assertion", spec))

    # 5 ------------------------------------------------- junit/manifest skew
    spec = base("RUN-SAMPLE-JUNITMISMATCH")
    cases = {}
    mixed_types = {1: "positive", 2: "negative", 3: "boundary", 4: "positive", 5: "negative"}
    for index in range(1, 6):
        cid = f"TC-SAMPLE-{index:03d}"
        cases[cid] = case_obj(cid, f"test_case_{index}", "passed",
                              meta={"requirement_ids": f"R{index}",
                                    "case_type": mixed_types[index]})
    spec.update({
        "cases": cases,
        "csv_rows": [
            csv_row(f"TC-SAMPLE-{i:03d}", f"自动化用例 {i}", f"R{i}", mixed_types[i],
                    "等价类划分", "列表为空", f"数据{i}", "1. 打开页面;2. 执行断言",
                    f"结果等于 {i}", f"tests/test_sample.py::test_case_{i}", "已执行-通过",
                    spec["run_id"])
            for i in range(1, 6)
        ],
        "evidence": [{"case_id": f"TC-SAMPLE-{i:03d}",
                      "filename": f"TC-SAMPLE-{i:03d}__final__viewport__{STAMP}.png",
                      "label": f"TC-SAMPLE-{i:03d}"} for i in range(1, 6)],
        "tests_source": TEST_SOURCE_FIVE,
        "junit_cases": [(f"test_case_{i}", "passed", "") for i in (1, 2, 3)],
        "requirements": [(f"R{i}", f"需求 {i}") for i in range(1, 6)],
        "readme": """
# junit-manifest-mismatch

模拟错误：manifest 记 5 个用例 passed，但 JUnit 只跑了 3 个（summary 与 xml 都是 3）。
pytest 退出码是 0，单看退出码完全看不出来。

预期拦截：**G2** `JUNIT_MANIFEST_COUNT_MISMATCH` 与 `MANIFEST_PASSED_WITHOUT_JUNIT`
（delivery_verdict=FAIL，退出码 1）。
""",
    })
    samples.append(("negative", "junit-manifest-mismatch", spec))

    # 6 ----------------------------------------------------- missing screenshot
    spec = base("RUN-SAMPLE-MISSINGEVIDENCE")
    spec["cases"]["TC-SAMPLE-001"]["evidence"] = []
    spec["evidence"] = []
    spec.update({
        "readme": """
# missing-screenshot

模拟错误：TC-SAMPLE-001 被标记 passed，但既没有截图、日志，也没有任何已登记证据。
“通过”结论无法复核。

预期拦截：**G3** `PASSED_CASE_WITHOUT_EVIDENCE`（delivery_verdict=FAIL，退出码 1）。
""",
    })
    samples.append(("negative", "missing-screenshot", spec))

    # 7 --------------------------------------------------------------- bad sha
    spec = base("RUN-SAMPLE-BADSHA")
    spec["evidence"] = [{
        "case_id": "TC-SAMPLE-001",
        "filename": f"TC-SAMPLE-001__final__viewport__{STAMP}.png",
        "label": "TC-SAMPLE-001 tampered",
        "sha_override": "0" * 64,
    }]
    spec.update({
        "readme": """
# bad-sha256

模拟错误：证据 PNG 是真实文件（在 `qualification/` 下生成，未登记进真实 manifest），
但 manifest 里的 sha256 被改成 `0000...`，模拟证据被替换/篡改。

预期拦截：**G3** `EVIDENCE_HASH_MISMATCH`（delivery_verdict=FAIL，退出码 1）。
哈希校验直接复用 `tools/evidence.py` 的 `verify_evidence()`。
""",
    })
    samples.append(("negative", "bad-sha256", spec))

    # 8 ---------------------------------------------------------- defect no repro
    spec = base("RUN-SAMPLE-DEFECTNOREPRO")
    spec["cases"] = {
        "TC-SAMPLE-001": case_obj("TC-SAMPLE-001", "test_add_valid", "passed",
                                  meta={"requirement_ids": "R1", "case_type": "positive"}),
        "TC-SAMPLE-002": case_obj(
            "TC-SAMPLE-002", "test_reject_blank_title", "failed",
            expected="提交三个空格时列表保持为空",
            actual="列表出现条目 '   '",
            assertions=[{"name": "空白标题被拒绝", "expected": "[]", "actual": "['   ']", "passed": False}],
            meta={"requirement_ids": "R2", "case_type": "negative", "failure_class": "ASSERT"},
            defects=[{
                "defect_id": "DEF-001",
                "title": "空白标题被接受",
                "severity": "major",
                "severity_rationale": "产生脏数据条目",
                "category": "APP",
                "status": "open",
                "description": "提交三个空格后列表出现空白条目",
                "environment": "",
                "preconditions": [],
                "repro_steps": [],
                "repro_status": "not-reproduced",
                "repro_count": 0,
                "expected": "列表保持为空",
                "actual": "列表出现 '   '",
                "evidence": "auto",
                "created_at": iso(),
            }]),
    }
    spec.update({
        "csv_rows": [
            csv_row("TC-SAMPLE-001", "新增一条合法待办", "R1", "positive", "等价类划分",
                    "列表为空", "标题=Buy milk", "1. 打开页面;2. 输入并回车",
                    "列表出现 Buy milk", "tests/test_sample.py::test_add_valid",
                    "已执行-通过", spec["run_id"]),
            csv_row("TC-SAMPLE-002", "拒绝纯空白标题", "R2", "negative", "边界值分析",
                    "列表为空", "标题=三个空格", "1. 打开页面;2. 提交三个空格",
                    "列表保持为空", "tests/test_sample.py::test_reject_blank_title",
                    "已执行-失败", spec["run_id"]),
            csv_row("TC-SAMPLE-003", "拒绝空标题", "R3", "boundary", "边界值分析",
                    "列表为空", "标题=空字符串", "1. 打开页面;2. 直接回车",
                    "列表保持为空", "", "待执行"),
        ],
        "tests_source": TEST_SOURCE_POSITIVE,
        "junit_cases": [("test_add_valid", "passed", ""),
                        ("test_reject_blank_title", "failed", "assert [] == ['   ']")],
        "evidence": [
            {"case_id": "TC-SAMPLE-001", "filename": f"TC-SAMPLE-001__final__viewport__{STAMP}.png"},
            {"case_id": "TC-SAMPLE-002", "filename": f"TC-SAMPLE-002__failure__viewport__{STAMP}.png",
             "label": "blank title accepted"},
        ],
        "readme": """
# defect-no-repro

模拟错误：一个 failed 用例挂了缺陷，但缺陷缺 `repro_steps`、`preconditions`、
`environment`——别人无法复现，也无法判断严重度是否合理。

预期拦截：**G3** `DEFECT_FIELD_MISSING`（delivery_verdict=FAIL，退出码 1）。
注意：这正是“产品缺陷 vs 不可信成果”的分界线——缺陷字段不全，交付结论不可信。
""",
    })
    samples.append(("negative", "defect-no-repro", spec))

    # 9 ------------------------------------------------------------ blocked run
    spec = base("RUN-SAMPLE-BLOCKED")
    spec.update({
        "cases": {},
        "run_status": "blocked",
        "junit_cases": None,
        "evidence": [],
        "readme": """
# blocked-run

模拟错误：环境/夹具阻塞，`run.status=blocked`、0 个用例、没有 JUnit。
历史审计 C5 的问题是这种运行曾经仍然 `exit 0`。

预期拦截：**G2** `RUN_STATUS_BLOCKED`（BLOCKED，退出码 2）。
阻塞运行必须非零退出，且不能被当成“通过”。
""",
    })
    samples.append(("negative", "blocked-run", spec))

    # 10 -------------------------------------------------------------- fake pass
    spec = base("RUN-SAMPLE-FAKEPASS")
    cases = {
        "TC-SAMPLE-001": case_obj("TC-SAMPLE-001", "test_add_valid", "passed"),
        "TC-SAMPLE-002": case_obj("TC-SAMPLE-002", "拒绝空标题", "passed"),
        "TC-SAMPLE-003": case_obj("TC-SAMPLE-003", "拒绝纯空白标题", "passed"),
    }
    spec.update({
        "cases": cases,
        "junit_cases": None,
        "evidence": [
            {"case_id": "TC-SAMPLE-001", "filename": f"TC-SAMPLE-001__final__viewport__{STAMP}.png"},
            {"case_id": "TC-SAMPLE-002", "filename": f"TC-SAMPLE-002__final__viewport__{STAMP}.png"},
            {"case_id": "TC-SAMPLE-003", "filename": f"TC-SAMPLE-003__final__viewport__{STAMP}.png"},
        ],
        "readme": """
# fake-pass

模拟错误：manifest 写 3 个用例 passed，但根本没有 JUnit 摘要和 JUnit XML。
pytest 从没跑过，通过结论是手写的。

预期拦截：**G2** `JUNIT_SUMMARY_MISSING`（delivery_verdict=FAIL，退出码 1）。
""",
    })
    samples.append(("negative", "fake-pass", spec))

    # 11 ------------------------------------------------------- unverifiable run
    spec = base("RUN-SAMPLE-UNVERIFIABLE")
    spec.update({
        "cases": {},
        "run_status": "running",
        "junit_cases": None,
        "evidence": [],
        "readme": """
# unverifiable-run

模拟错误：运行还停在 `running`，没有用例、没有 JUnit。既不能说通过，也不能说失败。

预期拦截：**G2** `EXECUTION_NOT_VERIFIABLE`（UNVERIFIED，退出码 3）。
这是 exit code 3 的真实触发路径：无法判定 ≠ 通过，也 ≠ 失败。
""",
    })
    samples.append(("negative", "unverifiable-run", spec))

    # 12 ----------------------------------------------------- no boundary type
    spec = base("RUN-SAMPLE-NOBOUNDARY")
    rows = base_rows(run_id=spec["run_id"])
    rows[2] = rows[2].replace(",boundary,", ",state,")
    spec.update({
        "csv_rows": rows,
        "readme": """
# no-boundary-coverage

模拟错误：用例表有 positive / negative，但没有 boundary 用例（类型列改成 state）。

预期拦截：**G1** `CASE_TYPE_COVERAGE_MISSING`（delivery_verdict=FAIL，退出码 1）。
""",
    })
    samples.append(("negative", "no-boundary-coverage", spec))

    # ---------------------------------------------------------------- positive
    defect = {
        "defect_id": "DEF-001",
        "title": "空白标题被接受并渲染为待办条目",
        "severity": "major",
        "severity_rationale": "违反输入校验规则并产生脏数据，但无数据丢失、无安全影响",
        "category": "APP",
        "status": "confirmed",
        "description": "在新增输入框提交三个空格后，列表出现一个空白条目，计数变为 1 item left。",
        "environment": "Chrome 156.0.8078.74 / ChromeDriver 156.0.8078.80 / Windows 11 / pytest 9.1.1",
        "preconditions": ["列表为空（localStorage 已清空）"],
        "repro_steps": ["打开待办页面", "在新增输入框输入三个空格", "按 Enter 提交"],
        "repro_status": "reproduced",
        "repro_count": 2,
        "expected": "空白标题被拒绝，列表保持为空",
        "actual": "列表出现空白条目，计数显示 1 item left",
        "evidence": "auto",
        "created_at": iso(),
    }

    pos_cases = {
        "TC-SAMPLE-001": case_obj("TC-SAMPLE-001", "test_add_valid", "passed",
                                  meta={"requirement_ids": "R1", "case_type": "positive"}),
        "TC-SAMPLE-002": case_obj(
            "TC-SAMPLE-002", "test_reject_blank_title", "failed",
            expected="列表保持为空", actual="列表出现空白条目 '   '",
            assertions=[{"name": "空白标题被拒绝", "expected": "[]", "actual": "['   ']", "passed": False}],
            meta={"requirement_ids": "R2", "case_type": "negative", "failure_class": "ASSERT"},
            defects=[deepcopy(defect)]),
        "TC-SAMPLE-003": case_obj("TC-SAMPLE-003", "拒绝空标题", "not-run",
                                  evidence=[], expected="列表保持为空",
                                  meta={"requirement_ids": "R3", "case_type": "boundary"}),
    }

    def positive_spec(run_id: str, status: str) -> dict:
        cases = deepcopy(pos_cases)
        cases["TC-SAMPLE-002"]["defects"][0]["status"] = status
        return {
            "run_id": run_id,
            "cases": cases,
            "csv_rows": [
                csv_row("TC-SAMPLE-001", "新增一条合法待办", "R1", "positive", "等价类划分",
                        "列表为空", "标题=Buy milk", "1. 打开页面;2. 输入 Buy milk 并回车",
                        "列表只出现一条 Buy milk；计数为 1 item left",
                        "tests/test_sample.py::test_add_valid", "已执行-通过", run_id, "元素截图"),
                csv_row("TC-SAMPLE-002", "拒绝纯空白标题", "R2", "negative", "边界值分析",
                        "列表为空", "标题=三个空格", "1. 打开页面;2. 提交三个空格",
                        "列表保持为空；不产生空白条目",
                        "tests/test_sample.py::test_reject_blank_title", "已执行-失败", run_id, "失败截图"),
                csv_row("TC-SAMPLE-003", "拒绝空标题", "R3", "boundary", "边界值分析",
                        "列表为空", "标题=空字符串", "1. 打开页面;2. 直接回车",
                        "列表保持为空", "", "待执行", "", "用例日志"),
            ],
            "requirements": [("R1", "新增待办"), ("R2", "空白标题校验"), ("R3", "空标题校验")],
            "tests_source": TEST_SOURCE_POSITIVE,
            "junit_cases": [("test_add_valid", "passed", ""),
                            ("test_reject_blank_title", "failed",
                             "assert [] == ['   ']  # 产品缺陷：空白标题被接受")],
            "evidence": [
                {"case_id": "TC-SAMPLE-001", "filename": f"TC-SAMPLE-001__final__viewport__{STAMP}.png"},
                {"case_id": "TC-SAMPLE-002",
                 "filename": f"TC-SAMPLE-002__failure__viewport__{STAMP}.png",
                 "label": "blank title accepted", "caption": "失败时视口截图"},
                {"case_id": "TC-SAMPLE-002",
                 "filename": f"TC-SAMPLE-002__failure__fullpage__{STAMP}.png",
                 "label": "blank title fullpage", "kind": "fullpage-screenshot",
                 "caption": "失败时整页截图"},
            ],
        }

    spec = positive_spec("RUN-SAMPLE-DEFECTREPORTED", "confirmed")
    spec["readme"] = """
# defect-reported  （正向样本）

场景：一个用例 failed，同时登记了一条**字段完整、已确认**的产品缺陷
（严重度+依据、类别、环境、前置条件、复现步骤、预期/实际、2 张证据截图）。

期望：
- `test_verdict=FAIL`（产品确实没通过这条用例）
- `delivery_verdict=PASS`（这批测试成果可信、可交付）
- 退出码 0

这就是“测试发现 Bug ≠ 测试成果不可信”的分界：缺陷可复现、证据齐全，
失败原因被准确定性，交付结论不受影响。

> 样本 manifest 没有写 `meta.ai_use_confirmed`：G0 会记一条 advisory UNVERIFIED，
> 只说明“AI 使用合规未声明”，不阻断本地演练，也不代表官方允许 AI。
"""
    samples.append(("positive", "defect-reported", spec))

    spec = positive_spec("RUN-SAMPLE-SUSPECTED", "suspected")
    spec["readme"] = """
# suspected-defect  （正向样本）

场景同 `defect-reported`，但缺陷状态是 `suspected`（尚未复核）。

期望：
- `test_verdict=FAIL`
- `delivery_verdict=WARNING`（允许交付，但报告必须标注结论不确定）
- 退出码 0
- findings 中包含 `DEFECT_STATUS_UNCONFIRMED`（WARNING）

门禁不会把 `suspected` 自动升级成 `confirmed`。
"""
    samples.append(("positive", "suspected-defect", spec))

    return samples


def build_package_samples() -> list[Path]:
    """Build a valid submission package and a corrupted copy (G4 fixtures).

    ``good/``  – structure, xlsx, zip and every sha256 are consistent.
    ``broken/`` – one file is modified after the package manifest was written,
                  so the recorded hash no longer matches.
    """
    import zipfile

    from openpyxl import Workbook

    base = QUAL / "package-sample"
    if base.exists():
        shutil.rmtree(base)
    source = QUAL / "positive" / "defect-reported"
    run_id = "RUN-SAMPLE-DEFECTREPORTED"

    submission = base / "good" / "submission" / run_id
    for directory in ("test-code", "screenshots", "reports"):
        (submission / directory).mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "test-cases"
    sheet.append(["case_id", "title", "priority", "requirement_ids", "case_type",
                  "method", "preconditions", "test_data", "steps", "expected", "status"])
    sheet.append(["TC-SAMPLE-001", "新增一条合法待办", "P0", "R1", "positive", "等价类划分",
                  "列表为空", "标题=Buy milk", "1. 打开页面;2. 输入并回车",
                  "列表出现 Buy milk", "已执行-通过"])
    workbook.save(submission / "test-cases.xlsx")

    shutil.copy2(source / "tests" / "test_sample.py", submission / "test-code" / "test_sample.py")
    shutil.copy2(source / "junit.xml", submission / "reports" / "junit.xml")
    screenshot = next((source / "evidence" / "raw" / run_id / "TC-SAMPLE-002").glob("*.png"))
    shutil.copy2(screenshot, submission / "screenshots" / "TC-SAMPLE-002.png")

    entries = []
    for path in sorted(submission.rglob("*")):
        if not path.is_file() or path.name in ("submission.zip", "manifest.json"):
            continue
        data = path.read_bytes()
        entries.append({
            "path": path.relative_to(submission).as_posix(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "case_id": "TC-SAMPLE-001",
            "source": "qualification package sample",
        })

    archive = submission / "submission.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            zf.write(submission / entry["path"], arcname=entry["path"])
    data = archive.read_bytes()
    entries.append({"path": "submission.zip", "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data), "case_id": "", "source": "qualification package sample"})

    package_manifest = {"schema_version": "1.0", "run_id": run_id,
                        "official_format_confirmed": False, "files": entries}
    (submission / "manifest.json").write_text(
        json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    broken = base / "broken" / "submission" / run_id
    shutil.copytree(submission, broken)
    tampered = broken / "screenshots" / "TC-SAMPLE-002.png"
    original = tampered.read_bytes()
    make_png(tampered, "tampered after packaging", (250, 220, 220))
    assert tampered.read_bytes() != original
    (base / "README.md").write_text(
        """
# package-sample  （G4 fixture）

- `good/submission/<RUN>/`：结构齐全、xlsx 可打开、zip 可解压、manifest.json 中每个文件
  sha256 与磁盘一致 → **G4 PASS**
- `broken/submission/<RUN>/`：打包后 `screenshots/TC-SAMPLE-002.png` 被替换，哈希不再匹配
  → **G4 FAIL**（`PACKAGE_HASH_MISMATCH`）

这两个目录只用于验证 `--submission` 分支，不属于任何真实交付包，
`official_format_confirmed=false` 标明格式未经官方确认。
""".strip() + "\n", encoding="utf-8")
    return [base]


def main() -> int:
    built: list[Path] = []
    for polarity, name, spec in sample_specs():
        built.append(materialize(polarity, name, spec))
    built.extend(build_package_samples())
    for root in built:
        print(root.relative_to(ROOT).as_posix())
    print(f"\n{len(built)} samples generated")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
