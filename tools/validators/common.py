"""Shared primitives for the pre-submission quality gate.

The module intentionally contains no gate logic: it only defines the finding
model, the verdict aggregation rules and small text/JSON helpers so every gate
reports in exactly the same way.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------- #
# verdict scale
# --------------------------------------------------------------------------- #
# PASS < WARNING < UNVERIFIED < FAIL < BLOCKED
# UNVERIFIED means "cannot tell", which is worse than a known warning but less
# severe than a proven failure: it must never be silently reported as PASS.
SEVERITY_ORDER: dict[str, int] = {
    "PASS": 0,
    "WARNING": 1,
    "UNVERIFIED": 2,
    "FAIL": 3,
    "BLOCKED": 4,
}

GATES: tuple[str, ...] = ("G0", "G1", "G2", "G3", "G4", "G5", "G6")

DELIVERY_VERDICTS = ("PASS", "WARNING", "FAIL", "BLOCKED", "UNVERIFIED")
TEST_VERDICTS = ("PASS", "FAIL", "BLOCKED", "UNVERIFIED")

EXIT_CODE: dict[str, int] = {
    "PASS": 0,
    "WARNING": 0,
    "FAIL": 1,
    "BLOCKED": 2,
    "UNVERIFIED": 3,
}


def worst_severity(values: Iterable[str]) -> str:
    """Return the most severe value of ``values`` (PASS when empty)."""
    result = "PASS"
    for value in values:
        if SEVERITY_ORDER.get(value, 0) > SEVERITY_ORDER[result]:
            result = value
    return result


# --------------------------------------------------------------------------- #
# findings
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    """One machine readable gate finding (contract §4)."""

    gate: str
    code: str
    severity: str
    subject: str
    message: str
    evidence: str = ""
    # Advisory findings are recorded for transparency but never block a local
    # rehearsal (e.g. "AI usage was not declared").  In --official-submission
    # mode the caller turns them into real BLOCKED findings instead.
    advisory: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "gate": self.gate,
            "code": self.code,
            "severity": self.severity,
            "subject": self.subject,
            "message": self.message,
            "evidence": self.evidence,
        }
        if self.advisory:
            payload["advisory"] = True
        return payload


class Report:
    """Collects findings and computes gate / delivery verdicts."""

    def __init__(self, run_id: str, gates: Sequence[str] = GATES) -> None:
        self.run_id = run_id
        self.gates: list[str] = [g for g in GATES if g in set(gates)]
        self.findings: list[Finding] = []
        self.checks = 0
        self.checks_passed = 0
        self.skipped: dict[str, str] = {}

    # -- recording ---------------------------------------------------------- #
    def add(self, gate: str, code: str, severity: str, subject: str, message: str,
            evidence: str = "", advisory: bool = False) -> Finding:
        if severity not in SEVERITY_ORDER:
            raise ValueError(f"invalid severity: {severity}")
        finding = Finding(gate, code, severity, subject, message, evidence, advisory)
        self.findings.append(finding)
        return finding

    def check(self, gate: str, code: str, passed: bool, subject: str, message: str,
              severity: str = "FAIL", evidence: str = "", advisory: bool = False) -> bool:
        """Record one check; a failed check becomes a finding."""
        self.checks += 1
        if passed:
            self.checks_passed += 1
            return True
        self.add(gate, code, severity, subject, message, evidence, advisory)
        return False

    def skip(self, gate: str, reason: str) -> None:
        self.skipped[gate] = reason

    # -- aggregation -------------------------------------------------------- #
    def findings_of(self, gate: str) -> list[Finding]:
        return [f for f in self.findings if f.gate == gate]

    def gate_status(self) -> dict[str, str]:
        """Worst *non-advisory* severity per gate (advisory items are listed in
        ``findings`` and in the top level ``advisory`` block instead)."""
        status: dict[str, str] = {}
        for gate in GATES:
            if gate not in self.gates:
                status[gate] = "SKIP"
                continue
            if gate in self.skipped:
                status[gate] = "SKIP"
                continue
            severities = [f.severity for f in self.findings_of(gate) if not f.advisory]
            status[gate] = worst_severity(severities) if severities else "PASS"
        return status

    def delivery_verdict(self) -> str:
        """Worst *blocking* finding.  Advisory findings do not block delivery."""
        return worst_severity(f.severity for f in self.findings if not f.advisory)

    def summary(self) -> dict[str, int]:
        counts = {"FAIL": 0, "WARNING": 0, "BLOCKED": 0, "UNVERIFIED": 0,
                  "PASS": self.checks_passed}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def codes(self) -> list[str]:
        return [f.code for f in self.findings]


# --------------------------------------------------------------------------- #
# io / text helpers
# --------------------------------------------------------------------------- #
def load_json(path: Path) -> tuple[Any | None, str | None]:
    """Load JSON, returning ``(data, error)`` and never raising."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None, "missing"
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slug(text: str, limit: int = 80) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "_", str(text or "")).strip("_")
    return cleaned[:limit] or "-"


def first_line(text: str, limit: int = 240) -> str:
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line[:limit]


_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def major_of(value: Any) -> int | None:
    """Return the major version of a version-ish string, or ``None``."""
    if value is None:
        return None
    match = _VERSION_RE.search(str(value))
    return int(match.group(1)) if match else None


def sort_key(text: str) -> str:
    return str(text or "").strip().lower()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v not in (None, "")]
    return [value]


def truncate(items: Sequence[Any], limit: int = 8) -> str:
    values = [str(i) for i in items]
    if len(values) <= limit:
        return ", ".join(values)
    return ", ".join(values[:limit]) + f" (+{len(values) - limit} more)"
