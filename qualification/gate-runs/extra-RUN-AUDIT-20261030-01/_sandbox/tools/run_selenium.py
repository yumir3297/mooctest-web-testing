#!/usr/bin/env python3
"""Run the Selenium/pytest suite and persist console + JUnit evidence.

Behaviour notes:
- a new run id is required by default; reusing an existing run needs `--reuse`
  so a finished run is never silently overwritten;
- the environment block records the real Python / Selenium / pytest / Chrome /
  ChromeDriver versions instead of placeholders;
- on timeout the pytest process tree is killed and the run is marked `blocked`.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import evidence  # noqa: E402
import versioning  # noqa: E402

DEFAULT_TARGET = "https://demo.playwright.dev/todomvc"


def _pytest_version() -> str:
    try:
        import pytest
        return pytest.__version__
    except Exception:
        return "<unknown>"


def environment_snapshot(target: str) -> dict[str, str]:
    env: dict[str, str] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "os": platform.release(),
        "pytest": _pytest_version(),
        "target": target,
    }
    try:
        import selenium
        env["selenium"] = selenium.__version__
    except Exception as exc:
        env["selenium"] = f"<import failed: {exc}>"
    chrome_path = versioning.find_chrome()
    env["chrome"] = versioning.exe_version(chrome_path) if chrome_path else "<not found>"
    if chrome_path:
        env["chrome_path"] = str(chrome_path)
    driver = ROOT / "tools" / "driver" / "chromedriver.exe"
    env["chromedriver"] = versioning.exe_version(driver) if driver.is_file() else "<not found>"
    env["node"] = versioning.first_line(["node", "--version"])
    return env


def _parse_junit(path: Path) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    suite = root.find("testsuite") if root.tag != "testsuite" else root
    if suite is None:
        suite = root
    counts = {
        "tests": int(suite.get("tests", 0) or 0),
        "failures": int(suite.get("failures", 0) or 0),
        "errors": int(suite.get("errors", 0) or 0),
        "skipped": int(suite.get("skipped", 0) or 0),
        "time": float(suite.get("time", 0) or 0),
        "xfailed": 0,
        "cases": [],
    }
    for tc in root.iter("testcase"):
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")
        status = "passed"
        message = ""
        if failure is not None:
            status = "failed"
            message = (failure.get("message") or failure.text or "")[:2000]
        elif error is not None:
            status = "failed"
            message = (error.get("message") or error.text or "")[:2000]
        elif skipped is not None:
            status = "skipped"
            message = skipped.get("message") or ""
            if skipped.get("type") == "pytest.xfail":
                status = "xfailed"
                counts["xfailed"] += 1
        counts["cases"].append({
            "name": tc.get("name"),
            "classname": tc.get("classname"),
            "time": float(tc.get("time", 0) or 0),
            "status": status,
            "message": message,
        })
    return counts


def _kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, text=True, timeout=30)
        else:  # pragma: no cover
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run Selenium/pytest with evidence")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--target", default=os.environ.get("MOOCTEST_TARGET", DEFAULT_TARGET))
    parser.add_argument("--label", default="Selenium acceptance")
    parser.add_argument("--suite", action="append", default=None, help="pytest path (repeatable)")
    parser.add_argument("--marker", "-m", default="")
    parser.add_argument("--keyword", "-k", default="")
    parser.add_argument("--capture-pass", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--reuse", action="store_true",
                        help="allow writing into an existing run id (default: refuse)")
    parser.add_argument("--pytest-arg", action="append", default=[])
    args = parser.parse_args(argv)

    run_id = args.run_id or f"RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    evidence.ensure_layout()
    try:
        evidence.start_run(run_id, target=args.target, label=args.label,
                           reuse=args.reuse, environment=environment_snapshot(args.target))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    evidence.update_run(run_id, status="running", stage="selenium", note="pytest started")
    exec_dir = evidence.REPORTS_DIR / "executions" / run_id
    exec_dir.mkdir(parents=True, exist_ok=True)
    junit = exec_dir / "junit.xml"
    console_log = evidence.LOGS_DIR / run_id / "pytest-console.log"
    console_log.parent.mkdir(parents=True, exist_ok=True)

    suites = args.suite or ["tests"]
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short", "--junitxml", str(junit)]
    if args.marker:
        cmd += ["-m", args.marker]
    if args.keyword:
        cmd += ["-k", args.keyword]
    cmd += suites + args.pytest_arg

    env = os.environ.copy()
    env.update({
        "MOOCTEST_RUN_ID": run_id,
        "MOOCTEST_TARGET": args.target,
        "MOOCTEST_CAPTURE_PASS": "1" if args.capture_pass else "0",
        "MOOCTEST_HEADED": "1" if args.headed else "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    })
    started = time.time()
    timed_out = False
    code = -1
    with console_log.open("w", encoding="utf-8", newline="\n") as logf:
        logf.write("$ " + " ".join(cmd) + "\n")
        logf.flush()
        proc = subprocess.Popen(
            cmd, cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        )
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                logf.write(line)
            code = proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc)
            try:
                code = proc.wait(timeout=60)
            except Exception:
                code = -9
            logf.write(f"\n[run_selenium] TIMEOUT after {args.timeout}s; process tree killed\n")
    elapsed = round(time.time() - started, 2)

    summary: dict = {"run_id": run_id, "exit_code": code, "elapsed_seconds": elapsed,
                     "timed_out": timed_out, "junit": str(junit), "console_log": str(console_log)}
    if timed_out:
        evidence.update_run(run_id, status="blocked", stage="executed",
                            note=f"pytest timed out after {args.timeout}s; process tree killed")
        summary["status"] = "blocked"
    elif junit.exists():
        try:
            parsed = _parse_junit(junit)
            summary.update(parsed)
            counts = evidence.run_summary(run_id).get("case_counts", {})
            if counts.get("failed"):
                status = "failed"
            elif counts.get("blocked") or parsed["tests"] == 0:
                status = "blocked"
            elif parsed["failures"] or parsed["errors"]:
                # JUnit reports failures/errors that never produced a case record
                status = "blocked" if counts.get("passed") is None else "failed"
            else:
                status = "passed"
            note = (f"pytest exit={code}; tests={parsed['tests']}; failures={parsed['failures']}; "
                    f"errors={parsed['errors']}; xfailed={parsed['xfailed']}; elapsed={elapsed}s; "
                    f"case_counts={counts}")
            evidence.update_run(run_id, status=status, stage="executed", note=note)
            summary["status"] = status
            summary["case_counts"] = counts
        except Exception as exc:
            summary["parse_error"] = str(exc)
            evidence.update_run(run_id, status="blocked", stage="executed", note=f"junit parse error: {exc}")
            summary["status"] = "blocked"
    else:
        evidence.update_run(run_id, status="blocked", stage="executed", note="junit.xml missing")
        summary["status"] = "blocked"
    (exec_dir / "junit-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: summary.get(k) for k in (
        "run_id", "exit_code", "status", "timed_out", "tests", "failures", "errors", "skipped",
        "xfailed", "elapsed_seconds", "junit", "console_log")}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
