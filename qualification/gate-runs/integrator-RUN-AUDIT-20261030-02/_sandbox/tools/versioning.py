#!/usr/bin/env python3
"""Version helpers shared by the test harness and the CLIs.

`chrome.exe --version` prints nothing useful on Windows and its console output
is not UTF-8, so the Windows fixed file version is the reliable source. The
Chromium based `chromedriver.exe --version` does print to stdout.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?")


def win_file_version(path: Path) -> str:
    """Return the Windows fixed file version (e.g. ``156.0.8078.74``) or ``""``."""
    if os.name != "nt":
        return ""
    try:
        import ctypes
        from ctypes import wintypes

        size = ctypes.windll.version.GetFileVersionInfoSizeW(str(path), None)
        if not size:
            return ""
        buffer = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(str(path), 0, size, buffer):
            return ""
        pointer = ctypes.c_void_p()
        length = wintypes.UINT()
        if not ctypes.windll.version.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)):
            return ""

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD), ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD), ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD), ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD), ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD), ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD), ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD),
            ]

        info = ctypes.cast(pointer, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        ms, ls = info.dwProductVersionMS, info.dwProductVersionLS
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:
        return ""


def first_line(cmd: list[str], timeout: int = 30) -> str:
    """Run a command and return its first output line, never raising."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"<error: {exc}>"
    text = (proc.stdout or proc.stderr or "").strip()
    return text.splitlines()[0] if text else ""


def exe_version(path: Path, args: tuple[str, ...] = ("--version",)) -> str:
    """Best-effort version string for a Windows executable."""
    if not path or not Path(path).is_file():
        return "<not found>"
    printed = first_line([str(path), *args])
    if printed and VERSION_RE.search(printed) and not printed.startswith("<error"):
        return printed
    file_version = win_file_version(Path(path))
    if file_version:
        return f"Chrome {file_version}" if Path(path).name.lower() == "chrome.exe" else file_version
    return printed or "<empty>"


def major(value: str) -> int | None:
    match = VERSION_RE.search(value or "")
    return int(match.group(1)) if match else None


def find_chrome() -> Path | None:
    candidates = (
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    )
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    return None
