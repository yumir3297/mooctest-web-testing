#!/usr/bin/env python3
"""Pre-run isolation check for exam clean rooms.

This is a *path-based* gate, not an OS security boundary. It catches the
accidental presence of known answer sources or prior target-specific outputs in
a freshly built clean room. Run it BEFORE the test starts; after the run,
reports/evidence/tests-generated are expected outputs and will be flagged if you
run the check again.

Usage:
    python tools/isolation_check.py --workspace <clean_room> --json
    python tools/isolation_check.py --workspace <clean_room> --strict

Exit codes:
    0  clean
    2  contaminated
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Known answer sources and prior target-specific outputs. All paths are relative
# to the clean-room root. A clean room must not contain any of them before the
# test starts.
FORBIDDEN = [
    "materials/参考答案",
    "official_2025",
    "submission",
    "reports",
    "evidence",
    "pipeline_runs",
    "qualification",
    "knowledge",
    "publish",
    "booook",
    "backups",
    "tests/generated",
    "fixtures",
]

# Answer-like names under materials/ (the question pack itself is allowed).
ANSWER_HINTS = ("参考答案", "答案", "solution", "answer_key", "answer-key")


def _is_forbidden_name(path: Path) -> bool:
    name = path.name.lower()
    return any(hint.lower() in name for hint in ANSWER_HINTS)


def scan(root: Path) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for rel in FORBIDDEN:
        candidate = root / rel
        if candidate.exists():
            found.append({
                "path": rel,
                "kind": "dir" if candidate.is_dir() else "file",
            })

    # Check answer-like filenames only under materials/, to keep the scan fast
    # and avoid false positives in source code or test fixtures.
    materials = root / "materials"
    if materials.is_dir():
        for path in materials.rglob("*"):
            if path.is_file() and _is_forbidden_name(path):
                found.append({
                    "path": path.relative_to(root).as_posix(),
                    "kind": "answer-name",
                })

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in found:
        if item["path"] in seen:
            continue
        seen.add(item["path"])
        unique.append(item)
    return unique


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="check a clean room for answer leakage")
    parser.add_argument("--workspace", default=".", help="clean-room root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="kept for CI symmetry; exit 2 on any finding")
    args = parser.parse_args(argv)

    root = Path(args.workspace).resolve()
    if not root.is_dir():
        print(f"ERROR: workspace not found: {root}", file=sys.stderr)
        return 2

    found = scan(root)
    verdict = "ISOLATION_CLEAN" if not found else "ISOLATION_CONTAMINATED"
    payload = {
        "workspace": str(root),
        "verdict": verdict,
        "found": found,
        "note": "pre-run check only; reports/evidence/tests-generated are expected after a run",
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"workspace: {root}")
        for item in found:
            print(f"[FOUND] {item['path']} ({item['kind']})")
        print(f"verdict: {verdict}  (found={len(found)})")
        if found:
            print("Move answer sources outside the clean room, or rebuild the clean room.")

    return 0 if not found else 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
