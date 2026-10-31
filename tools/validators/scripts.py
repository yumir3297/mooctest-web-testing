"""G2 - test code, pytest collection and JUnit <-> manifest cross checks.

Why this gate exists
--------------------
A green pytest exit code alone is not evidence: a suite can be empty, a case
can exist only in the CSV, or the manifest can claim ``passed`` while JUnit
never ran the test.  G2 therefore cross-checks three independent sources:

* the ``automation`` column of the case table (which function should exist),
* a real ``pytest --collect-only`` run (does the function exist),
* ``junit-summary.json`` + ``junit.xml`` versus the manifest case statuses.

Isolation
---------
Collection is executed in a sandbox copy (``<out>/_sandbox``) because the
project ``tests/conftest.py`` registers an evidence run at configure time: a
plain ``pytest --collect-only tests`` would mutate ``evidence/manifest.json``.
The sandbox mirrors the suite plus ``tools/*.py`` so imports resolve exactly as
in the real run.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

from .common import Report, first_line, load_json, truncate

GATE = "G2"

TEST_ASSERT_CALLS = ("check", "assert_equal", "assert_true", "assert_false", "assert_in")


# --------------------------------------------------------------------------- #
# automation specs
# --------------------------------------------------------------------------- #
def _clean_func(name: str) -> str:
    return re.split(r"[\[\(]", str(name or ""))[0].strip()


_PATH_LIKE = re.compile(r"^[\w./\\-]+\.py$")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_automation(value: Any) -> tuple[str | None, str | None]:
    """Split an ``automation`` cell into ``(file, function)``.

    Accepted forms:
    ``tests/test_x.py::test_y``, ``test_y``, ``tests/test_x.py``.
    Free text such as ``待实现`` / ``部分覆盖`` is *not* automation and returns
    ``(None, None)`` so it is reported as unrecognised instead of pretending a
    function exists.
    """
    text = str(value or "").strip()
    if not text:
        return None, None
    if "::" in text:
        left, _, right = text.partition("::")
        return (left.strip() or None), (_clean_func(right.split("::")[-1]) or None)
    if _PATH_LIKE.match(text):
        return text, None
    if _IDENTIFIER.match(text):
        return None, _clean_func(text)
    return None, None


# --------------------------------------------------------------------------- #
# junit
# --------------------------------------------------------------------------- #
def _summary_cases(summary: dict[str, Any]) -> list[dict[str, Any]]:
    cases = summary.get("cases")
    if isinstance(cases, list):
        return [c for c in cases if isinstance(c, dict)]
    return []


def _resolve_junit_xml(summary: dict[str, Any], summary_path: Path, case_root: Path) -> Path | None:
    raw = str(summary.get("junit") or "").strip()
    candidates: list[Path] = []
    if raw:
        literal = Path(raw)
        candidates.append(literal)
        if not literal.is_absolute():
            candidates.append(summary_path.parent / literal)
            candidates.append(case_root / literal)
    candidates.append(summary_path.parent / "junit.xml")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def parse_junit_xml(report: Report, path: Path) -> dict[str, Any] | None:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        report.add(GATE, "JUNIT_XML_PARSE_ERROR", "FAIL", str(path),
                   f"JUnit XML 无法解析：{type(exc).__name__}: {exc}")
        return None
    cases: list[dict[str, Any]] = []
    failures = errors = skipped = xfailed = 0
    for node in root.iter("testcase"):
        status = "passed"
        if node.find("failure") is not None:
            status, failures = "failed", failures + 1
        elif node.find("error") is not None:
            status, errors = "failed", errors + 1
        elif node.find("skipped") is not None:
            marker = node.find("skipped")
            if marker is not None and marker.get("type") == "pytest.xfail":
                status, xfailed = "xfailed", xfailed + 1
            else:
                status, skipped = "skipped", skipped + 1
        cases.append({
            "name": node.get("name") or "",
            "classname": node.get("classname") or "",
            "status": status,
        })
    return {
        "cases": cases,
        "counts": {"tests": len(cases), "failures": failures, "errors": errors,
                   "skipped": skipped, "xfailed": xfailed},
    }


def _status_counts(cases: Iterable[dict[str, Any]]) -> Counter:
    return Counter(str(case.get("status") or "unknown") for case in cases)


# --------------------------------------------------------------------------- #
# collection sandbox
# --------------------------------------------------------------------------- #
def prepare_sandbox(sandbox: Path, case_root: Path, suites: Sequence[str]) -> tuple[list[str], list[str]]:
    """Mirror ``suites`` into ``sandbox``; return (pytest args, missing paths)."""
    if sandbox.exists():
        shutil.rmtree(sandbox, ignore_errors=True)
    sandbox.mkdir(parents=True, exist_ok=True)
    (sandbox / "pytest.ini").write_text("[pytest]\naddopts =\n", encoding="utf-8")
    args: list[str] = []
    problems: list[str] = []
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "*.egg-info")
    for rel in suites:
        source = case_root / rel
        if not source.exists():
            problems.append(str(source))
            continue
        target = sandbox / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
        args.append(Path(rel).as_posix())
    # conftest.py commonly imports helper modules from <root>/tools
    tools_source = case_root / "tools"
    if tools_source.is_dir():
        tools_target = sandbox / "tools"
        tools_target.mkdir(parents=True, exist_ok=True)
        for module in tools_source.glob("*.py"):
            shutil.copy2(module, tools_target / module.name)
    return args, problems


def collect_tests(report: Report, sandbox: Path, case_root: Path, suites: Sequence[str],
                  python: str, timeout: int = 300) -> tuple[set[str], set[str]]:
    """Run ``pytest --collect-only`` in the sandbox; return (node ids, func names)."""
    args, problems = prepare_sandbox(sandbox, case_root, suites)
    if problems:
        report.add(GATE, "SUITE_PATH_MISSING", "FAIL", truncate(problems, 3),
                   "pytest 收集路径不存在")
        return set(), set()
    if not args:
        report.add(GATE, "SUITE_NOT_DERIVED", "FAIL", "suite",
                   "无法从 automation 列推导出可收集的套件目录")
        return set(), set()
    cmd = [python, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *args]
    env = os.environ.copy()
    env.update({
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "MOOCTEST_RUN_ID": "RUN-GATE-COLLECT",
    })
    try:
        proc = subprocess.run(cmd, cwd=str(sandbox), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        report.checks += 1
        report.add(GATE, "PYTEST_COLLECT_TIMEOUT", "FAIL", " ".join(args),
                   f"pytest --collect-only 超过 {timeout}s 未结束")
        return set(), set()
    output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    report.checks += 1
    if proc.returncode != 0:
        report.add(GATE, "PYTEST_COLLECT_FAILED", "FAIL", " ".join(args),
                   f"pytest --collect-only 退出码 {proc.returncode}：{first_line(output)}",
                   "stdout/stderr captured by the gate")
        return set(), set()
    report.checks_passed += 1
    nodes: set[str] = set()
    for line in output.splitlines():
        line = line.strip()
        if "::" not in line or line.startswith(("=", "ERROR", "E ")):
            continue
        node = line.split(" ")[0].strip()
        if "::" in node:
            nodes.add(node)
    report.check(GATE, "PYTEST_COLLECT_EMPTY", bool(nodes), " ".join(args),
                 "pytest --collect-only 没有收集到任何用例", "FAIL")
    funcs = {node.split("::")[1].split("[")[0] for node in nodes if "::" in node}
    if nodes:
        report.checks += 1
        report.checks_passed += 1
    return nodes, funcs


# --------------------------------------------------------------------------- #
# static analysis
# --------------------------------------------------------------------------- #
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_source(path: Path) -> tuple[ast.AST | None, str, SyntaxError | None]:
    text = _read(path)
    try:
        return ast.parse(text, filename=str(path)), text, None
    except SyntaxError as exc:
        return None, text, exc


def _imported_module_sources(path: Path, case_root: Path) -> list[str]:
    """Source of local modules imported by ``path`` (page objects, helpers)."""
    tree, _, _ = _parse_source(path)
    if tree is None:
        return []
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module and getattr(node, "level", 0) == 0:
            modules.add(node.module)
    sources: list[str] = []
    for module in sorted(modules):
        relative = module.replace(".", "/") + ".py"
        for candidate in (case_root / relative, path.parent / relative):
            if candidate.is_file() and candidate.resolve() != path.resolve():
                sources.append(_read(candidate))
                break
    return sources


def _has_assertion(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in TEST_ASSERT_CALLS:
                return True
    return False


_SLEEP_DIRECT = re.compile(r"\btime\s*\.\s*sleep\s*\(")
_SLEEP_IMPORTED = re.compile(r"from\s+time\s+import\s+[^\n]*\bsleep\b")
_SLEEP_BARE = re.compile(r"(?<![\w.])sleep\s*\(")
_EXCEPT_PASS = re.compile(r"except[^\n:]*:\s*(?:\r?\n\s*)?pass\b")
_WAIT_HINT = re.compile(r"\bWebDriverWait\b|\.until\s*\(")
_SELENIUM_HINT = re.compile(r"\bselenium\b|\bwebdriver\b")


def check_source(report: Report, path: Path, case_root: Path, subject: str) -> bool:
    """Static rules for one automation file.  Returns True when it parsed."""
    tree, text, error = _parse_source(path)
    if tree is None:
        report.check(GATE, "SYNTAX_ERROR", False, subject,
                     f"{path.name}:{getattr(error, 'lineno', '?')} 语法错误："
                     f"{getattr(error, 'msg', error)}", "FAIL", str(path))
        return False
    report.check(GATE, "SYNTAX_ERROR", True, subject, f"{path.name} ast.parse 通过")

    report.check(GATE, "CASE_WITHOUT_ASSERTION", _has_assertion(tree), subject,
                 f"{path.name} 没有 assert 语句，也没有 case_ctx.check(...) 断言", "FAIL")

    sleeps = bool(_SLEEP_DIRECT.search(text) or _SLEEP_IMPORTED.search(text))
    if not sleeps and _SLEEP_BARE.search(text):
        sleeps = True
    report.check(GATE, "TIME_SLEEP_IN_TEST", not sleeps, subject,
                 f"{path.name} 使用了 time.sleep()：应改用显式等待", "FAIL")

    combined = text + "\n" + "\n".join(_imported_module_sources(path, case_root))
    if _SELENIUM_HINT.search(combined):
        report.check(GATE, "MISSING_EXPLICIT_WAIT", bool(_WAIT_HINT.search(combined)), subject,
                     f"{path.name} 是浏览器测试但没有 WebDriverWait / wait.until 显式等待", "FAIL")

    report.check(GATE, "EXCEPT_PASS", not _EXCEPT_PASS.search(text), subject,
                 f"{path.name} 含 `except: pass`：异常被静默吞掉", "FAIL")
    return True


# --------------------------------------------------------------------------- #
# main entry
# --------------------------------------------------------------------------- #
def derive_suites(case_root: Path, automation_files: Iterable[str]) -> list[str]:
    suites: set[str] = set()
    for value in automation_files:
        parts = Path(value).parts
        if not parts:
            continue
        candidate = parts[0]
        if (case_root / candidate).exists():
            suites.add(candidate)
    if not suites and (case_root / "tests").is_dir():
        suites.add("tests")
    return sorted(suites)


def build_case_lookup(manifest_cases: dict[str, dict[str, Any]],
                      case_rows: Sequence[dict[str, Any]]) -> dict[str, str]:
    """Map junit test name / case id / automation function -> manifest case id."""
    lookup: dict[str, str] = {}
    for case_id, case in manifest_cases.items():
        candidates = {
            case_id,
            str(case.get("title") or ""),
            str((case.get("meta") or {}).get("junit_name") or ""),
        }
        for value in candidates:
            if value:
                lookup.setdefault(value, case_id)
    for row in case_rows:
        case_id = str(row.get("case_id") or "").strip()
        if not case_id or case_id not in manifest_cases:
            continue
        _, func = parse_automation(row.get("automation"))
        if func:
            lookup.setdefault(func, case_id)
    return lookup


def validate(report: Report, *,
             run_id: str,
             run: dict[str, Any] | None,
             manifest_cases: dict[str, dict[str, Any]],
             case_rows: Sequence[dict[str, Any]],
             junit_summary_path: Path | None,
             case_root: Path,
             sandbox: Path,
             suites: Sequence[str],
             python: str = sys.executable,
             timeout: int = 300,
             collect: bool = True) -> dict[str, Any]:
    run = run or {}
    stats: dict[str, Any] = {"manifest_case_counts": {}}

    # --- run level status --------------------------------------------------
    status = str(run.get("status") or "").strip()
    report.check(GATE, "RUN_STATUS_MISSING", bool(status), run_id,
                 "manifest 中 run.status 为空", "FAIL")
    if status == "blocked":
        report.add(GATE, "RUN_STATUS_BLOCKED", "BLOCKED", run_id,
                   "运行状态为 blocked：执行未完成，不能作为交付依据", str(run.get("stage") or ""))
    elif status == "aborted":
        report.add(GATE, "RUN_STATUS_ABORTED", "BLOCKED", run_id,
                   "运行状态为 aborted：执行中断，不能作为交付依据")
    elif status == "running":
        report.add(GATE, "RUN_STATUS_RUNNING", "WARNING", run_id,
                   "运行状态仍为 running：结果可能不完整")

    blocked_cases = [cid for cid, case in manifest_cases.items() if case.get("status") == "blocked"]
    report.check(GATE, "CASE_BLOCKED_ENV", not blocked_cases, run_id,
                 f"{len(blocked_cases)} 个用例 blocked（环境/夹具失败）：执行不完整，不是产品缺陷；"
                 f"{truncate(blocked_cases)}", "FAIL")

    counts = _status_counts(manifest_cases.values())
    stats["manifest_case_counts"] = dict(counts)
    executed = {s: n for s, n in counts.items() if s in ("passed", "failed", "xfailed", "skipped")}

    # --- junit summary -----------------------------------------------------
    summary_path = Path(junit_summary_path) if junit_summary_path else None
    summary: dict[str, Any] | None = None
    summary_state = "missing"
    if summary_path is not None and summary_path.is_file():
        data, error = load_json(summary_path)
        if isinstance(data, dict):
            summary, summary_state = data, "ok"
        else:
            summary_state = "invalid"
            report.add(GATE, "JUNIT_SUMMARY_INVALID", "FAIL", run_id,
                       f"junit-summary.json 无法解析：{error}", str(summary_path))
    stats["junit_summary"] = str(summary_path) if summary_path else None
    stats["junit_summary_state"] = summary_state

    junit_cases: list[dict[str, Any]] = []
    summary_passed = 0
    if summary is None:
        if not executed:
            if status not in ("blocked", "aborted"):
                report.add(GATE, "EXECUTION_NOT_VERIFIABLE", "UNVERIFIED", run_id,
                           "既没有可解析的 JUnit 摘要，也没有任何已执行用例：无法判定执行结果")
        elif summary_state == "missing":
            report.add(GATE, "JUNIT_SUMMARY_MISSING", "FAIL", run_id,
                       f"manifest 声称 {sum(executed.values())} 个用例已执行，但没有 junit-summary.json",
                       str(summary_path or ""))
    else:
        summary_cases = _summary_cases(summary)
        if summary_cases:
            junit_cases = summary_cases
            summary_passed = sum(1 for c in summary_cases if c.get("status") == "passed")
        else:
            derived = (int(summary.get("tests", 0) or 0) - int(summary.get("failures", 0) or 0)
                       - int(summary.get("errors", 0) or 0) - int(summary.get("skipped", 0) or 0))
            summary_passed = max(derived, 0)
        stats["junit_summary_passed"] = summary_passed
        stats["junit_summary_counts"] = {k: summary.get(k) for k in
                                         ("tests", "failures", "errors", "skipped", "xfailed")}

        # junit.xml consistency
        if summary_path is not None:
            xml_path = _resolve_junit_xml(summary, summary_path, case_root)
            report.check(GATE, "JUNIT_XML_PRESENT", xml_path is not None, run_id,
                         "junit-summary.json 指向的 JUnit XML 不存在", "FAIL",
                         str(summary.get("junit") or ""))
            if xml_path is not None:
                xml = parse_junit_xml(report, xml_path)
                if xml is not None:
                    xml_cases = xml["cases"]
                    if not junit_cases:
                        junit_cases = xml_cases
                    xml_counts = xml["counts"]
                    stats["junit_xml"] = str(xml_path)
                    stats["junit_xml_counts"] = dict(xml_counts)
                    for key in ("tests", "failures", "errors"):
                        if summary.get(key) is not None:
                            expected = int(summary.get(key) or 0)
                            report.check(GATE, "JUNIT_XML_SUMMARY_MISMATCH",
                                         expected == int(xml_counts[key]), run_id,
                                         f"{key}: junit-summary={expected} != junit.xml={xml_counts[key]}",
                                         "FAIL", str(xml_path))
                    if summary.get("skipped") is not None:
                        skipped_xml = int(xml_counts["skipped"]) + int(xml_counts["xfailed"])
                        report.check(GATE, "JUNIT_XML_SUMMARY_MISMATCH",
                                     int(summary.get("skipped") or 0) == skipped_xml, run_id,
                                     f"skipped: junit-summary={summary.get('skipped')} != junit.xml={skipped_xml}",
                                     "FAIL", str(xml_path))

        # --- manifest <-> junit counts ------------------------------------
        manifest_passed = counts.get("passed", 0)
        report.check(GATE, "JUNIT_MANIFEST_COUNT_MISMATCH", manifest_passed == summary_passed, run_id,
                     f"JUnit passed={summary_passed}，manifest passed={manifest_passed}"
                     "（允许 manifest 多出 xfailed/blocked）", "FAIL")

        # --- name mapping --------------------------------------------------
        lookup = build_case_lookup(manifest_cases, case_rows)
        mapped_cases: set[str] = set()
        for testcase in junit_cases:
            name = str(testcase.get("name") or "")
            matched = lookup.get(name)
            if matched:
                mapped_cases.add(matched)
            report.check(GATE, "JUNIT_CASE_UNMAPPED", bool(matched), name,
                         f"JUnit 用例 `{name}` 无法映射到 manifest 用例", "FAIL")
        stats["junit_case_names"] = [str(c.get("name")) for c in junit_cases]

        if junit_cases:
            orphans = [cid for cid, case in manifest_cases.items()
                       if case.get("status") == "passed" and cid not in mapped_cases]
            report.check(GATE, "MANIFEST_PASSED_WITHOUT_JUNIT", not orphans, run_id,
                         f"manifest 记为 passed 但 JUnit 无对应用例：{truncate(orphans)}", "FAIL")

    # --- collection + automation ------------------------------------------
    automation: list[tuple[str, str | None, str]] = []
    unrecognised: list[str] = []
    for row in case_rows:
        case_id = str(row.get("case_id") or "").strip()
        raw = str(row.get("automation") or "").strip()
        if not raw:
            continue
        file_part, func = parse_automation(raw)
        if not file_part and not func:
            unrecognised.append(f"{case_id or '-'}:{raw}")
            continue
        automation.append((case_id or "-", file_part, func or ""))
    if case_rows:
        report.check(GATE, "AUTOMATION_COLUMN_EMPTY", bool(automation), "automation",
                     "用例表没有任何可解析的 automation：所有用例都是手工用例，无法自动核验", "WARNING")
    report.check(GATE, "AUTOMATION_VALUE_UNRECOGNISED", not unrecognised, "automation",
                 f"automation 列含非代码值（按手工用例处理）：{truncate(unrecognised)}", "WARNING")

    nodes: set[str] = set()
    funcs: set[str] = set()
    if collect and suites:
        nodes, funcs = collect_tests(report, sandbox, case_root, suites, python, timeout)
    else:
        report.add(GATE, "PYTEST_COLLECT_SKIPPED", "WARNING", "suite",
                   "--no-collect：未执行 pytest 收集，无法验证自动化用例真实存在")

    resolved: dict[str, tuple[Path, str]] = {}
    for case_id, file_part, func in automation:
        path: Path | None = None
        if file_part:
            candidate = case_root / file_part
            if candidate.is_file():
                path = candidate
        if path is None and func:
            for node in nodes:
                file_rel, _, node_func = node.partition("::")
                if _clean_func(node_func) != func:
                    continue
                candidate = case_root / file_rel
                if candidate.is_file():
                    path = candidate
                    break
        report.check(GATE, "AUTOMATION_FILE_MISSING", path is not None, case_id,
                     f"automation `{file_part or func}` 对应的测试文件不存在", "FAIL")
        if path is not None:
            resolved.setdefault(str(path), (path, case_id))
        if collect and nodes and func:
            report.check(GATE, "AUTOMATION_NOT_COLLECTED", func in funcs, case_id,
                         f"pytest 收集结果中没有 `{func}`：用例声称已自动化但函数不存在", "FAIL")

    for path, subject in resolved.values():
        check_source(report, path, case_root, subject)

    stats["automation"] = [{"case_id": cid, "file": f, "func": fn} for cid, f, fn in automation]
    stats["collected_nodes"] = sorted(nodes)
    return stats
