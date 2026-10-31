#!/usr/bin/env python3
"""Run the pre-submission gate on every qualification sample.

    python qualification/run_all.py            # human table
    python qualification/run_all.py --json     # machine readable

Each sample owns its own ``--out`` directory under
``qualification/gate-runs/`` so a later run never overwrites an earlier report
by accident (the gate itself overwrites only its own report file).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUAL = ROOT / "qualification"
GATE = ROOT / "tools" / "pre_submission_gate.py"


def sample_dirs(polarity: str) -> list[Path]:
    base = QUAL / polarity
    if not base.is_dir():
        return []
    return sorted(d for d in base.iterdir() if d.is_dir() and (d / "manifest.json").is_file())


def run_sample(polarity: str, directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    run_id = next(iter(manifest["runs"]))
    out = QUAL / "gate-runs" / f"{polarity}-{directory.name}"
    command = [sys.executable, str(GATE), "--run-id", run_id,
               "--manifest", str(directory / "manifest.json"),
               "--cases", str(directory / "cases.csv"),
               "--out", str(out), "--no-env-check", "--json"]
    junit = directory / "junit-summary.json"
    if junit.is_file():
        command += ["--junit-summary", str(junit)]
    requirements = directory / "requirements.csv"
    if requirements.is_file():
        command += ["--requirements", str(requirements)]
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)
    report_path = out / "gate-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    return {
        "polarity": polarity,
        "sample": directory.name,
        "run_id": run_id,
        "exit_code": proc.returncode,
        "delivery_verdict": report.get("delivery_verdict"),
        "test_verdict": report.get("test_verdict"),
        "gate_status": report.get("gate_status"),
        "codes": sorted({f["code"] for f in report.get("findings", [])}),
        "blocking_codes": sorted({f["code"] for f in report.get("findings", []) if not f.get("advisory")}),
        "report": str(report_path.relative_to(ROOT)),
        "stdout_tail": (proc.stdout or "").strip().splitlines()[-1:] if proc.stdout else [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--polarity", choices=("negative", "positive"), default=None)
    args = parser.parse_args(argv)

    polarities = [args.polarity] if args.polarity else ["negative", "positive"]
    results = []
    for polarity in polarities:
        for directory in sample_dirs(polarity):
            results.append(run_sample(polarity, directory))

    summary_path = QUAL / "gate-runs" / "qualification-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    print("| sample | exit | delivery | test | failing codes |")
    print("|---|---|---|---|---|")
    for item in results:
        codes = ", ".join(item["blocking_codes"]) or "-"
        print(f"| {item['polarity']}/{item['sample']} | {item['exit_code']} | "
              f"{item['delivery_verdict']} | {item['test_verdict']} | {codes} |")
    print(f"\nsummary: {summary_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
