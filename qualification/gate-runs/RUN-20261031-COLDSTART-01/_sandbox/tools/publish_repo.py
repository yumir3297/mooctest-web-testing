#!/usr/bin/env python3
"""Build a sanitised, publishable snapshot of the project.

The live project keeps its own artefacts untouched (evidence hashes must stay
verifiable). This tool copies an allow-listed subset into ``publish/`` and
redacts local account names / absolute paths, so the snapshot can be pushed to a
public repository without leaking the local environment or redistributing
third-party competition materials.

Usage:
    python tools/publish_repo.py [--out publish] [--force]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Top-level entries that may be published.
INCLUDE = [
    "AGENTS.md",
    "README.md",
    "requirements.txt",
    "pytest.ini",
    "opencode.json",
    "package.json",
    "package-lock.json",
    "docs",
    "tools",
    "tests",
    "tests_meta",
    "tests_meta_report",
    "fixtures",
    "templates",
    ".opencode",
    "knowledge",
    "mooctest-knowledge",
    "reports",
    "evidence",
    "pipeline_runs",
    "qualification",
    "official_2025",
    "submission",
    "backups",
]

# Never published: third-party competition packs, copyrighted books, local
# binaries, dependency trees and build caches.
DENY_PARTS = {
    "materials",
    "booook",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".playwright",
    ".playwright-cli",
    ".screenshots",
    "_原始压缩包",
}
DENY_SUFFIX = {".exe", ".zip", ".xlsx", ".pyc", ".pyd", ".dll", ".msi"}
# Third-party texts kept only in the private working copy.
DENY_PREFIX = [
    "knowledge/01_competition_official",
    "knowledge/02_istqb",
    "knowledge/03_selenium_pytest",
    "knowledge/04_iso_public_summaries",
    "knowledge/05_books_bibliography",
    "knowledge/06_mooctest_courses",
    "knowledge/07_skill_source_notes",
    "mooctest-knowledge/sources",
    "tools/driver/archive",
]
# Duplicate copies of screenshots that already exist under evidence/.
DENY_DIRS = [
    "submission/RUN-AUDIT-20261030-02/screenshots",
    "submission/RUN-20261031-COLDSTART-01/screenshots",
    "official_2025/RUN-20261031-COLDSTART-01/screenshots",
]

TEXT_SUFFIX = {
    ".md", ".py", ".json", ".txt", ".ini", ".js", ".csv", ".yml", ".yaml",
    ".tmpl", ".cfg", ".toml", ".html", ".css",
}

REDACTIONS = [
    (re.compile(r"C:\\Users\\[^\\\s]+"), r"C:\\Users\\<user>"),
    (re.compile(r"D:\\桌面\\软件测试competion"), "<PROJECT_ROOT>"),
    (re.compile(r"<PROJECT_ROOT>"), "<PROJECT_ROOT>"),
    (re.compile(r"<user>"), "<user>"),
]


def denied(rel: Path) -> bool:
    posix = rel.as_posix()
    if any(part in DENY_PARTS for part in rel.parts):
        return True
    if rel.suffix.lower() in DENY_SUFFIX:
        return True
    if any(posix == p or posix.startswith(p + "/") for p in DENY_PREFIX):
        return True
    return any(posix == d or posix.startswith(d + "/") for d in DENY_DIRS)


def redact(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIX:
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    original = text
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    if text != original:
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def build(out: Path, force: bool) -> int:
    if out.exists():
        if not force:
            print(f"ERROR: {out} exists; use --force", file=sys.stderr)
            return 2
        # Keep the git metadata: publish/ is itself the repository working tree.
        for child in out.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        out.mkdir(parents=True)

    copied = 0
    skipped = 0
    redacted = 0
    for name in INCLUDE:
        src = ROOT / name
        if not src.exists():
            continue
        if src.is_file():
            rel = Path(name)
            if denied(rel):
                skipped += 1
                continue
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
            if redact(dst):
                redacted += 1
            continue
        for path in src.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if denied(rel):
                skipped += 1
                continue
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)
            copied += 1
            if redact(dst):
                redacted += 1

    print(f"published {copied} files ({skipped} skipped, {redacted} redacted) -> {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build a sanitised publish snapshot")
    parser.add_argument("--out", default="publish")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    return build(out, args.force)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
