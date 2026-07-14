"""Command-line entry point for the execute harness."""
from __future__ import annotations

import argparse
import sys

from .runner import run


# Windows 콘솔 기본 인코딩(cp949)이 한글·이모지를 못 찍으므로 UTF-8 강제
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="codex exec 기반 다단계 티켓 실행기")
    ap.add_argument("--task", required=True, help="docs/execplan/<TICKET> 디렉터리")
    ap.add_argument("--from", dest="from_step", default=None, help="재개 지점 (예: step2)")
    ap.add_argument("--dry-run", action="store_true", help="프롬프트·명령만 출력, codex/git 미실행")
    ap.add_argument("--no-branch", action="store_true", help="브랜치 전환 안 함(현재 위치에서)")
    ap.add_argument("--no-commit", action="store_true", help="step 커밋 안 함")
    ap.add_argument("--allow-dirty", action="store_true", help="dirty 워킹트리에서도 실행(무관 변경 커밋 위험 감수)")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--no-pr", action="store_true")
    ap.add_argument("--no-review", action="store_true", help="교차 리뷰(codex exec review) 생략")
    ap.add_argument("--base", default=None, help="base 브랜치(기본: task.md base_branch 또는 dev)")
    ap.add_argument("--self-repair", type=int, default=2, help="verify 실패 시 재시도 횟수(기본 2)")
    ap.add_argument("--timeout", type=int, default=1800, help="codex/verify 개별 타임아웃 초")
    args = ap.parse_args(argv)
    return run(args)
