"""Tests for the pre-submission quality gate itself.

Run with an explicit path (``pytest.ini`` pins ``testpaths = tests`` for the
product suite, so this directory is never collected implicitly):

    python -m pytest tests_meta -q

Every test invokes the real CLI in a subprocess and reads the real
``gate-report.json``.  Nothing is mocked: the exit code, the verdicts and the
finding codes are exactly what the gate wrote.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "pre_submission_gate.py"
QUAL = ROOT / "qualification"
RUNS = QUAL / "gate-runs"

# sample -> (expected exit code, gate, required finding code(s))
NEGATIVE_CASES = {
    "empty-cases": (1, "G1", {"CASES_EMPTY"}),
    "missing-expected": (1, "G1", {"CASE_EXPECTED_MISSING"}),
    "duplicate-case-id": (1, "G1", {"CASE_ID_DUPLICATE"}),
    "no-boundary-coverage": (1, "G1", {"CASE_TYPE_COVERAGE_MISSING"}),
    "no-assertion": (1, "G2", {"CASE_WITHOUT_ASSERTION"}),
    "junit-manifest-mismatch": (1, "G2", {"JUNIT_MANIFEST_COUNT_MISMATCH",
                                          "MANIFEST_PASSED_WITHOUT_JUNIT"}),
    "fake-pass": (1, "G2", {"JUNIT_SUMMARY_MISSING"}),
    "missing-screenshot": (1, "G3", {"PASSED_CASE_WITHOUT_EVIDENCE"}),
    "bad-sha256": (1, "G3", {"EVIDENCE_HASH_MISMATCH"}),
    "defect-no-repro": (1, "G3", {"DEFECT_FIELD_MISSING"}),
    "blocked-run": (2, "G2", {"RUN_STATUS_BLOCKED"}),
    "unverifiable-run": (3, "G2", {"EXECUTION_NOT_VERIFIABLE"}),
}

POSITIVE_CASES = {
    "defect-reported": {"delivery": {"PASS"}, "test": "FAIL"},
    "suspected-defect": {"delivery": {"WARNING"}, "test": "FAIL",
                         "warnings": {"DEFECT_STATUS_UNCONFIRMED"}},
}


def sample_dirs(polarity: str, name: str) -> Path:
    directory = QUAL / polarity / name
    assert (directory / "manifest.json").is_file(), f"missing sample: {directory}"
    return directory


def gate_command(directory: Path, out: Path, extra: tuple[str, ...] = ()) -> tuple[list[str], str]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    run_id = next(iter(manifest["runs"]))
    command = [sys.executable, str(GATE),
               "--run-id", run_id,
               "--manifest", str(directory / "manifest.json"),
               "--cases", str(directory / "cases.csv"),
               "--out", str(out),
               "--no-env-check",
               "--json"]
    junit = directory / "junit-summary.json"
    if junit.is_file():
        command += ["--junit-summary", str(junit)]
    requirements = directory / "requirements.csv"
    if requirements.is_file():
        command += ["--requirements", str(requirements)]
    command += list(extra)
    return command, run_id


def run_gate(directory: Path, out_name: str, extra: tuple[str, ...] = ()):
    out = RUNS / out_name
    out.mkdir(parents=True, exist_ok=True)
    command, run_id = gate_command(directory, out, extra)
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)
    report_path = out / "gate-report.json"
    assert report_path.is_file(), f"gate did not write {report_path}\n{proc.stdout}\n{proc.stderr}"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return proc.returncode, report, run_id


@pytest.mark.parametrize("name", sorted(NEGATIVE_CASES))
def test_negative_sample_is_rejected(name: str) -> None:
    expected_exit, gate, required = NEGATIVE_CASES[name]
    directory = sample_dirs("negative", name)
    code, report, _ = run_gate(directory, f"pytest-negative-{name}")

    assert code == expected_exit, (
        f"{name}: exit {code} != {expected_exit}; findings="
        f"{[f['code'] for f in report['findings']]}")
    assert code != 0, f"{name}: a broken delivery must never exit 0"
    assert report["delivery_verdict"] in {"FAIL", "BLOCKED", "UNVERIFIED"}

    findings = report["findings"]
    codes = {f["code"] for f in findings}
    missing = required - codes
    assert not missing, f"{name}: expected {sorted(required)} in {sorted(codes)}"

    for finding in findings:
        if finding["code"] in required:
            assert finding["gate"] == gate, f"{name}: {finding['code']} reported by {finding['gate']}"


@pytest.mark.parametrize("name", sorted(POSITIVE_CASES))
def test_positive_sample_is_deliverable(name: str) -> None:
    spec = POSITIVE_CASES[name]
    directory = sample_dirs("positive", name)
    code, report, _ = run_gate(directory, f"pytest-positive-{name}")

    assert code == 0, f"{name}: expected exit 0, got {code}"
    assert report["delivery_verdict"] in spec["delivery"]
    assert report["test_verdict"] == spec["test"]

    failing = [f for f in report["findings"]
               if not f.get("advisory") and f["severity"] in {"FAIL", "BLOCKED"}]
    assert not failing, f"{name}: a deliverable sample must not have blocking findings: {failing}"

    if spec.get("warnings"):
        codes = {f["code"] for f in report["findings"]}
        assert spec["warnings"] <= codes


def test_confirmed_defect_separates_test_verdict_from_delivery_verdict() -> None:
    """The core distinction: a real bug fails the app, not the test artefacts."""
    directory = sample_dirs("positive", "defect-reported")
    code, report, _ = run_gate(directory, "pytest-verdict-separation")

    assert code == 0
    assert report["test_verdict"] == "FAIL"
    assert report["delivery_verdict"] == "PASS"
    assert report["gate_status"]["G3"] == "PASS"
    assert report["execution"]["failed_case_triage"] == {
        "TC-SAMPLE-002": "已登记确认缺陷",
    }


def test_official_submission_escalates_unverified_ai_compliance() -> None:
    """Without an AI-usage declaration an official submission is blocked."""
    directory = sample_dirs("positive", "defect-reported")
    code, report, _ = run_gate(directory, "pytest-official-submission",
                               extra=("--official-submission",))

    assert code == 2, f"official submission must be BLOCKED, got exit {code}"
    assert report["delivery_verdict"] == "BLOCKED"
    codes = {f["code"] for f in report["findings"]}
    assert "AI_USE_NOT_CONFIRMED" in codes


def test_g4_accepts_valid_package_and_rejects_tampered_one() -> None:
    """G4 validates the artefact itself (structure, openable xlsx/zip, sha256)."""
    directory = sample_dirs("positive", "defect-reported")
    run_id = "RUN-SAMPLE-DEFECTREPORTED"
    good = QUAL / "package-sample" / "good" / "submission" / run_id
    broken = QUAL / "package-sample" / "broken" / "submission" / run_id
    if not good.is_dir() or not broken.is_dir():
        pytest.skip("package samples not generated (run qualification/make_samples.py)")

    code, report, _ = run_gate(directory, "pytest-g4-good", extra=("--submission", str(good)))
    assert code == 0, f"valid package must pass, got {code}"
    assert report["gate_status"]["G4"] == "PASS"

    code, report, _ = run_gate(directory, "pytest-g4-broken", extra=("--submission", str(broken)))
    assert code == 1, f"tampered package must fail, got {code}"
    assert report["gate_status"]["G4"] == "FAIL"
    assert any(f["code"] == "PACKAGE_HASH_MISMATCH" for f in report["findings"])


def test_collection_runs_in_a_sandbox() -> None:
    """pytest collection must not touch evidence/manifest.json of the project."""
    directory = sample_dirs("negative", "no-assertion")
    _, report, _ = run_gate(directory, "pytest-sandbox")
    sandbox = RUNS / "pytest-sandbox" / "_sandbox"
    assert (sandbox / "tests" / "test_sample.py").is_file()
    assert report["execution"]["collected_nodes"] == ["tests/test_sample.py::test_add_valid"]


def test_historical_blocked_run_is_not_exit_zero() -> None:
    """Regression for audit item C5: a blocked run must not exit 0."""
    manifest = ROOT / "evidence" / "manifest.json"
    if not manifest.is_file():
        pytest.skip("no evidence manifest")
    runs = json.loads(manifest.read_text(encoding="utf-8")).get("runs", {})
    if "RUN-CMDCHECK-01" not in runs:
        pytest.skip("RUN-CMDCHECK-01 not present in the manifest")

    out = RUNS / "pytest-cmdcheck01"
    out.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(GATE), "--run-id", "RUN-CMDCHECK-01",
               "--cases", str(ROOT / "reports" / "test-cases" / "TodoMVC-CMDCHECK-test-cases.csv"),
               "--out", str(out), "--no-env-check", "--json"]
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)
    report = json.loads((out / "gate-report.json").read_text(encoding="utf-8"))
    assert proc.returncode == 2, f"expected BLOCKED exit 2, got {proc.returncode}"
    assert report["delivery_verdict"] == "BLOCKED"
    assert report["test_verdict"] == "BLOCKED"


# --------------------------------------------------------------------------- #
# unit level checks on the text helpers
# --------------------------------------------------------------------------- #
def test_split_steps_counts_numbered_and_separated_steps() -> None:
    from validators.cases import split_steps

    assert len(split_steps("1.打开页面;2.输入文本;3.回车")) == 3
    assert len(split_steps("打开页面 -> 输入 -> 回车")) == 1
    assert len(split_steps("勾选第一条；切换过滤器")) == 2
    assert split_steps("") == []


def test_vague_expected_is_detected() -> None:
    from validators.cases import is_vague_expected

    assert is_vague_expected("正常显示")
    assert is_vague_expected("功能正常")
    assert is_vague_expected("OK")
    assert not is_vague_expected("列表出现 Buy milk；计数 1 item left")


def test_parse_automation_forms() -> None:
    from validators.scripts import parse_automation

    assert parse_automation("tests/test_x.py::test_y") == ("tests/test_x.py", "test_y")
    assert parse_automation("test_y") == (None, "test_y")
    assert parse_automation("tests/test_x.py") == ("tests/test_x.py", None)
    assert parse_automation("待实现") == (None, None)
    assert parse_automation("") == (None, None)
