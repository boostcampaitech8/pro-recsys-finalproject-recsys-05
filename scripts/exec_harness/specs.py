"""Execplan front-matter parsing and step discovery."""
from __future__ import annotations

import re
from pathlib import Path


def _scalar(v: str):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()] if inner else []
    return v.strip("\"'")


def _parse_yaml_subset(lines: list[str]) -> dict:
    meta: dict = {}
    key = None
    for raw in lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if raw.lstrip().startswith("- ") and key is not None:
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(_scalar(raw.lstrip()[2:]))
            continue
        m = re.match(r"^([\w][\w\-]*):\s*(.*)$", raw)
        if m:
            key, val = m.group(1), m.group(2)
            meta[key] = "" if val.strip() == "" else _scalar(val)
    return meta


def parse_frontmatter(text: str) -> tuple[dict, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text
    return _parse_yaml_subset(lines[1:end]), "\n".join(lines[end + 1:]).strip()


def read_md(path: Path) -> tuple[dict, str]:
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    return meta, body


def step_num(p: Path) -> int:
    """stepN → N (자연 정렬용; 코덱스 미검출 + 내 CL-2: step10 사전순 오류 방지)."""
    m = re.search(r"(\d+)", p.stem)
    return int(m.group(1)) if m else 0


def discover_steps(task_dir: Path, meta: dict) -> list[Path]:
    if meta.get("steps"):
        return [task_dir / s for s in meta["steps"]]
    return sorted(task_dir.glob("step*.md"), key=step_num)
