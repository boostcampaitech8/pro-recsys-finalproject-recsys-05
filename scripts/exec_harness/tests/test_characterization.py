import re
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def normalize_output(out: str) -> str:
    normalized = out.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"-\d{8}-\d{6}", "-RUNID", normalized)
    return "\n".join(line.rstrip() for line in normalized.split("\n")).rstrip()


def test_dry_run_matches_golden(repo_root: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/execute.py",
            "--task",
            "scripts/exec_harness/tests/fixtures/task_sample",
            "--dry-run",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    actual_lines = normalize_output(completed.stdout).splitlines()
    golden_path = repo_root / (
        "scripts/exec_harness/tests/fixtures/task_sample/dryrun.golden.txt"
    )
    expected_lines = golden_path.read_text(encoding="utf-8").splitlines()
    assert actual_lines == expected_lines
