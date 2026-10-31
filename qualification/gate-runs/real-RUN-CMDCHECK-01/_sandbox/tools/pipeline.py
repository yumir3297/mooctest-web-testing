#!/usr/bin/env python3
"""Deterministic stage/artifact state machine for the testing pipeline.

The pipeline never calls an LLM and never imports the sibling tool modules.
It only reads/writes ``pipeline_runs/<RUN-ID>/state.json`` and validates the
artifacts declared for each stage. Stage ownership and artifact contracts are
defined in ``docs/CONTRACTS.md`` section 6 and ``docs/PIPELINE.md``.

Exit codes:
    0  success / idempotent no-op
    1  artifact gate failed (missing/invalid required artifacts)
    2  usage or state precondition error (unknown run, existing run, bad id)
    3  repair budget exhausted (record-repair only)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "pipeline_runs"
MANIFEST_PATH = ROOT / "evidence" / "manifest.json"
TOOLS_DIR = ROOT / "tools"

RUN_ID_RE = re.compile(r"^RUN-[A-Za-z0-9][A-Za-z0-9._-]*$")
SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")
REPAIR_LIMIT = 3
REPAIR_CLASSES = ("ENV", "LOCATOR", "TIMING", "DATA", "SCRIPT", "ASSERT", "APP", "UNKNOWN")

# The single source of truth for stage order and required artifacts.
# Patterns are relative to the project root; {run} and {slug} are expanded.
STAGES: tuple[dict[str, Any], ...] = (
    {
        "name": "INIT",
        "artifacts": [
            "pipeline_runs/{run}/state.json",
            "pipeline_runs/{run}/requirement.md",
        ],
        "next_action": "确认 state.json 与 requirement.md 已生成，然后运行 advance。",
    },
    {
        "name": "ENV_CHECK",
        "artifacts": ["pipeline_runs/{run}/env_check.json"],
        "next_action": "运行环境自检并把 JSON 写入 pipeline_runs/{run}/env_check.json。",
    },
    {
        "name": "KNOWLEDGE_LOAD",
        "artifacts": ["pipeline_runs/{run}/knowledge_plan.json"],
        "next_action": "用 knowledge_router 生成本阶段知识计划，写入 pipeline_runs/{run}/knowledge_plan.json。",
    },
    {
        "name": "REQUIREMENT_ANALYSIS",
        "artifacts": [
            "pipeline_runs/{run}/requirements.json",
            "reports/test-cases/*{slug}*requirements*.md",
        ],
        "next_action": "提取功能点/R1..Rn/输入域/边界，产出 requirements.json 与需求分析 Markdown。",
    },
    {
        "name": "BROWSER_EXPLORATION",
        "artifacts": [
            "reports/executions/{run}/exploration.md",
            "evidence/raw/{run}/**",
        ],
        "next_action": "用浏览器打开目标，记录真实 DOM/选择器/交互路径与截图，写 exploration.md。",
    },
    {
        "name": "TEST_DESIGN",
        "artifacts": [
            "reports/test-cases/*{slug}*test-cases.csv",
            "reports/test-cases/*{slug}*test-cases.md",
        ],
        "next_action": "按方法论文档设计用例，产出 CSV（规范列）与 Markdown 用例文档。",
    },
    {
        "name": "CASE_REVIEW",
        "artifacts": ["pipeline_runs/{run}/case-review.md"],
        "next_action": "审查覆盖缺口/重复/可执行性/可追溯性，写 case-review.md。",
    },
    {
        "name": "SCRIPT_GENERATION",
        "artifacts": [
            "tests/generated/{slug}/test_*.py",
            "tests/generated/{slug}/page_*.py",
        ],
        "next_action": "用 tools/scaffold.py 生成骨架并补全为真实断言脚本。",
    },
    {
        "name": "SCRIPT_VALIDATION",
        "artifacts": ["pipeline_runs/{run}/script-validation.json"],
        "next_action": "运行 pytest --collect-only 与静态门禁，记录 script-validation.json。",
    },
    {
        "name": "TEST_EXECUTION",
        "artifacts": ["reports/executions/{run}/junit-summary.json"],
        "next_action": "用 tools/run_selenium.py 执行测试，生成 JUnit 与 junit-summary.json。",
    },
    {
        "name": "FAILURE_TRIAGE",
        "artifacts": ["pipeline_runs/{run}/triage.md"],
        "next_action": "逐条失败分类（ENV/LOCATOR/TIMING/DATA/SCRIPT/ASSERT/APP），无失败也要写说明。",
    },
    {
        "name": "EVIDENCE_REVIEW",
        "artifacts": ["pipeline_runs/{run}/evidence-review.json"],
        "next_action": "核验 manifest、哈希、证据完整性，写 evidence-review.json。",
    },
    {
        "name": "COVERAGE_REVIEW",
        "artifacts": ["pipeline_runs/{run}/coverage.md"],
        "next_action": "核对需求→用例→脚本→执行覆盖，写 coverage.md。",
    },
    {
        "name": "REPORT_GENERATION",
        "artifacts": [
            "reports/executions/{run}/report.md",
            "reports/executions/{run}/report.json",
        ],
        "next_action": "生成测试报告（Markdown + JSON），引用已登记证据。",
    },
    {
        "name": "QUALITY_GATE",
        "artifacts": ["qualification/gate-runs/{run}/gate-report.json"],
        "next_action": "运行 pre_submission_gate，产出 gate-report.json。",
    },
    {
        "name": "PACKAGE_PREPARATION",
        "artifacts": [
            "submission/{run}/submission.zip",
            "submission/{run}/manifest.json",
        ],
        "next_action": "打包 submission/<run> 并校验 manifest 与哈希。",
    },
    {
        "name": "COMPLETE",
        "artifacts": ["pipeline_runs/{run}/FINAL.md"],
        "next_action": "写 FINAL.md 交付说明，然后运行 verify-run。",
    },
)
STAGE_NAMES = tuple(s["name"] for s in STAGES)
STAGE_INDEX = {name: i for i, name in enumerate(STAGE_NAMES)}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _fail(message: str, code: int = 2) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code


def _validate_run_id(run_id: str) -> bool:
    return bool(run_id) and bool(RUN_ID_RE.match(run_id)) and ".." not in run_id


def _run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def _state_path(run_id: str) -> Path:
    return _run_dir(run_id) / "state.json"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "gbk"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def _load_json(path: Path) -> Any:
    """Parse JSON from UTF-8/UTF-8-BOM/UTF-16 files (PowerShell redirects)."""
    raw = path.read_bytes()
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-16", "gbk"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeError, json.JSONDecodeError) as exc:
            last_error = exc
            continue
    raise ValueError(f"cannot parse JSON: {last_error}")


def _load_state(run_id: str) -> dict[str, Any] | None:
    path = _state_path(run_id)
    if not path.is_file():
        return None
    return _load_json(path)


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    _atomic_json(_state_path(state["run_id"]), state)


def _slugify(value: str) -> str:
    slug = SLUG_RE.sub("-", value).strip("-").lower()
    return slug or "app"


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _expand(pattern: str, state: dict[str, Any]) -> str:
    return pattern.replace("{run}", str(state.get("run_id", ""))).replace(
        "{slug}", str(state.get("slug", ""))
    )


def _stage_entry(state: dict[str, Any], name: str) -> dict[str, Any]:
    for stage in state["stages"]:
        if stage["name"] == name:
            return stage
    raise KeyError(f"stage not found in state: {name}")


def _current_stage(state: dict[str, Any]) -> dict[str, Any]:
    return _stage_entry(state, state["current_stage"])


def _validate_file(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "not a file"
    if path.stat().st_size <= 0:
        return False, "empty file"
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            _load_json(path)
        except Exception as exc:  # noqa: BLE001 - report the real parse error
            return False, f"invalid json: {exc}"
    elif suffix == ".csv":
        lines = [line for line in _read_text(path).splitlines() if line.strip()]
        if len(lines) < 2:
            return False, f"csv needs header + 1 data row, got {len(lines)} non-empty line(s)"
    return True, "ok"


def validate_artifacts(state: dict[str, Any], stage_name: str) -> tuple[list[str], list[str]]:
    """Return (existing valid artifact paths, problem descriptions)."""
    definition = STAGES[STAGE_INDEX[stage_name]]
    ok_paths: list[str] = []
    problems: list[str] = []
    for pattern in definition["artifacts"]:
        expanded = _expand(pattern, state)
        matches = [p for p in ROOT.glob(expanded) if p.is_file()]
        if not matches:
            problems.append(f"missing: {expanded}")
            continue
        valid = 0
        for match in matches:
            good, detail = _validate_file(match)
            if good:
                valid += 1
                ok_paths.append(_rel(match))
            else:
                problems.append(f"invalid: {_rel(match)} ({detail})")
        if valid == 0:
            problems.append(f"no valid file matched: {expanded}")
    # de-duplicate while keeping a stable order
    ok_paths = list(dict.fromkeys(ok_paths))
    return ok_paths, problems


def suggestions_for(state: dict[str, Any], stage_name: str) -> list[str]:
    """Commands that would produce the stage artifacts, printed only if the CLI exists."""
    run_id = state["run_id"]
    slug = state.get("slug", "")
    target = state.get("target", "")
    candidates: dict[str, tuple[str, str]] = {
        "ENV_CHECK": (
            "tools/env_check.py",
            f"python tools/env_check.py --json  # write stdout to pipeline_runs/{run_id}/env_check.json",
        ),
        "KNOWLEDGE_LOAD": (
            "tools/knowledge_router.py",
            f"python tools/knowledge_router.py --stage requirement-analysis --json  # write to pipeline_runs/{run_id}/knowledge_plan.json",
        ),
        "SCRIPT_VALIDATION": (
            f"tests/generated/{slug}",
            f"python -m pytest --collect-only -q tests/generated/{slug}",
        ),
        "TEST_EXECUTION": (
            "tools/run_selenium.py",
            f"python tools/run_selenium.py --run-id {run_id} --target {target} --suite tests/generated/{slug}",
        ),
        "EVIDENCE_REVIEW": (
            "tools/evidence.py",
            f"python tools/evidence.py verify --run-id {run_id} --fail-on-error",
        ),
        "REPORT_GENERATION": (
            "tools/generate_report.py",
            f"python tools/generate_report.py --run-id {run_id}",
        ),
        "QUALITY_GATE": (
            "tools/pre_submission_gate.py",
            f"python tools/pre_submission_gate.py --run-id {run_id} --out qualification/gate-runs/{run_id}",
        ),
        "PACKAGE_PREPARATION": (
            "tools/package_submission.py",
            f"python tools/package_submission.py --run-id {run_id}",
        ),
    }
    item = candidates.get(stage_name)
    if not item:
        return []
    probe, command = item
    probe_path = ROOT / probe if "/" in probe else TOOLS_DIR / probe
    if not probe_path.exists():
        return []
    return [command]


def _print_suggestions(state: dict[str, Any], stage_name: str) -> None:
    for command in suggestions_for(state, stage_name):
        print(f"  suggestion: {command}")


def _status_payload(state: dict[str, Any]) -> dict[str, Any]:
    used = len(state.get("repairs", []))
    ok_paths, problems = validate_artifacts(state, state["current_stage"])
    return {
        "run_id": state["run_id"],
        "status": state.get("status", "running"),
        "scope": state.get("scope", ""),
        "slug": state.get("slug", ""),
        "target": state.get("target", ""),
        "requirement": state.get("requirement", ""),
        "revision": state.get("revision", 0),
        "current_stage": state["current_stage"],
        "stages": [
            {"name": s["name"], "status": s["status"], "finished_at": s.get("finished_at")}
            for s in state["stages"]
        ],
        "completed_artifacts": [
            path
            for stage in state["stages"]
            if stage["status"] == "done"
            for path in stage.get("artifacts", [])
        ],
        "registered_artifacts": state.get("artifacts", {}),
        "missing_artifacts": problems,
        "current_stage_valid_artifacts": ok_paths,
        "repairs": {
            "used": used,
            "limit": REPAIR_LIMIT,
            "remaining": max(0, REPAIR_LIMIT - used),
            "entries": state.get("repairs", []),
        },
    }


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    run_id = args.run_id
    if not _validate_run_id(run_id):
        return _fail(f"invalid run id {run_id!r}; expected RUN-<alnum>[-...]")
    run_dir = _run_dir(run_id)
    state_path = run_dir / "state.json"
    if state_path.exists() and not args.force:
        return _fail(f"{_rel(state_path)} already exists; use --force to reinitialize", 2)

    req_arg = Path(args.requirement)
    req_src = req_arg if req_arg.is_absolute() else (ROOT / req_arg)
    req_src = req_src.resolve()
    if not req_src.is_file():
        return _fail(f"requirement file not found: {req_src}", 2)
    try:
        req_src.relative_to(ROOT)
    except ValueError:
        return _fail(f"requirement must stay inside the project: {req_src}", 2)

    slug = _slugify(args.slug or req_src.parent.name)
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(req_src, run_dir / "requirement.md")

    stamp = now_iso()
    stages = []
    for index, definition in enumerate(STAGES):
        stages.append({
            "name": definition["name"],
            "status": "running" if index == 0 else "pending",
            "started_at": stamp if index == 0 else None,
            "finished_at": None,
            "note": "",
            "artifacts": [],
        })
    state = {
        "schema_version": "1.0",
        "run_id": run_id,
        "target": args.target,
        "requirement": _rel(req_src),
        "scope": args.scope,
        "slug": slug,
        "status": "running",
        "current_stage": STAGE_NAMES[0],
        "stages": stages,
        "artifacts": {},
        "repairs": [],
        "repair_limit": REPAIR_LIMIT,
        "created_at": stamp,
        "updated_at": stamp,
        "finished_at": None,
        "revision": 1,
    }
    _atomic_json(state_path, state)
    action = "reinitialized" if args.force else "initialized"
    print(f"{action} {run_id}")
    print(f"  target:      {args.target}")
    print(f"  requirement: {_rel(req_src)} -> {_rel(run_dir / 'requirement.md')}")
    print(f"  slug:        {slug}")
    print(f"  scope:       {args.scope}")
    print(f"  state:       {_rel(state_path)}")
    print(f"  current:     {STAGE_NAMES[0]}")
    print("  next:        fill INIT artifacts (already present), then `advance`")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not _validate_run_id(args.run_id):
        return _fail(f"invalid run id {args.run_id!r}")
    state = _load_state(args.run_id)
    if state is None:
        return _fail(f"run not found: {_state_path(args.run_id)}", 2)
    payload = _status_payload(state)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"{payload['run_id']}  status={payload['status']}  scope={payload['scope']}  "
          f"revision={payload['revision']}")
    print(f"  target:      {payload['target']}")
    print(f"  requirement: {payload['requirement']}")
    print(f"  current:     {payload['current_stage']}")
    print("  stages:")
    for stage in payload["stages"]:
        mark = {"done": "done", "running": "run ", "failed": "FAIL", "pending": "    "}.get(
            stage["status"], stage["status"]
        )
        print(f"    [{mark}] {stage['name']}")
    print("  completed artifacts:")
    if payload["completed_artifacts"]:
        for path in payload["completed_artifacts"]:
            print(f"    - {path}")
    else:
        print("    (none yet)")
    print("  missing artifacts (current stage):")
    if payload["missing_artifacts"]:
        for problem in payload["missing_artifacts"]:
            print(f"    - {problem}")
    else:
        print("    (none)")
    print(f"  repair budget: {payload['repairs']['used']}/{payload['repairs']['limit']} used, "
          f"{payload['repairs']['remaining']} remaining")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    if not _validate_run_id(args.run_id):
        return _fail(f"invalid run id {args.run_id!r}")
    state = _load_state(args.run_id)
    if state is None:
        return _fail(f"run not found: {_state_path(args.run_id)}", 2)

    stage = _current_stage(state)
    name = stage["name"]
    if stage["status"] == "done":
        print(f"stage {name} is already done; nothing to advance (idempotent no-op)")
        print(f"current stage: {state['current_stage']}")
        return 0
    if state.get("status") == "blocked":
        return _fail("run is blocked; cannot advance. Inspect state and resume manually.", 1)

    ok_paths, problems = validate_artifacts(state, name)
    print(f"stage {name}: validating {len(STAGES[STAGE_INDEX[name]]['artifacts'])} artifact pattern(s)")
    for path in ok_paths:
        print(f"  OK      {path}")
    for problem in problems:
        print(f"  PROBLEM {problem}")
    if problems:
        print(f"advance refused: {len(problems)} problem(s) in stage {name}")
        _print_suggestions(state, name)
        print("run `python tools/pipeline.py resume --run-id "
              f"{state['run_id']}` for the next action")
        return 1

    stamp = now_iso()
    stage["status"] = "done"
    stage["finished_at"] = stamp
    stage["artifacts"] = ok_paths
    state["revision"] = int(state.get("revision", 0)) + 1
    state["status"] = "running"
    index = STAGE_INDEX[name]

    if index == len(STAGES) - 1:
        state["status"] = "complete"
        state["finished_at"] = stamp
        _save_state(state)
        print(f"stage {name} done; run is COMPLETE")
        return 0

    next_name = STAGE_NAMES[index + 1]
    next_stage = _stage_entry(state, next_name)
    if next_stage["status"] == "pending":
        next_stage["status"] = "running"
        next_stage["started_at"] = stamp
    state["current_stage"] = next_name
    _save_state(state)
    print(f"stage {name} done; advanced to {next_name}")
    print(f"next action: {STAGES[index + 1]['next_action'].format(run=state['run_id'], slug=state.get('slug', ''))}")
    _print_suggestions(state, next_name)
    return 0


def cmd_fail(args: argparse.Namespace) -> int:
    if not _validate_run_id(args.run_id):
        return _fail(f"invalid run id {args.run_id!r}")
    state = _load_state(args.run_id)
    if state is None:
        return _fail(f"run not found: {_state_path(args.run_id)}", 2)
    stage = _current_stage(state)
    if stage["status"] == "done":
        return _fail(f"stage {stage['name']} is already done; cannot mark it failed", 1)
    stage["status"] = "failed"
    stage["note"] = args.reason
    state["status"] = "failed"
    state["revision"] = int(state.get("revision", 0)) + 1
    _save_state(state)
    print(f"stage {stage['name']} marked failed")
    print(f"  reason: {args.reason}")
    print("  recovery: fix the cause, add artifacts, then `advance` to retry")
    return 0


def cmd_block(args: argparse.Namespace) -> int:
    if not _validate_run_id(args.run_id):
        return _fail(f"invalid run id {args.run_id!r}")
    state = _load_state(args.run_id)
    if state is None:
        return _fail(f"run not found: {_state_path(args.run_id)}", 2)
    state["status"] = "blocked"
    state["blocked_reason"] = args.reason
    state["blocked_at"] = now_iso()
    state["revision"] = int(state.get("revision", 0)) + 1
    _save_state(state)

    sync: dict[str, Any] = {"ok": False, "at": now_iso()}
    evidence_cli = TOOLS_DIR / "evidence.py"
    if not evidence_cli.is_file():
        sync["error"] = "tools/evidence.py not found"
    else:
        command = [
            sys.executable, str(evidence_cli), "update-run",
            "--run-id", state["run_id"],
            "--status", "blocked",
            "--stage", state["current_stage"],
            "--note", args.reason,
        ]
        try:
            proc = subprocess.run(command, cwd=str(ROOT), capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=60)
            sync["returncode"] = proc.returncode
            if proc.returncode == 0:
                sync["ok"] = True
            else:
                sync["error"] = (proc.stderr or proc.stdout or "").strip()[:1000]
        except Exception as exc:  # noqa: BLE001 - manifest sync must not block
            sync["error"] = f"{type(exc).__name__}: {exc}"
    state["manifest_sync"] = sync
    _save_state(state)

    print(f"run {state['run_id']} marked blocked")
    print(f"  reason: {args.reason}")
    if sync["ok"]:
        print("  manifest: run status updated to blocked")
    else:
        print(f"  manifest: NOT updated (non-blocking): {sync.get('error', 'unknown error')}")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    if not _validate_run_id(args.run_id):
        return _fail(f"invalid run id {args.run_id!r}")
    state = _load_state(args.run_id)
    if state is None:
        return _fail(f"run not found: {_state_path(args.run_id)}", 2)
    stage = _current_stage(state)
    used = len(state.get("repairs", []))
    ok_paths, problems = validate_artifacts(state, state["current_stage"])
    definition = STAGES[STAGE_INDEX[state["current_stage"]]]

    print(f"{state['run_id']} resume")
    print(f"  run status:  {state.get('status')}")
    print(f"  target:      {state.get('target')}")
    print(f"  scope:       {state.get('scope')}")
    print(f"  current:     {stage['name']} ({stage['status']})")
    if state.get("status") == "complete":
        print("  next action: none — run is complete")
    else:
        print(f"  next action: {definition['next_action'].format(run=state['run_id'], slug=state.get('slug', ''))}")
        _print_suggestions(state, stage["name"])
    print("  missing artifacts:")
    if problems:
        for problem in problems:
            print(f"    - {problem}")
    else:
        print("    (none)")
    if ok_paths:
        print(f"  valid artifacts: {len(ok_paths)} file(s)")
    print(f"  repair budget: {used}/{REPAIR_LIMIT} used, {max(0, REPAIR_LIMIT - used)} remaining")
    if state.get("blocked_reason"):
        print(f"  blocked reason: {state['blocked_reason']}")
    if stage.get("note"):
        print(f"  stage note:  {stage['note']}")
    for entry in state.get("repairs", []):
        print(f"    repair {entry['at']}: [{entry['class']}] {entry['action']} -> {entry['result']}")
    return 0


def cmd_record_repair(args: argparse.Namespace) -> int:
    if not _validate_run_id(args.run_id):
        return _fail(f"invalid run id {args.run_id!r}")
    state = _load_state(args.run_id)
    if state is None:
        return _fail(f"run not found: {_state_path(args.run_id)}", 2)
    repair_class = args.repair_class.upper()
    if repair_class not in REPAIR_CLASSES:
        return _fail(f"invalid repair class {args.repair_class!r}; expected one of {', '.join(REPAIR_CLASSES)}")

    repairs = state.setdefault("repairs", [])
    if len(repairs) >= REPAIR_LIMIT:
        print(f"repair budget exhausted: {len(repairs)}/{REPAIR_LIMIT} used; "
              f"refusing another repair for {state['run_id']}", file=sys.stderr)
        print("  next step: run `python tools/pipeline.py block --run-id "
              f"{state['run_id']} --reason \"...\"` and hand off to a human/main agent",
              file=sys.stderr)
        return 3

    repairs.append({
        "at": now_iso(),
        "stage": state["current_stage"],
        "class": repair_class,
        "action": args.action,
        "result": args.result,
    })
    state["revision"] = int(state.get("revision", 0)) + 1
    _save_state(state)
    remaining = REPAIR_LIMIT - len(repairs)
    print(f"repair recorded: {len(repairs)}/{REPAIR_LIMIT} used, {remaining} remaining")
    print(f"  stage: {state['current_stage']}  class: {repair_class}")
    print(f"  action: {args.action}")
    print(f"  result: {args.result}")
    return 0


def cmd_set_artifact(args: argparse.Namespace) -> int:
    if not _validate_run_id(args.run_id):
        return _fail(f"invalid run id {args.run_id!r}")
    state = _load_state(args.run_id)
    if state is None:
        return _fail(f"run not found: {_state_path(args.run_id)}", 2)
    target = Path(args.path)
    absolute = target if target.is_absolute() else (ROOT / target)
    absolute = absolute.resolve()
    entry = {
        "path": _rel(absolute),
        "exists": absolute.is_file(),
        "size_bytes": absolute.stat().st_size if absolute.is_file() else None,
        "registered_at": now_iso(),
    }
    state.setdefault("artifacts", {})[args.key] = entry
    state["revision"] = int(state.get("revision", 0)) + 1
    _save_state(state)
    print(f"artifact registered: {args.key} -> {entry['path']} (exists={str(entry['exists']).lower()})")
    if not entry["exists"]:
        print("WARNING: the registered path does not exist yet", file=sys.stderr)
    return 0


def cmd_verify_run(args: argparse.Namespace) -> int:
    if not _validate_run_id(args.run_id):
        return _fail(f"invalid run id {args.run_id!r}")
    state = _load_state(args.run_id)
    checks: list[dict[str, Any]] = []
    missing_artifacts: list[str] = []
    missing_stages: list[str] = []

    if state is None:
        checks.append({"name": "state_exists", "ok": False, "detail": _rel(_state_path(args.run_id))})
        result = {
            "run_id": args.run_id,
            "ok": False,
            "checks": checks,
            "missing_stages": [name for name in STAGE_NAMES],
            "missing_artifacts": ["pipeline_runs/{run}/state.json".replace("{run}", args.run_id)],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    checks.append({"name": "state_exists", "ok": True, "detail": _rel(_state_path(args.run_id))})

    for stage in state["stages"]:
        if stage["status"] != "done":
            missing_stages.append(stage["name"])
    checks.append({
        "name": "all_stages_done",
        "ok": not missing_stages,
        "detail": "all 17 stages done" if not missing_stages else f"not done: {', '.join(missing_stages)}",
    })

    for name in STAGE_NAMES:
        _, problems = validate_artifacts(state, name)
        missing_artifacts.extend(problems)
    checks.append({
        "name": "required_artifacts",
        "ok": not missing_artifacts,
        "detail": f"{len(missing_artifacts)} problem(s)" if missing_artifacts else "all required artifacts valid",
    })

    manifest_run = False
    manifest_detail = "manifest missing"
    if MANIFEST_PATH.is_file():
        try:
            manifest = _load_json(MANIFEST_PATH)
            manifest_run = state["run_id"] in manifest.get("runs", {})
            manifest_detail = "run present" if manifest_run else f"run {state['run_id']} absent"
        except Exception as exc:  # noqa: BLE001
            manifest_detail = f"manifest parse error: {exc}"
    checks.append({"name": "manifest_run", "ok": manifest_run, "detail": manifest_detail})

    junit_path = ROOT / "reports" / "executions" / state["run_id"] / "junit-summary.json"
    junit_ok = False
    junit_detail = _rel(junit_path)
    if junit_path.is_file():
        try:
            _load_json(junit_path)
            junit_ok = junit_path.stat().st_size > 0
            junit_detail = "present and parseable"
        except Exception as exc:  # noqa: BLE001
            junit_detail = f"parse error: {exc}"
    checks.append({"name": "junit_summary", "ok": junit_ok, "detail": junit_detail})

    ok = all(check["ok"] for check in checks)
    result = {
        "run_id": state["run_id"],
        "ok": ok,
        "status": state.get("status"),
        "current_stage": state.get("current_stage"),
        "checks": checks,
        "missing_stages": missing_stages,
        "missing_artifacts": missing_artifacts,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="deterministic stage/artifact pipeline for mooctest-web-testing")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create pipeline_runs/<run>/state.json")
    p.add_argument("--run-id", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--requirement", required=True)
    p.add_argument("--scope", required=True, choices=("smoke", "full"))
    p.add_argument("--slug")
    p.add_argument("--force", action="store_true", help="reinitialize an existing run")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status", help="show stage status and missing artifacts")
    p.add_argument("--run-id", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("advance", help="validate current stage and move to the next")
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("fail", help="mark the current stage failed")
    p.add_argument("--run-id", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_fail)

    p = sub.add_parser("block", help="block the run and sync the manifest if possible")
    p.add_argument("--run-id", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_block)

    p = sub.add_parser("resume", help="print the recovery briefing for a new session")
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("record-repair", help="record one controlled repair (max 3 per run)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--class", dest="repair_class", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--result", required=True)
    p.set_defaults(func=cmd_record_repair)

    p = sub.add_parser("set-artifact", help="register an artifact path in state.json")
    p.add_argument("--run-id", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--path", required=True)
    p.set_defaults(func=cmd_set_artifact)

    p = sub.add_parser("verify-run", help="verify stages, artifacts, manifest and JUnit summary")
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=cmd_verify_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - keep the CLI deterministic
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
