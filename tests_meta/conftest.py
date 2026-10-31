"""Make ``tools/validators`` importable for the gate's own tests.

This conftest only adjusts ``sys.path``.  It deliberately does not import the
product ``tests/conftest.py`` and does not run any evidence hook, so
``python -m pytest tests_meta`` can never mutate ``evidence/manifest.json``.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
