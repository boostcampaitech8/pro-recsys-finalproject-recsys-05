"""Verification gates for execute harness steps."""
from __future__ import annotations

from .procio import run


def run_verify(cmd: str, timeout: int):
    if not cmd or not cmd.strip():
        return True, "(verify 없음 — 스킵)"
    r = run(cmd, shell=True, timeout=timeout)
    return r.returncode == 0, (r.stdout or "")
