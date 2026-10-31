"""Run a command and save its raw stdout bytes (UTF-8 safe on PowerShell 5.1).

PowerShell's ``>`` re-encodes stdout as UTF-16 and corrupts Chinese text, so
every JSON artifact produced from a console command goes through this helper.

    python capture.py <output-file> -- <command> [args...]
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    if "--" not in argv:
        print(__doc__, file=sys.stderr)
        return 2
    split = argv.index("--")
    out = Path(argv[0])
    cmd = argv[split + 1:]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, env=env)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
    print(f"[capture] {' '.join(cmd)} -> {out} (exit={proc.returncode}, {len(proc.stdout)} bytes)")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
