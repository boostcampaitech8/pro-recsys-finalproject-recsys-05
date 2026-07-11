"""Codex CLI invocation and token accounting."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from .paths import FINDINGS_SCHEMA, HANDOFF_SCHEMA, REPO


def _walk_tokens(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower()
            if isinstance(v, (int, float)):
                if "input" in kl and "token" in kl:
                    acc["input"] = max(acc["input"], int(v))
                elif "output" in kl and "token" in kl:
                    acc["output"] = max(acc["output"], int(v))
                elif kl in ("total_tokens", "total_token_count"):
                    acc["total"] = max(acc["total"], int(v))
            _walk_tokens(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _walk_tokens(v, acc)


def parse_tokens(events_text: str) -> dict:
    acc = {"input": 0, "output": 0, "total": 0}
    for line in events_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            _walk_tokens(json.loads(line), acc)
        except json.JSONDecodeError:
            continue
    acc["found"] = bool(acc["input"] or acc["output"] or acc["total"])
    return acc


def find_codex() -> str:
    exe = shutil.which("codex")
    if not exe:
        sys.exit("[execute] codex CLI를 PATH에서 찾을 수 없습니다.")
    return exe


def codex_exec(
    codex,
    prompt,
    summary_path,
    events_path,
    timeout,
    cwd: str | Path = REPO,
):
    cmd = [
        codex, "exec",
        "--sandbox", "workspace-write",
        "-c", "approval_policy=never",
        "--output-schema", str(HANDOFF_SCHEMA),
        "-o", str(summary_path),
        "--json",
        "-",  # 프롬프트는 stdin
    ]
    proc = subprocess.run(
        cmd, cwd=str(cwd), input=prompt, text=True,
        encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
    )
    events_path.write_text(proc.stdout or "", encoding="utf-8")
    summary = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {"_raw": summary_path.read_text(encoding="utf-8")[:2000]}
    return proc.returncode, summary, parse_tokens(proc.stdout or "")


def codex_review(
    codex,
    base,
    out_path,
    events_path,
    timeout,
    cwd: str | Path = REPO,
):
    cmd = [
        codex, "exec", "review", "--base", base,
        "--output-schema", str(FINDINGS_SCHEMA),
        "-o", str(out_path), "--json",
    ]
    proc = subprocess.run(
        cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
    )
    events_path.write_text(proc.stdout or "", encoding="utf-8")
    findings = {}
    if out_path.exists():
        try:
            findings = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            findings = {"_raw": out_path.read_text(encoding="utf-8")[:2000]}
    return proc.returncode, findings, parse_tokens(proc.stdout or "")
