#!/usr/bin/env python3
"""실체는 exec_harness/ 패키지 — ADR-0005 경로 계약 보존용 shim."""
from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from exec_harness.cli import main


if __name__ == "__main__":
    main()
