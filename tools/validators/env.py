"""G0 - environment record and AI-usage compliance.

Two independent sources are used:

1. the run's own ``environment`` block in the manifest (the authoritative
   historical fact for that execution), and
2. an *optional* live ``python tools/env_check.py --json`` probe that confirms
   the toolchain on this machine.

The live probe is optional on purpose: ``env_check.py`` is owned by another
module and may be absent.  A missing probe is a WARNING, never an error.  The
manifest block is always checked on its own so the gate still works offline.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from .common import Report, first_line, major_of, truncate

GATE = "G0"

REQUIRED_ENV_KEYS = ("chrome", "chromedriver", "selenium", "pytest")
TRUE_VALUES = {"true", "1", "yes", "y", "confirmed", "declared"}


def _env(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(k): str(v).strip() for k, v in value.items() if v is not None}


def probe_env_check(project_root: Path, python: str = sys.executable, timeout: int = 180) -> dict[str, Any] | None:
    """Run ``tools/env_check.py --json``.  Returns parsed JSON or ``None``."""
    script = project_root / "tools" / "env_check.py"
    if not script.is_file():
        return None
    try:
        proc = subprocess.run([python, str(script), "--json"], cwd=str(project_root),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (proc.stdout or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        payload.setdefault("exit_code", proc.returncode)
    return payload if isinstance(payload, dict) else None


def validate(report: Report, *,
             run_id: str,
             run: Mapping[str, Any] | None,
             env_check: Mapping[str, Any] | None,
             official: bool = False,
             env_check_expected: bool = True) -> dict[str, Any]:
    run = run or {}
    environment = _env(run.get("environment"))
    stats: dict[str, Any] = {"environment_keys": sorted(environment)}

    # --- manifest environment ---------------------------------------------
    missing = [key for key in REQUIRED_ENV_KEYS if not environment.get(key)]
    report.check(GATE, "ENV_RECORD_INCOMPLETE", not missing, run_id,
                 f"run.environment 缺少 {', '.join(missing)}：环境无法复核"
                 + ("（正式提交模式：阻断）" if official else "（本地演练：仅告警）"),
                 "BLOCKED" if official else "WARNING",
                 ", ".join(f"{k}={environment.get(k)}" for k in REQUIRED_ENV_KEYS))
    stats["missing_env_keys"] = missing

    chrome_major = major_of(environment.get("chrome"))
    driver_major = major_of(environment.get("chromedriver"))
    if chrome_major is not None and driver_major is not None:
        report.check(GATE, "ENV_MAJOR_MISMATCH", chrome_major == driver_major, run_id,
                     f"Chrome 主版本 {chrome_major} != ChromeDriver 主版本 {driver_major}",
                     "BLOCKED",
                     f"chrome={environment.get('chrome')!r} chromedriver={environment.get('chromedriver')!r}")
        stats["chrome_major"] = chrome_major
        stats["chromedriver_major"] = driver_major
    else:
        report.check(GATE, "ENV_VERSION_UNPARSABLE", False, run_id,
                     "无法从 run.environment 解析 chrome/chromedriver 主版本，兼容性未验证",
                     "WARNING",
                     f"chrome={environment.get('chrome')!r} chromedriver={environment.get('chromedriver')!r}")

    # --- live probe --------------------------------------------------------
    if env_check is None:
        report.add(GATE, "ENV_CHECK_UNAVAILABLE", "WARNING", "tools/env_check.py",
                   "env_check.py 不存在或无法输出 JSON：跳过实时环境探测，仅使用 manifest 记录"
                   + ("（本次运行显式关闭）" if not env_check_expected else ""),
                   advisory=not env_check_expected)
    else:
        counts = env_check.get("summary") or {}
        blocked = [str(x) for x in (env_check.get("blocking") or [])]
        warnings = [str(x) for x in (env_check.get("warnings") or [])]
        stats["env_check"] = {
            "verdict": env_check.get("verdict"),
            "summary": counts,
            "blocking": blocked,
            "warnings": warnings,
        }
        hard = [item for item in blocked if item in ("driver_major_match",)]
        report.check(GATE, "ENV_CHECK_DRIVER_MISMATCH", not hard, "env_check",
                     f"实时探测报告驱动主版本不一致：{truncate(hard)}", "BLOCKED")
        soft = [item for item in blocked if item not in ("driver_major_match",)]
        report.check(GATE, "ENV_CHECK_BLOCKED", not soft, "env_check",
                     f"实时探测报告阻断项：{truncate(soft)}", "WARNING")
        report.check(GATE, "ENV_CHECK_WARNINGS", not warnings, "env_check",
                     f"实时探测告警项：{truncate(warnings)}", "WARNING")

    # --- AI usage compliance ----------------------------------------------
    meta = run.get("meta") or {}
    declared = str(meta.get("ai_use_confirmed", "")).strip().lower()
    ai_confirmed = declared in TRUE_VALUES
    stats["ai_use_confirmed"] = ai_confirmed
    stats["ai_use_raw"] = declared

    if official:
        report.check(GATE, "AI_USE_NOT_CONFIRMED", ai_confirmed, run_id,
                     "正式提交模式下未声明 AI 使用合规确认（meta.ai_use_confirmed）：阻断。"
                     "门禁不判断官方是否允许 AI，只要求提交者给出书面依据", "BLOCKED")
    else:
        report.check(GATE, "AI_USE_UNVERIFIED", ai_confirmed, run_id,
                     "未声明 AI 使用合规确认（meta.ai_use_confirmed）：本地产出视为 UNVERIFIED，"
                     "不阻断本地演练；正式提交前必须人工核对当届赛项规则",
                     "UNVERIFIED", advisory=True)
    return stats
