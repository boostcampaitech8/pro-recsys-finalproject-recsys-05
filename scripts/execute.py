#!/usr/bin/env python3
"""execute.py — codex exec 기반 다단계 티켓 실행기 (code 레인 자동화).

설계 근거: docs/adr/0005-codex-exec-orchestration.md · 티켓 T13(MAINTENANCE §3).

역할 분리(토큰 관점):
  - AI 레이어(토큰 O) : codex exec(step 코드변경) · codex exec review(교차리뷰)
  - CodeAct 레이어(토큰 0) : verify 실행 · git add/commit · push · gh pr · summary 주입 · state
    → 기계적 행동은 이 스크립트가 결정론적으로 수행한다. codex의 AI 턴은 '코드변경'에만 쓴다.

이관 방식(B1) : 각 step은 fresh `codex exec`. 이전 step들의 구조화 handoff 요약을
  다음 step 프롬프트에 재주입한다(네이티브 resume 아님 — 컨텍스트 완전 제어·감사가능).

입력 : docs/execplan/<TICKET>/ 디렉터리
  task.md  — front-matter(ticket/issue/base_sha/base_branch/branch/steps/seam_guards/dont_touch)
             + 본문(task 개요, 매 step 프롬프트 헤더로 주입)
  stepN.md — front-matter(title/verify) + 본문(bounded task; codex에 전달)

산출 : .exec/runs/<TICKET>-<runid>/ (gitignore) — state.json · stepN.summary.json
       · stepN.events.jsonl · codex_review.json · report.json

사용 예:
  python scripts/execute.py --task docs/execplan/T4 --dry-run          # 결정론 검증(codex 미호출)
  python scripts/execute.py --task docs/execplan/T4 --no-push --no-pr  # 로컬 실행
  python scripts/execute.py --task docs/execplan/T4 --from step2       # 중단 지점 재개
"""
from __future__ import annotations
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 콘솔 기본 인코딩(cp949)이 한글·이모지를 못 찍으므로 UTF-8 강제
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO / "docs" / "execplan" / "_schemas"
HANDOFF_SCHEMA = SCHEMA_DIR / "handoff.schema.json"
FINDINGS_SCHEMA = SCHEMA_DIR / "findings.schema.json"
RUNS_DIR = REPO / ".exec" / "runs"


def log(msg: str) -> None:
    print(f"[execute] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# front-matter (최소 YAML 서브셋 — 외부 의존 없이 stdlib만)
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# git / shell helpers (CodeAct 레이어 — 토큰 0)
# --------------------------------------------------------------------------- #
def run(cmd, *, shell=False, timeout=None, check=False, capture=True):
    return subprocess.run(
        cmd, cwd=str(REPO), shell=shell, timeout=timeout, check=check,
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


def step_num(p: Path) -> int:
    """stepN → N (자연 정렬용; 코덱스 미검출 + 내 CL-2: step10 사전순 오류 방지)."""
    m = re.search(r"(\d+)", p.stem)
    return int(m.group(1)) if m else 0


def load_prior_summaries(ticket, want_num, current_run_dir, out):
    """--from 재개 시 가장 최근 이전 run에서 want_num 미만 step 요약 복원 (코덱스 P2)."""
    dirs = sorted((d for d in RUNS_DIR.glob(f"{ticket}-*")
                   if d.is_dir() and d != current_run_dir), reverse=True)
    if not dirs:
        log("--from 재개: 이전 run 없음 — 요약 복원 스킵")
        return
    prev = dirs[0]
    for sp in prev.glob("step*.summary.json"):
        name = sp.name.split(".")[0]
        if step_num(Path(name)) >= want_num:
            continue
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append({"step": name, **(data if isinstance(data, dict) else {"summary": data})})
    out.sort(key=lambda d: step_num(Path(d["step"])))
    log(f"--from 재개: {prev.name}에서 요약 {len(out)}건 복원")


# --------------------------------------------------------------------------- #
# codex 이벤트 토큰 집계 (best-effort — 실측으로 스키마 확정 후 정교화)
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# 프롬프트 조립 (task 헤더 + 이전 요약 재주입 + 이번 step)
# --------------------------------------------------------------------------- #
def build_prompt(task_meta, task_body, prior_summaries, step_name, step_body, failure=None):
    guards = task_meta.get("seam_guards") or []
    dont = task_meta.get("dont_touch") or []
    p = [
        "당신은 code 레인 하위 실행자입니다. 아래 경계 안에서 '코드 변경'만 수행하세요.",
        "커밋·push·PR·git·gh 및 최종 검증(verify)은 하네스(execute.py)가 대신 수행합니다.",
        "필요한 읽기/탐색은 자유롭게 하되, 산출물은 '파일 수정'입니다.",
        "",
        f"[티켓] {task_meta.get('ticket', '?')}  (기준 SHA: {task_meta.get('base_sha', '?')})",
        "[목표(task)]",
        task_body or "(없음)",
        f"[지켜야 할 seam guard] {', '.join(guards) if guards else '없음'}",
        f"[건드리지 말 것] {', '.join(dont) if dont else '없음'}",
    ]
    if prior_summaries:
        p += ["", "[이전 step 요약(handoff)]",
              json.dumps(prior_summaries, ensure_ascii=False, indent=2)]
    p += ["", f"[이번 step: {step_name}]", step_body or "(본문 없음)"]
    if failure:
        p += ["", "[직전 시도 verify 실패 — 아래 출력을 보고 원인을 고치세요]",
              failure[-4000:]]
    p += ["", "작업을 마치면 최종 메시지를 제공된 JSON 스키마(handoff)에 맞춰 응답하세요."]
    return "\n".join(p)


# --------------------------------------------------------------------------- #
# codex 호출
# --------------------------------------------------------------------------- #
def find_codex() -> str:
    exe = shutil.which("codex")
    if not exe:
        sys.exit("[execute] codex CLI를 PATH에서 찾을 수 없습니다.")
    return exe


def codex_exec(codex, prompt, summary_path, events_path, timeout):
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
        cmd, cwd=str(REPO), input=prompt, text=True,
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


def codex_review(codex, base, out_path, events_path, timeout):
    cmd = [
        codex, "exec", "review", "--base", base,
        "--output-schema", str(FINDINGS_SCHEMA),
        "-o", str(out_path), "--json",
    ]
    proc = subprocess.run(
        cmd, cwd=str(REPO), text=True, encoding="utf-8", errors="replace",
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


def run_verify(cmd: str, timeout: int):
    if not cmd or not cmd.strip():
        return True, "(verify 없음 — 스킵)"
    r = run(cmd, shell=True, timeout=timeout)
    return r.returncode == 0, (r.stdout or "")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def discover_steps(task_dir: Path, meta: dict) -> list[Path]:
    if meta.get("steps"):
        return [task_dir / s for s in meta["steps"]]
    return sorted(task_dir.glob("step*.md"), key=step_num)


def main():
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
    args = ap.parse_args()

    task_dir = (REPO / args.task).resolve() if not Path(args.task).is_absolute() else Path(args.task)
    task_md = task_dir / "task.md"
    if not task_md.exists():
        sys.exit(f"[execute] {task_md} 없음")
    meta, task_body = read_md(task_md)
    ticket = meta.get("ticket", task_dir.name)
    base = args.base or meta.get("base_branch") or "dev"
    steps = discover_steps(task_dir, meta)
    if not steps:
        sys.exit("[execute] step*.md 를 찾지 못했습니다.")

    if args.from_step:
        want_num = step_num(Path(args.from_step))
        steps = [s for s in steps if step_num(s) >= want_num] or steps

    runid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"{ticket}-{runid}"
    run_dir.mkdir(parents=True, exist_ok=True)
    codex = None if args.dry_run else find_codex()

    # clean 베이스라인 보장 — git add -A가 무관한 워킹트리 변경을 커밋하지 않도록 (코덱스 리뷰 P2)
    if not args.dry_run and not args.no_commit and not args.allow_dirty:
        if git("status", "--porcelain").strip():
            sys.exit("[execute] 워킹트리 dirty — clean 상태에서 실행하거나 --allow-dirty 사용")

    log(f"티켓 {ticket} · steps={[s.name for s in steps]} · base={base} · run={run_dir.name}")

    # 브랜치
    branch = meta.get("branch") or f"feature/{ticket}-exec"
    if not args.no_branch and not args.dry_run:
        exists = branch in git("branch", "--list", branch)
        try:
            git("checkout", branch, check=True) if exists else git("checkout", "-b", branch, base, check=True)
        except RuntimeError as e:
            sys.exit(f"[execute] 브랜치 전환 실패: {e}")
        log(f"브랜치: {current_branch()}")

    state = {"ticket": ticket, "runid": runid, "base": base, "branch": branch, "steps": []}
    prior_summaries = []
    if args.from_step:
        load_prior_summaries(ticket, step_num(Path(args.from_step)), run_dir, prior_summaries)

    for step_path in steps:
        smeta, sbody = read_md(step_path)
        name = step_path.stem
        title = smeta.get("title", name)
        verify_cmd = smeta.get("verify", "")
        summary_path = run_dir / f"{name}.summary.json"
        events_path = run_dir / f"{name}.events.jsonl"
        log(f"── {name}: {title}")

        prompt = build_prompt(meta, task_body, prior_summaries, name, sbody)
        if args.dry_run:
            print(f"\n===== DRY-RUN PROMPT [{name}] =====\n{prompt}\n")
            print(f"codex exec --sandbox workspace-write -c approval_policy=never "
                  f"--output-schema {HANDOFF_SCHEMA.name} -o {summary_path.name} --json -")
            if verify_cmd:
                print(f"verify: {verify_cmd}")
            continue

        # codex + verify + self-repair
        attempts = 1 + max(0, args.self_repair)
        failure = None
        step_rec = {"name": name, "title": title, "status": "failed",
                    "attempts": 0, "tokens": {}, "verify": None, "sha": None}
        for attempt in range(1, attempts + 1):
            step_rec["attempts"] = attempt
            p = prompt if failure is None else build_prompt(
                meta, task_body, prior_summaries, name, sbody, failure=failure)
            log(f"   codex exec (시도 {attempt}/{attempts}) …")
            try:
                rc, summary, tokens = codex_exec(codex, p, summary_path, events_path, args.timeout)
            except subprocess.TimeoutExpired:
                failure = f"codex exec 타임아웃({args.timeout}s)"
                log(f"   ! {failure}")
                break
            step_rec["tokens"] = tokens
            step_rec["codex_rc"] = rc
            if rc != 0:  # 코덱스 P1 = 내 CL-1: codex 실패를 verify 성공이 가리지 못하게
                failure = f"codex exec 비정상 종료(rc={rc}) — {events_path.name} 참조"
                log(f"   ! codex rc={rc} (시도 {attempt}/{attempts})")
                continue
            ok, vout = run_verify(verify_cmd, args.timeout)
            step_rec["verify"] = "pass" if ok else "fail"
            if ok:
                step_rec["status"] = "done"
                step_rec["summary"] = summary
                log(f"   verify={'skip' if not verify_cmd.strip() else 'pass'} "
                    f"· tokens(in/out)={tokens['input']}/{tokens['output']}"
                    f"{'' if tokens['found'] else ' (미검출)'}")
                break
            failure = vout
            log(f"   verify FAIL (시도 {attempt}) — 재시도" if attempt < attempts
                else "   verify FAIL — 재시도 소진")

        # commit
        if step_rec["status"] == "done" and not args.no_commit:
            git("add", "-A")
            if git("status", "--porcelain").strip():
                git("commit", "-m", f"{ticket} {name}: {title}", check=True)
                step_rec["sha"] = short_sha()
                log(f"   commit {step_rec['sha']}")
            else:
                log("   (변경 없음 — 커밋 생략)")

        state["steps"].append(step_rec)
        (run_dir / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        if step_rec["status"] != "done":
            log(f"!! {name} 실패 — run 중단. 재개: --from {name}")
            _finish(state, run_dir, halted=True)
            return

        if step_rec.get("summary"):
            prior_summaries.append({"step": name, **(step_rec["summary"] if isinstance(
                step_rec["summary"], dict) else {"summary": step_rec["summary"]})})

    if args.dry_run:
        log("dry-run 완료 (codex/git 미실행)")
        return

    # push / PR (CodeAct — 토큰 0)
    if not args.no_push:
        try:
            git("push", "-u", "origin", branch, check=True)
            log(f"push → origin/{branch}")
        except RuntimeError as e:
            log(f"!! push 실패 — PR 생략: {e}")
            _finish(state, run_dir, halted=True)
            return
    if not args.no_pr:
        body = _pr_body(state, prior_summaries)
        r = run(["gh", "pr", "create", "--base", base, "--head", branch,
                 "--title", f"{ticket}: {meta.get('title', branch)}", "--body", body])
        log(f"gh pr create: {(r.stdout or '').strip()[:200]}")

    # 교차 리뷰 (AI — 토큰 O)
    if not args.no_review:
        log("codex exec review (교차 리뷰) …")
        try:
            rc, findings, rtok = codex_review(
                codex, base, run_dir / "codex_review.json",
                run_dir / "review.events.jsonl", args.timeout)
            state["review"] = {"tokens": rtok,
                               "findings_count": len(findings.get("findings", []))
                               if isinstance(findings, dict) else None}
            log(f"   review tokens(in/out)={rtok['input']}/{rtok['output']} "
                f"· findings={state['review']['findings_count']}")
        except subprocess.TimeoutExpired:
            log("   ! review 타임아웃")

    _finish(state, run_dir, halted=False)


def _pr_body(state, summaries) -> str:
    lines = [f"자동 실행: `execute.py` (티켓 {state['ticket']}, run {state['runid']})", ""]
    for s in state["steps"]:
        lines.append(f"- **{s['name']}** {s['title']} — {s['status']} (verify={s['verify']}, "
                     f"sha={s['sha']}, tokens in/out={s['tokens'].get('input')}/{s['tokens'].get('output')})")
    lines += ["", "> 교차 리뷰(codex exec review) 결과는 run 산출물 `codex_review.json` 참조.",
              "> 클로드가 diff + codex findings를 대조해 최종 판정합니다.", "",
              "🤖 Generated with [Claude Code](https://claude.com/claude-code)"]
    return "\n".join(lines)


def _finish(state, run_dir, halted):
    (run_dir / "report.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    ai_in = sum(s["tokens"].get("input", 0) for s in state["steps"])
    ai_out = sum(s["tokens"].get("output", 0) for s in state["steps"])
    log("=" * 56)
    log(f"RUN {'중단' if halted else '완료'} · {state['ticket']} · steps done="
        f"{sum(1 for s in state['steps'] if s['status'] == 'done')}/{len(state['steps'])}")
    log(f"AI 토큰 합계 in/out = {ai_in}/{ai_out}  (CodeAct 레이어=git/gh/verify=0)")
    log(f"산출물: {run_dir}")


if __name__ == "__main__":
    main()
