"""Validators used by :mod:`tools.pre_submission_gate`.

Each module owns one gate of the pre-submission quality gate:

``env``             G0  environment + compliance
``cases``           G1  requirement / test case table
``scripts``         G2  test code, pytest collection and JUnit cross-check
``evidence_check``  G3  evidence registry, defect and triage checks
``defects``         G3  defect object field/status rules (used by G3)
``package``         G4  submission package structure and hashes

The modules never write outside the paths handed to them.  ``evidence_check``
reuses :func:`tools.evidence.verify_evidence` instead of re-implementing hashing.
"""

from __future__ import annotations

__all__ = ["common", "env", "cases", "scripts", "evidence_check", "defects", "package"]
