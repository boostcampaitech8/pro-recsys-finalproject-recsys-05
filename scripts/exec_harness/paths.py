"""Shared filesystem paths for the execute harness."""
from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO / "docs" / "execplan" / "_schemas"
HANDOFF_SCHEMA = SCHEMA_DIR / "handoff.schema.json"
FINDINGS_SCHEMA = SCHEMA_DIR / "findings.schema.json"
RUNS_DIR = REPO / ".exec" / "runs"
