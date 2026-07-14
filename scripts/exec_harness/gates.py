"""Verification gates for execute harness steps."""
from __future__ import annotations

import subprocess

from .procio import run


def run_verify(cmd: str, timeout: int):
    if not cmd or not cmd.strip():
        return False, "verify 필수 — 빈 값은 허용되지 않습니다. 스킵은 verify: skip으로 명시하세요."
    if cmd.strip().lower() == "skip":
        return True, "(verify: skip 명시)"
    try:
        r = run(cmd, shell=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"verify 타임아웃({timeout}s)"
    return r.returncode == 0, (r.stdout or "")
