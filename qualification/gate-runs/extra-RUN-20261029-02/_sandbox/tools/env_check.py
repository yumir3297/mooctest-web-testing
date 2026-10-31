#!/usr/bin/env python3
"""Unified environment & toolchain diagnostics for the mooctest workspace.

Usage
-----
    python tools/env_check.py            # human readable report
    python tools/env_check.py --json     # machine readable JSON on stdout (summary on stderr)
    python tools/env_check.py --strict   # treat WARN as failure (exit code 3)
    python tools/env_check.py --chrome PATH --chromedriver PATH   # override discovery

Exit codes
----------
    0   every check PASS, or only WARN without --strict
    2   at least one BLOCKED check
    3   --strict and at least one WARN but no BLOCKED

Status policy (implemented in ``build_checks``)
-----------------------------------------------
* python_version      < 3.8                        -> BLOCKED
* selenium / pytest   import failure                -> BLOCKED
* openpyxl / pillow / opencv / numpy                -> WARN only (vision & packaging deps)
* chrome_binary       not found                     -> BLOCKED
* chrome_version      cannot determine version      -> BLOCKED
* chromedriver_binary missing                       -> BLOCKED
* chromedriver_version cannot execute               -> BLOCKED
* driver_major_match  Chrome major != driver major  -> BLOCKED (audit P0-2 gate, never downgraded)
* driver_source       sha256 != DRIVER.md record    -> BLOCKED
* playwright_cli / node                             -> WARN only
* evidence_dirs / skills_dir                        -> WARN only (recreated by tooling)
  skills_dir additionally requires the 7 project skills under ``.opencode/skills``;
  a missing project skill is WARN, never BLOCKED (a capability gap cannot break a run)

The script never hardcodes expected tool versions: it reports what is actually
installed. Only *minimum requirements* are fixed constants.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER_DIR = ROOT / "tools" / "driver"
DRIVER_EXE = DRIVER_DIR / "chromedriver.exe"
DRIVER_MD = DRIVER_DIR / "DRIVER.md"
DRIVER_ARCHIVE = DRIVER_DIR / "archive"

MIN_PYTHON = (3, 8)

# The 7 project skills that must ship with this workspace (``.opencode/skills``).
# A missing one is a capability gap, not a broken toolchain, so it is WARN only.
PROJECT_SKILLS = (
    "browser-exploration",
    "mooctest-web-testing",
    "selenium-testing",
    "test-case-design",
    "test-reporting",
    "visual-testing",
    "test-design-methodology",
)

STATUS_PASS = "PASS"
STATUS_WARN = "WARN"
STATUS_BLOCKED = "BLOCKED"

EXIT_OK = 0
EXIT_BLOCKED = 2
EXIT_STRICT_WARN = 3

SUBPROCESS_TIMEOUT = 30


@dataclass
class Check:
    id: str
    status: str
    detail: str
    evidence: str


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _run(cmd: list[str], timeout: int = SUBPROCESS_TIMEOUT) -> tuple[int, str]:
    """Run a command and return (returncode, merged output). Never raises."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, (proc.stdout or "").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return -1, f"{type(exc).__name__}: {exc}"


def _first_line(text: str, limit: int = 200) -> str:
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line[:limit]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def _version_tuple(text: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", text or "")
    return tuple(int(p) for p in parts[:4]) if parts else ()


def _windows_file_version(path: Path) -> str | None:
    """Read the PE version resource (reliable when ``chrome.exe --version`` is not)."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:  # pragma: no cover - ctypes is stdlib on CPython
        return None

    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [
            ("dwSignature", wintypes.DWORD),
            ("dwStrucVersion", wintypes.DWORD),
            ("dwFileVersionMS", wintypes.DWORD),
            ("dwFileVersionLS", wintypes.DWORD),
            ("dwProductVersionMS", wintypes.DWORD),
            ("dwProductVersionLS", wintypes.DWORD),
            ("dwFileFlagsMask", wintypes.DWORD),
            ("dwFileFlags", wintypes.DWORD),
            ("dwFileOS", wintypes.DWORD),
            ("dwFileType", wintypes.DWORD),
            ("dwFileSubtype", wintypes.DWORD),
            ("dwFileDateMS", wintypes.DWORD),
            ("dwFileDateLS", wintypes.DWORD),
        ]

    try:
        version = ctypes.WinDLL("version")
        target = str(path)
        size = version.GetFileVersionInfoSizeW(target, None)
        if not size:
            return None
        buffer = ctypes.create_string_buffer(size)
        if not version.GetFileVersionInfoW(target, 0, size, buffer):
            return None
        pointer = ctypes.c_void_p()
        length = wintypes.UINT()
        if not version.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)):
            return None
        info = ctypes.cast(pointer, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        ms, ls = info.dwFileVersionMS, info.dwFileVersionLS
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except (OSError, AttributeError, ValueError):
        return None


def _chrome_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("MOOCTEST_CHROME", "CHROME_BINARY", "CHROME_PATH"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))
    if os.name == "nt":
        for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env_name)
            if base:
                candidates.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")
        candidates.append(Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
    else:
        candidates.extend(Path(p) for p in (
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ))
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _chrome_version(binary: Path) -> tuple[str | None, str]:
    """Return (version, resolution_method)."""
    if os.name == "nt":
        from_resource = _windows_file_version(binary)
        if from_resource:
            return from_resource, "pe-version-resource"

    code, output = _run([str(binary), "--version"], timeout=20)
    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output or "")
    if code == 0 and match:
        return match.group(1), "cli --version"

    if os.name == "nt":
        try:
            versions = [
                child.name
                for child in binary.parent.iterdir()
                if child.is_dir() and re.fullmatch(r"\d+\.\d+\.\d+\.\d+", child.name)
            ]
        except OSError:
            versions = []
        if versions:
            versions.sort(key=_version_tuple)
            return versions[-1], "install-dir-fallback"
    return None, f"unavailable (exit={code}, output={_first_line(output)!r})"


def _driver_version(binary: Path) -> tuple[str | None, str]:
    code, output = _run([str(binary), "--version"], timeout=20)
    match = re.search(r"ChromeDriver\s+(\d+\.\d+\.\d+\.\d+)", output or "")
    if code == 0 and match:
        return match.group(1), _first_line(output)
    return None, f"exit={code}, output={_first_line(output)!r}"


def _package_check(check_id: str, module: str, distribution: str, blocking: bool) -> Check:
    try:
        imported = importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001 - any import error is a finding
        status = STATUS_BLOCKED if blocking else STATUS_WARN
        return Check(check_id, status, f"import {module} failed: {type(exc).__name__}: {exc}",
                     f"python -c \"import {module}\"")
    module_version = getattr(imported, "__version__", None)
    dist_name = "unknown"
    try:
        from importlib.metadata import version as dist_version

        dist_name = dist_version(distribution)
    except Exception:  # noqa: BLE001 - metadata may be absent for vendored builds
        pass
    if dist_name == "unknown" and module_version:
        dist_name = module_version
    if module_version and dist_name != module_version:
        detail = f"{distribution} {dist_name} (import {module} ok, runtime {module_version})"
    else:
        detail = f"{distribution} {dist_name} (import {module} ok)"
    return Check(check_id, STATUS_PASS, detail,
                 f"python -c \"import {module}; print({module}.__version__)\"")


def _read_driver_record() -> tuple[str | None, str | None, str]:
    """Return (sha256, version, note) recorded in tools/driver/DRIVER.md."""
    if not DRIVER_MD.exists():
        return None, None, f"{DRIVER_MD.relative_to(ROOT)} missing"
    text = DRIVER_MD.read_text(encoding="utf-8", errors="replace")
    sha_match = re.search(r"SHA-256[^\n]*?([0-9A-Fa-f]{64})", text)
    ver_match = re.search(r"ChromeDriver 版本[^\n`]*`([0-9]+(?:\.[0-9]+){1,3})`", text)
    sha = sha_match.group(1).upper() if sha_match else None
    ver = ver_match.group(1) if ver_match else None
    note = f"parsed {DRIVER_MD.relative_to(ROOT)}"
    return sha, ver, note


def _playwright_cli() -> tuple[str | None, str]:
    candidates: list[Path] = []
    local = ROOT / "node_modules" / ".bin"
    if os.name == "nt":
        candidates.append(local / "playwright-cli.cmd")
    candidates.append(local / "playwright-cli")
    for name in ("playwright-cli", "playwright-cli.cmd"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        if not candidate.exists():
            continue
        if os.name == "nt" and candidate.suffix.lower() in (".cmd", ".bat"):
            code, output = _run(["cmd", "/c", str(candidate), "--version"], timeout=30)
        else:
            code, output = _run([str(candidate), "--version"], timeout=30)
        if code == 0 and output:
            return _first_line(output), f"{candidate} -> {_first_line(output)}"
    return None, "not found (PATH and node_modules/.bin)"


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def build_checks(chrome_override: str | None, driver_override: str | None) -> tuple[list[Check], dict]:
    checks: list[Check] = []
    facts: dict = {}

    # --- runtime -----------------------------------------------------------
    py = platform.python_version()
    if sys.version_info[:2] < MIN_PYTHON:
        checks.append(Check("python_version", STATUS_BLOCKED,
                            f"Python {py} < required {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
                            f"{sys.executable}"))
    else:
        checks.append(Check("python_version", STATUS_PASS,
                            f"Python {py} (>= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})",
                            f"{sys.executable}"))
    facts["python_executable"] = sys.executable
    facts["platform"] = platform.platform()

    checks.append(_package_check("selenium", "selenium", "selenium", blocking=True))
    checks.append(_package_check("pytest", "pytest", "pytest", blocking=True))
    checks.append(_package_check("openpyxl", "openpyxl", "openpyxl", blocking=False))
    checks.append(_package_check("pillow", "PIL", "pillow", blocking=False))
    checks.append(_package_check("opencv", "cv2", "opencv-python", blocking=False))
    checks.append(_package_check("numpy", "numpy", "numpy", blocking=False))

    # --- chrome ------------------------------------------------------------
    chrome_path: Path | None = None
    if chrome_override:
        candidate = Path(chrome_override)
        if candidate.exists():
            chrome_path = candidate
    if chrome_path is None:
        for candidate in _chrome_candidates():
            if candidate.exists():
                chrome_path = candidate
                break
    if chrome_path is None:
        checks.append(Check("chrome_binary", STATUS_BLOCKED,
                            "Chrome executable not found (env MOOCTEST_CHROME, standard install dirs, PATH)",
                            "checked: " + "; ".join(str(p) for p in _chrome_candidates()[:4])))
        checks.append(Check("chrome_version", STATUS_BLOCKED,
                            "skipped: chrome binary missing", "n/a"))
        chrome_version = None
    else:
        checks.append(Check("chrome_binary", STATUS_PASS, str(chrome_path),
                            f"{chrome_path} (exists, {_human_bytes(chrome_path.stat().st_size)})"))
        chrome_version, method = _chrome_version(chrome_path)
        if chrome_version:
            checks.append(Check("chrome_version", STATUS_PASS, chrome_version,
                                f"resolution={method}, binary={chrome_path}"))
        else:
            checks.append(Check("chrome_version", STATUS_BLOCKED,
                                f"cannot determine Chrome version: {method}",
                                f"binary={chrome_path}"))
    facts["chrome_binary"] = str(chrome_path) if chrome_path else None
    facts["chrome_version"] = chrome_version

    # --- chromedriver ------------------------------------------------------
    driver_path = Path(driver_override) if driver_override else DRIVER_EXE
    driver_version: str | None = None
    if not driver_path.exists():
        checks.append(Check("chromedriver_binary", STATUS_BLOCKED,
                            f"missing: {driver_path}", str(driver_path)))
        checks.append(Check("chromedriver_version", STATUS_BLOCKED,
                            "skipped: chromedriver binary missing", "n/a"))
    else:
        checks.append(Check("chromedriver_binary", STATUS_PASS, str(driver_path),
                            f"{driver_path} (exists, {_human_bytes(driver_path.stat().st_size)})"))
        driver_version, raw = _driver_version(driver_path)
        if driver_version:
            checks.append(Check("chromedriver_version", STATUS_PASS, driver_version,
                                f"cmd: {driver_path} --version -> {raw}"))
        else:
            checks.append(Check("chromedriver_version", STATUS_BLOCKED,
                                f"cannot execute chromedriver: {raw}",
                                f"cmd: {driver_path} --version"))
    facts["chromedriver_binary"] = str(driver_path)
    facts["chromedriver_version"] = driver_version

    # --- major version gate (audit P0-2) -----------------------------------
    chrome_major = _version_tuple(chrome_version or "")[:1]
    driver_major = _version_tuple(driver_version or "")[:1]
    if chrome_major and driver_major:
        if chrome_major == driver_major:
            checks.append(Check("driver_major_match", STATUS_PASS,
                                f"chrome major {chrome_major[0]} == driver major {driver_major[0]}",
                                f"chrome={chrome_version}, chromedriver={driver_version}"))
        else:
            checks.append(Check("driver_major_match", STATUS_BLOCKED,
                                f"chrome major {chrome_major[0]} != driver major {driver_major[0]} "
                                f"(update tools/driver/chromedriver.exe, see tools/driver/DRIVER.md)",
                                f"chrome={chrome_version}, chromedriver={driver_version}"))
    else:
        checks.append(Check("driver_major_match", STATUS_BLOCKED,
                            "cannot compare majors: chrome or chromedriver version unknown",
                            f"chrome={chrome_version}, chromedriver={driver_version}"))

    # --- driver provenance -------------------------------------------------
    recorded_sha, recorded_version, record_note = _read_driver_record()
    archive_note = ""
    if DRIVER_ARCHIVE.is_dir():
        archived = sorted(p.name for p in DRIVER_ARCHIVE.glob("*.exe"))
        if archived:
            archive_note = f"; archive: {', '.join(archived)}"
    if not driver_path.exists():
        checks.append(Check("driver_source", STATUS_BLOCKED,
                            "cannot hash missing chromedriver", str(driver_path)))
    else:
        actual_sha = _sha256(driver_path)
        facts["chromedriver_sha256"] = actual_sha
        if recorded_sha is None:
            checks.append(Check("driver_source", STATUS_BLOCKED,
                                f"no SHA-256 record found ({record_note})",
                                f"actual sha256={actual_sha}"))
        elif recorded_sha != actual_sha:
            checks.append(Check("driver_source", STATUS_BLOCKED,
                                "sha256 mismatch vs tools/driver/DRIVER.md "
                                f"(recorded {recorded_sha[:16]}..., actual {actual_sha[:16]}...)",
                                f"recorded={recorded_sha}; actual={actual_sha}"))
        else:
            checks.append(Check("driver_source", STATUS_PASS,
                                f"sha256 matches DRIVER.md (recorded driver {recorded_version or 'unknown'})",
                                f"sha256={actual_sha}; source={record_note}{archive_note}"))

    # --- node / playwright -------------------------------------------------
    node = shutil.which("node")
    if node:
        code, output = _run([node, "--version"], timeout=20)
        version = _first_line(output) if code == 0 else ""
        checks.append(Check("node", STATUS_PASS if version else STATUS_WARN,
                            f"node {version} ({node})" if version else f"node found but not runnable: {output}",
                            f"{node} --version"))
    else:
        checks.append(Check("node", STATUS_WARN, "node not found on PATH", "shutil.which('node') -> None"))

    pw_version, pw_note = _playwright_cli()
    if pw_version:
        checks.append(Check("playwright_cli", STATUS_PASS, f"playwright-cli {pw_version}", pw_note))
    else:
        checks.append(Check("playwright_cli", STATUS_WARN,
                            "playwright-cli not runnable (browser exploration via MCP still works)",
                            pw_note))

    # --- workspace layout --------------------------------------------------
    required = {
        "evidence/raw": ROOT / "evidence" / "raw",
        "evidence/annotated": ROOT / "evidence" / "annotated",
        "evidence/diff": ROOT / "evidence" / "diff",
        "evidence/logs": ROOT / "evidence" / "logs",
        "reports/executions": ROOT / "reports" / "executions",
    }
    missing = [name for name, path in required.items() if not path.is_dir()]
    manifest = ROOT / "evidence" / "manifest.json"
    manifest_note = "manifest.json present" if manifest.exists() else "manifest.json absent (run tools/evidence.py init)"
    if missing:
        checks.append(Check("evidence_dirs", STATUS_WARN,
                            f"missing dirs: {', '.join(missing)}; {manifest_note}",
                            "; ".join(f"{n}={'ok' if (ROOT / n).is_dir() else 'missing'}" for n in required)))
    else:
        checks.append(Check("evidence_dirs", STATUS_PASS,
                            f"all {len(required)} evidence dirs present; {manifest_note}",
                            "; ".join(f"{n}=ok" for n in required)))

    project_dir = ROOT / ".opencode" / "skills"
    external_dir = ROOT / ".agents" / "skills"
    project_present = [name for name in PROJECT_SKILLS if (project_dir / name).is_dir()]
    project_missing = [name for name in PROJECT_SKILLS if name not in project_present]
    external_count = (
        sum(1 for child in external_dir.iterdir() if child.is_dir())
        if external_dir.is_dir() else 0
    )
    knowledge_missing = [
        name for name in ("knowledge", "mooctest-knowledge") if not (ROOT / name).is_dir()
    ]
    detail = (
        f"project={len(project_present)} (.opencode/skills) "
        f"external={external_count} (.agents/skills), missing={len(project_missing)}"
    )
    if project_missing:
        detail += ": " + ", ".join(project_missing)
    if knowledge_missing:
        detail += "; missing dirs: " + ", ".join(knowledge_missing)
    skills_ok = not project_missing and external_count > 0 and not knowledge_missing
    checks.append(Check(
        "skills_dir",
        STATUS_PASS if skills_ok else STATUS_WARN,
        detail,
        f"project_dir={project_dir} ({len(project_present)}/{len(PROJECT_SKILLS)} required); "
        f"external_dir={external_dir} ({external_count}); "
        f"missing={project_missing or 'none'}; knowledge_missing={knowledge_missing or 'none'}",
    ))

    return checks, facts


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def summarize(checks: list[Check]) -> tuple[dict, str]:
    counts = {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_BLOCKED: 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    if counts[STATUS_BLOCKED]:
        verdict = "BLOCKED"
    elif counts[STATUS_WARN]:
        verdict = "READY_WITH_WARNINGS"
    else:
        verdict = "READY"
    return counts, verdict


def exit_code_for(counts: dict, strict: bool) -> int:
    if counts[STATUS_BLOCKED]:
        return EXIT_BLOCKED
    if strict and counts[STATUS_WARN]:
        return EXIT_STRICT_WARN
    return EXIT_OK


def render_human(checks: list[Check], counts: dict, verdict: str, code: int) -> str:
    width = max(len(c.id) for c in checks) + 2
    lines = ["== mooctest env_check =="]
    for check in checks:
        lines.append(f"[{check.status:<7}] {check.id:<{width}} {check.detail}")
    lines.append("")
    lines.append(
        f"verdict: {verdict}  (PASS={counts[STATUS_PASS]} WARN={counts[STATUS_WARN]} "
        f"BLOCKED={counts[STATUS_BLOCKED]})  exit={code}"
    )
    blocked = [c.id for c in checks if c.status == STATUS_BLOCKED]
    warned = [c.id for c in checks if c.status == STATUS_WARN]
    if blocked:
        lines.append("blocking: " + ", ".join(blocked))
    if warned:
        lines.append("warnings: " + ", ".join(warned))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose the Selenium/Chrome/pytest toolchain of this workspace.",
        epilog="exit codes: 0 ok (or WARN without --strict), 2 BLOCKED, 3 --strict with WARN",
    )
    parser.add_argument("--json", action="store_true", help="emit machine readable JSON on stdout")
    parser.add_argument("--strict", action="store_true", help="return 3 when any WARN exists")
    parser.add_argument("--chrome", default=None, help="override Chrome executable path")
    parser.add_argument("--chromedriver", default=None, help="override chromedriver executable path")
    args = parser.parse_args(argv)

    checks, facts = build_checks(args.chrome, args.chromedriver)
    counts, verdict = summarize(checks)
    code = exit_code_for(counts, args.strict)

    payload = {
        "verdict": verdict,
        "strict": bool(args.strict),
        "exit_code": code,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "PASS": counts[STATUS_PASS],
            "WARN": counts[STATUS_WARN],
            "BLOCKED": counts[STATUS_BLOCKED],
            "total": len(checks),
        },
        "blocking": [c.id for c in checks if c.status == STATUS_BLOCKED],
        "warnings": [c.id for c in checks if c.status == STATUS_WARN],
        "facts": facts,
        "checks": [asdict(c) for c in checks],
    }

    human = render_human(checks, counts, verdict, code)
    if args.json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        sys.stdout.flush()
        sys.stderr.write(human + "\n")
    else:
        sys.stdout.write(human + "\n")
    return code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
