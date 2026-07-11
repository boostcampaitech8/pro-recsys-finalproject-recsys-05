"""Subprocess and git helpers for the execute harness."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .paths import REPO


def run(
    cmd,
    *,
    shell=False,
    timeout=None,
    check=False,
    capture=True,
    cwd: str | Path = REPO,
):
    return subprocess.run(
        cmd, cwd=str(cwd), shell=shell, timeout=timeout, check=check,
        text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def git(*args, check=False) -> str:
    r = run(["git", *args])
    if check and r.returncode != 0:  # 코덱스 리뷰 P2: 실패를 삼키지 않는다
        raise RuntimeError(f"git {' '.join(args)} 실패(rc={r.returncode}):\n{(r.stdout or '').strip()}")
    return r.stdout or ""


def current_branch() -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD").strip()


def short_sha() -> str:
    return git("rev-parse", "--short", "HEAD").strip()
