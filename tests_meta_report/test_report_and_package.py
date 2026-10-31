"""Self-tests for ``tools/generate_report.py`` and ``tools/package_submission.py``.

These tests exercise the real deliverables (report for RUN-AUDIT-20261030-02 and
its submission package) through the CLI, in temporary directories, so they never
write into ``reports/`` or ``submission/``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT_TOOL = ROOT / "tools" / "generate_report.py"
PACKAGE_TOOL = ROOT / "tools" / "package_submission.py"
RUN_ID = "RUN-AUDIT-20261030-02"
JUNIT_SUMMARY = ROOT / "reports" / "executions" / RUN_ID / "junit-summary.json"


def _run(args: list[str], cwd: Path = ROOT) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, *args], cwd=str(cwd), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env)
    return proc.returncode, proc.stdout, proc.stderr


def _json(stdout: str) -> dict:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - diagnostic path
        raise AssertionError(f"stdout is not JSON: {exc}\n{stdout[:2000]}") from exc


def _write_fake_manifest(path: Path, cases: dict, *, status: str = "passed") -> None:
    manifest = {
        "schema_version": "1.1",
        "runs": {
            "FAKE-RUN-1": {
                "run_id": "FAKE-RUN-1",
                "target": "https://example.invalid/",
                "status": status,
                "stage": "executed",
                "started_at": "2026-10-31T00:00:00+08:00",
                "finished_at": "2026-10-31T00:00:05+08:00",
                "environment": {"python": "3.13.9", "platform": "test-os",
                                "target": "https://example.invalid/"},
                "notes": [],
                "cases": cases,
            }
        },
        "evidence": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture(scope="module")
def real_report(tmp_path_factory) -> tuple[dict, Path]:
    out_dir = tmp_path_factory.mktemp("report")
    rc, stdout, stderr = _run([
        str(REPORT_TOOL), "--run-id", RUN_ID, "--title", "自测报告",
        "--out-dir", str(out_dir), "--junit-summary", str(JUNIT_SUMMARY),
    ])
    assert rc == 0, f"generate_report exit={rc}\nstdout={stdout}\nstderr={stderr}"
    payload = _json(stdout)
    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    return report, payload


@pytest.fixture(scope="module")
def packages(tmp_path_factory, real_report) -> dict:
    report_dir = real_report[1]["out_dir"]
    out_a = tmp_path_factory.mktemp("pkg-a")
    out_b = tmp_path_factory.mktemp("pkg-b")
    results = []
    for out in (out_a, out_b):
        rc, stdout, stderr = _run([
            str(PACKAGE_TOOL), "--run-id", RUN_ID, "--report-dir", report_dir,
            "--out", str(out), "--json",
        ])
        assert rc == 0, f"package_submission exit={rc}\nstdout={stdout}\nstderr={stderr}"
        results.append(_json(stdout))
    return {"a": results[0], "b": results[1],
            "package_dir": Path(results[0]["package_dir"])}


# --------------------------------------------------------------------------- #
# report generator
# --------------------------------------------------------------------------- #
def test_report_never_uses_assertion_booleans_as_case_expected(real_report):
    report, _ = real_report
    assert report["cases"], "run should have cases"
    offenders = {c["case_id"]: c["expected"] for c in report["cases"]
                 if str(c["expected"]).strip() in {"True", "False", "None"}}
    assert not offenders, f"case-level expected must not be an assertion value: {offenders}"
    case_001 = next(c for c in report["cases"] if c["case_id"] == "TC-TODO-001")
    assert case_001["expected"] == ""
    assert case_001["expected_source"] == "assertions"
    assert case_001["expected_raw"] == "True"
    assert len(case_001["assertions"]) == 3
    markdown = Path(report["artifacts"]["markdown"]).read_text(encoding="utf-8")
    assert "见断言明细（3 条断言）" in markdown
    assert "预期：True" not in markdown


def test_report_environment_lists_chrome_and_chromedriver(real_report):
    report, payload = real_report
    env = report["environment"]
    for field in ("os", "platform", "python", "selenium", "pytest", "chrome",
                  "chromedriver", "node", "target"):
        assert field in env, f"missing environment field: {field}"
    assert env["chrome"], "chrome row must not be empty"
    assert env["chromedriver"], "chromedriver row must not be empty"
    assert report["environment_meta"]["chrome"]["label"] == "Chrome"
    probe = report["environment_probe"]
    assert probe is not None
    assert probe["chrome"] and not probe["chrome"].startswith("<")
    assert probe["chromedriver"] and not probe["chromedriver"].startswith("<")
    # The 2026-10-30 run record predates the v2 environment snapshot: the field is
    # rendered as 未采集 instead of being dropped, and the probe is labelled separately.
    assert report["environment_meta"]["chrome"]["source"] == "missing"
    assert report["environment_meta"]["chromedriver"]["source"] == "missing"
    assert "chrome" in payload["environment_missing"]
    assert "chromedriver" in payload["environment_missing"]
    assert probe["probe_kind"] == "report-time"
    markdown = Path(report["artifacts"]["markdown"]).read_text(encoding="utf-8")
    assert "| Chrome |" in markdown and "| ChromeDriver |" in markdown


def test_report_uses_run_scoped_case_table_only(real_report):
    report, _ = real_report
    table = report["case_table"]
    assert table["found"] is False, "no CSV declares executed_in_run for this run"
    assert table["path"] is None
    assert RUN_ID in table["reason"]
    assert report["strategy"]["methods"] == []
    assert report["strategy"]["design_source"] == "none"
    inspected = [item["run_tokens"] for item in table["inspected"]]
    assert all(RUN_ID not in tokens for tokens in inspected)


def test_report_json_exposes_all_sections(real_report):
    report, _ = real_report
    for key in ("scope", "environment", "environment_probe", "case_table", "strategy",
                "summary", "cases", "defects", "coverage", "visual", "evidence",
                "junit", "junit_counts", "quality_gate", "gate", "limitations"):
        assert key in report, f"report.json missing section: {key}"
    assert report["quality_gate"]["found"] is False
    assert report["quality_gate"]["message"] == "本次未运行质量门禁"
    assert report["gate"]["enabled"] is True
    assert report["gate"]["verdict"] in {"PASS", "WARNING"}
    assert report["gate"]["counts"].get("FAIL", 0) == 0
    assert report["summary"]["case_total"] == 8
    assert report["summary"]["xfailed"] == 1
    assert report["summary"]["pass_rate"] == 1.0
    assert set(report["evidence"]) >= {"checked", "ok", "missing", "mismatched",
                                       "cross_run", "unscoped"}


def test_strategy_and_requirement_coverage_come_from_case_table(tmp_path):
    import csv as _csv

    project = tmp_path / "meta-project"
    _write_fake_manifest(project / "evidence" / "manifest.json", {
        "TC-META-001": {
            "case_id": "TC-META-001", "title": "新增待办", "status": "passed",
            "expected": "列表出现 Buy milk", "actual": "断言通过", "steps": ["输入并回车"],
            "assertions": [{"name": "a1", "expected": "Buy milk", "actual": "Buy milk",
                            "passed": True}],
            "evidence": [], "defects": [], "log_path": None, "meta": {},
        },
        "TC-META-002": {
            "case_id": "TC-META-002", "title": "删除待办", "status": "not-run",
            "expected": "列表为空", "actual": "", "steps": [], "assertions": [],
            "evidence": [], "defects": [], "log_path": None, "meta": {},
        },
    })
    csv_path = tmp_path / "meta-cases.csv"
    header = ["case_id", "title", "priority", "requirement_ids", "case_type", "method",
              "preconditions", "test_data", "steps", "expected", "actual", "status",
              "automation", "evidence_required", "executed_in_run", "notes"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerow({"case_id": "TC-META-001", "title": "新增待办", "priority": "P0",
                         "requirement_ids": "REQ-01", "case_type": "positive",
                         "method": "边界值", "preconditions": "空列表",
                         "test_data": "Buy milk", "steps": "1. 输入并回车",
                         "expected": "列表出现 Buy milk", "actual": "",
                         "status": "passed", "automation": "", "evidence_required": "截图",
                         "executed_in_run": "RUN-META-1", "notes": ""})
        writer.writerow({"case_id": "TC-META-002", "title": "删除待办", "priority": "P1",
                         "requirement_ids": "REQ-02", "case_type": "negative",
                         "method": "判定表", "preconditions": "一条记录",
                         "test_data": "Delete me", "steps": "1. 删除",
                         "expected": "列表为空", "actual": "", "status": "not-run",
                         "automation": "", "evidence_required": "日志",
                         "executed_in_run": "RUN-META-1", "notes": ""})

    rc, stdout, stderr = _run([
        str(REPORT_TOOL), "--run-id", "FAKE-RUN-1",
        "--cases", str(csv_path),
        "--manifest", str(project / "evidence" / "manifest.json"),
        "--project-root", str(project),
        "--reports-root", str(project / "reports"),
        "--out-dir", str(project / "out"),
        "--no-gate", "--no-env-probe",
    ])
    assert rc == 0, f"{stdout}\n{stderr}"
    report = json.loads((project / "out" / "report.json").read_text(encoding="utf-8"))
    methods = {item["method"]: item["count"] for item in report["strategy"]["methods"]}
    assert methods == {"边界值": 1, "判定表": 1}
    assert report["strategy"]["design_source"] == "case-table"
    assert report["case_table"]["source"] == "explicit"
    assert report["case_table"]["found"] is True
    requirements = {item["requirement_id"]: item for item in report["coverage"]["requirements"]}
    assert set(requirements) == {"REQ-01", "REQ-02"}
    assert requirements["REQ-01"]["executed"] is True
    assert requirements["REQ-02"]["executed"] is False
    assert report["coverage"]["requirements_without_execution"] == ["REQ-02"]


# --------------------------------------------------------------------------- #
# gate
# --------------------------------------------------------------------------- #
def test_gate_fails_when_junit_is_missing(tmp_path):
    project = tmp_path / "fake-project"
    _write_fake_manifest(project / "evidence" / "manifest.json", {
        "TC-FAKE-001": {
            "case_id": "TC-FAKE-001", "title": "test_fake", "status": "passed",
            "expected": "列表出现一条记录", "actual": "断言通过",
            "steps": ["打开页面"], "assertions": [
                {"name": "a1", "expected": "ok", "actual": "ok", "passed": True}],
            "evidence": [], "defects": [], "log_path": None, "meta": {},
        }
    })
    (project / "reports" / "executions" / "FAKE-RUN-1").mkdir(parents=True)
    rc, stdout, stderr = _run([
        str(REPORT_TOOL), "--run-id", "FAKE-RUN-1",
        "--manifest", str(project / "evidence" / "manifest.json"),
        "--project-root", str(project),
        "--reports-root", str(project / "reports"),
        "--out-dir", str(project / "out"),
        "--no-env-probe",
    ])
    assert rc != 0, f"gate must fail without JUnit\nstdout={stdout}\nstderr={stderr}"
    assert rc == 1
    payload = _json(stdout)
    assert payload["gate"]["verdict"] == "FAIL"
    codes = {f["code"] for f in payload["findings"]}
    assert "JUNIT_MISSING" in codes


def test_gate_blocks_when_run_has_no_cases(tmp_path):
    project = tmp_path / "empty-project"
    _write_fake_manifest(project / "evidence" / "manifest.json", {})
    rc, stdout, _ = _run([
        str(REPORT_TOOL), "--run-id", "FAKE-RUN-1",
        "--manifest", str(project / "evidence" / "manifest.json"),
        "--project-root", str(project),
        "--reports-root", str(project / "reports"),
        "--out-dir", str(project / "out"),
        "--no-env-probe",
    ])
    assert rc == 2, stdout
    payload = _json(stdout)
    assert payload["gate"]["verdict"] == "BLOCKED"
    assert "NO_CASES" in {f["code"] for f in payload["findings"]}


def test_no_gate_keeps_legacy_exit_code(tmp_path):
    project = tmp_path / "legacy-project"
    _write_fake_manifest(project / "evidence" / "manifest.json", {
        "TC-FAKE-001": {
            "case_id": "TC-FAKE-001", "title": "test_fake", "status": "passed",
            "expected": "ok", "actual": "ok", "steps": [], "assertions": [],
            "evidence": [], "defects": [], "log_path": None, "meta": {},
        }
    })
    rc, stdout, _ = _run([
        str(REPORT_TOOL), "--run-id", "FAKE-RUN-1",
        "--manifest", str(project / "evidence" / "manifest.json"),
        "--project-root", str(project),
        "--reports-root", str(project / "reports"),
        "--out-dir", str(project / "out"),
        "--no-env-probe", "--no-gate",
    ])
    assert rc == 0, stdout
    assert _json(stdout)["gate"]["verdict"] == "DISABLED"


# --------------------------------------------------------------------------- #
# packaging
# --------------------------------------------------------------------------- #
def test_package_is_byte_stable(packages):
    assert packages["a"]["zip"]["sha256"] == packages["b"]["zip"]["sha256"], (
        "rebuilding the same run must produce the same zip bytes")
    assert packages["a"]["zip"]["size_bytes"] == packages["b"]["zip"]["size_bytes"]
    assert packages["a"]["case_count"] == 8
    assert packages["a"]["counts"]["files"] == packages["b"]["counts"]["files"]
    zip_path = packages["package_dir"] / "submission.zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert names == sorted(names)
    assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in zipfile.ZipFile(zip_path).infolist())


def test_package_manifest_declares_internal_rehearsal(packages):
    manifest = json.loads((packages["package_dir"] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["official_format_confirmed"] is False
    assert "未确认" in manifest["official_format_note"]
    assert manifest["case_count"] == 8
    assert manifest["files"], "manifest must list payload files"
    for item in manifest["files"]:
        assert {"path", "sha256", "size_bytes", "case_id", "source"} <= set(item)
    readme = (packages["package_dir"] / "README.md").read_text(encoding="utf-8")
    assert "内部演练交付包，2026 官方提交格式未确认" in readme


def test_package_verify_passes(packages):
    rc, stdout, stderr = _run([str(PACKAGE_TOOL), "--verify", str(packages["package_dir"]), "--json"])
    assert rc == 0, f"verify exit={rc}\nstdout={stdout}\nstderr={stderr}"
    result = _json(stdout)
    assert result["verdict"] == "PASS"
    assert result["finding_counts"]["FAIL"] == 0
    summary = result["summary"]
    assert summary["checks_ok"] == summary["checks_total"]
    assert summary["case_count"] == 8
    assert summary["case_links"]["broken"] == []
    assert len(summary["case_links"]["implemented"]) == 8
    assert summary["screenshots"] == 13
    assert (packages["package_dir"] / "test-cases.xlsx").is_file()
    assert (packages["package_dir"] / "screenshots" / "index.csv").is_file()


# --------------------------------------------------------------------------- #
# defects and quality gate rendering
# --------------------------------------------------------------------------- #
def test_defect_fields_and_quality_gate_are_rendered(tmp_path):
    project = tmp_path / "defect-project"
    defect = {
        "defect_id": "DEF-001", "title": "计数更新滞后",
        "severity": "major", "severity_rationale": "影响用户判断剩余任务数，但可手动刷新规避",
        "category": "APP", "status": "needs_review",
        "description": "删除最后一项后 footer 计数未即时更新",
        "environment": "Chrome 156 / chromedriver 156 / Windows 11",
        "preconditions": ["列表中只有一项待办"],
        "repro_steps": ["打开 TodoMVC 演示页", "新增一项 Buy milk", "点击该项的删除按钮"],
        "repro_status": "intermittent", "repro_count": 2,
        "expected": "footer 消失", "actual": "footer 仍显示 1 item left",
        "evidence": ["EV-defect00001"], "created_at": "2026-10-30T17:00:00+08:00",
    }
    _write_fake_manifest(project / "evidence" / "manifest.json", {
        "TC-META-010": {
            "case_id": "TC-META-010", "title": "删除最后一项", "status": "failed",
            "expected": "footer 消失", "actual": "footer 仍显示 1 item left",
            "steps": ["新增一项", "删除该项"],
            "assertions": [{"name": "footer 隐藏", "expected": "True", "actual": "False",
                            "passed": False}],
            "evidence": [], "defects": [defect], "log_path": None, "meta": {},
        }
    })
    gate_dir = project / "qualification" / "gate-runs" / "FAKE-RUN-1"
    gate_dir.mkdir(parents=True)
    (gate_dir / "gate-report.json").write_text(json.dumps({
        "schema_version": "1.0", "run_id": "FAKE-RUN-1",
        "generated_at": "2026-10-30T18:00:00+08:00",
        "gate_status": {"G0": "PASS", "G2": "FAIL"},
        "delivery_verdict": "FAIL", "test_verdict": "FAIL",
        "findings": [{"gate": "G2", "code": "CASE_WITHOUT_ASSERTION", "severity": "FAIL",
                      "subject": "TC-META-010", "message": "断言缺失", "evidence": ""}],
        "summary": {"FAIL": 1, "WARNING": 0, "BLOCKED": 0, "UNVERIFIED": 0, "PASS": 12},
    }, ensure_ascii=False), encoding="utf-8")

    rc, stdout, stderr = _run([
        str(REPORT_TOOL), "--run-id", "FAKE-RUN-1",
        "--manifest", str(project / "evidence" / "manifest.json"),
        "--project-root", str(project),
        "--reports-root", str(project / "reports"),
        "--out-dir", str(project / "out"),
        "--no-gate", "--no-env-probe",
    ])
    assert rc == 0, f"{stdout}\n{stderr}"
    report = json.loads((project / "out" / "report.json").read_text(encoding="utf-8"))
    rendered = report["defects"][0]
    for field in ("severity_rationale", "category", "environment", "preconditions",
                  "repro_steps", "repro_status", "repro_count", "evidence"):
        assert field in rendered, f"defect field dropped: {field}"
        assert rendered[field] not in ("", [], None), f"defect field empty: {field}"
    assert rendered["unconfirmed"] is True
    assert rendered["repro_count"] == 2

    markdown = (project / "out" / "report.md").read_text(encoding="utf-8")
    assert "疑似/待复核，未确认为产品缺陷" in markdown
    assert "影响用户判断剩余任务数" in markdown
    assert "1. 打开 TodoMVC 演示页" in markdown
    assert "2. 新增一项 Buy milk" in markdown
    assert "3. 点击该项的删除按钮" in markdown

    gate = report["quality_gate"]
    assert gate["found"] is True
    assert gate["delivery_verdict"] == "FAIL"
    assert gate["gate_status"]["G2"] == "FAIL"
    assert gate["fail_findings"][0]["code"] == "CASE_WITHOUT_ASSERTION"
    assert "delivery_verdict：**FAIL**" in markdown
    assert "CASE_WITHOUT_ASSERTION" in markdown
