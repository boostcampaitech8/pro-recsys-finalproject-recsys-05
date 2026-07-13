"""Main execution loop for the execute harness."""
from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path

from .codex import codex_exec, codex_review, find_codex
from .gates import run_verify
from .paths import HANDOFF_SCHEMA, REPO, RUNS_DIR
from .procio import current_branch, git, run as run_process, short_sha
from .specs import discover_steps, read_md, step_num


def log(msg: str) -> None:
    print(f"[execute] {msg}", flush=True)


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


def run(args) -> int:
    task_dir = (REPO / args.task).resolve() if not Path(args.task).is_absolute() else Path(args.task)
    task_md = task_dir / "task.md"
    if not task_md.exists():
        log(f"{task_md} 없음")
        return 1
    try:
        meta, task_body = read_md(task_md)
    except OSError as e:
        log(f"task 파일 읽기 실패: {e}")
        return 1
    ticket = meta.get("ticket", task_dir.name)
    base = args.base or meta.get("base_branch") or "dev"
    steps = discover_steps(task_dir, meta)
    if not steps:
        log("step*.md 를 찾지 못했습니다.")
        return 1

    if args.from_step:
        matches = [
            index for index, step in enumerate(steps)
            if args.from_step in (step.stem, step.name)
        ]
        if not matches:
            log(f"--from {args.from_step!r}와 일치하는 step이 없습니다.")
            log(f"사용 가능한 step: {', '.join(step.stem for step in steps)}")
            return 2
        steps = steps[matches[0]:]

    step_inputs = []
    for step_path in steps:
        if not step_path.is_file():
            log(f"step 파일 없음: {step_path}")
            return 1
        try:
            smeta, sbody = read_md(step_path)
        except OSError as e:
            log(f"step 파일 읽기 실패({step_path.name}): {e}")
            return 1
        verify_cmd = smeta.get("verify", "")
        if not isinstance(verify_cmd, str) or not verify_cmd.strip():
            log(
                f"{step_path.name} verify 필수 — 빈 값은 허용되지 않습니다. "
                "스킵은 verify: skip으로 명시하세요."
            )
            return 1
        step_inputs.append((step_path, smeta, sbody, verify_cmd))

    runid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"{ticket}-{runid}"
    run_dir.mkdir(parents=True, exist_ok=True)
    codex = None if args.dry_run else find_codex()

    # clean 베이스라인 보장 — git add -A가 무관한 워킹트리 변경을 커밋하지 않도록 (코덱스 리뷰 P2)
    if not args.dry_run and not args.no_commit and not args.allow_dirty:
        try:
            dirty = git("status", "--porcelain", check=True).strip()
        except RuntimeError as e:
            log(f"git 상태 확인 실패: {e}")
            return 1
        if dirty:
            log("워킹트리 dirty — clean 상태에서 실행하거나 --allow-dirty 사용")
            return 1

    log(f"티켓 {ticket} · steps={[s.name for s in steps]} · base={base} · run={run_dir.name}")

    # 브랜치
    branch = meta.get("branch") or f"feature/{ticket}-exec"
    if not args.no_branch and not args.dry_run:
        try:
            exists = branch in git("branch", "--list", branch, check=True)
            git("checkout", branch, check=True) if exists else git("checkout", "-b", branch, base, check=True)
            active_branch = current_branch()
        except RuntimeError as e:
            log(f"브랜치 전환 실패: {e}")
            return 1
        log(f"브랜치: {active_branch}")

    state = {"ticket": ticket, "runid": runid, "base": base, "branch": branch, "steps": []}
    prior_summaries = []
    if args.from_step:
        load_prior_summaries(ticket, step_num(Path(args.from_step)), run_dir, prior_summaries)

    for step_path, smeta, sbody, verify_cmd in step_inputs:
        name = step_path.stem
        title = smeta.get("title", name)
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
                rc, summary, tokens = codex_exec(
                    codex, p, summary_path, events_path, args.timeout, cwd=REPO)
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
                log(f"   verify={'skip' if verify_cmd.strip().lower() == 'skip' else 'pass'} "
                    f"· tokens(in/out)={tokens['input']}/{tokens['output']}"
                    f"{'' if tokens['found'] else ' (미검출)'}")
                break
            failure = vout
            log(f"   verify FAIL (시도 {attempt}) — 재시도" if attempt < attempts
                else "   verify FAIL — 재시도 소진")

        # commit
        if step_rec["status"] == "done" and not args.no_commit:
            try:
                git("add", "-A", check=True)
                if git("status", "--porcelain", check=True).strip():
                    git("commit", "-m", f"{ticket} {name}: {title}", check=True)
                    step_rec["sha"] = short_sha()
                    log(f"   commit {step_rec['sha']}")
                else:
                    log("   (변경 없음 — 커밋 생략)")
            except RuntimeError as e:
                step_rec["status"] = "failed"
                step_rec["error"] = f"git commit 경로 실패: {e}"
                log(f"   ! {step_rec['error']}")

        state["steps"].append(step_rec)
        (run_dir / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        if step_rec["status"] != "done":
            log(f"!! {name} 실패 — run 중단. 재개: --from {name}")
            return _finish(state, run_dir, halted=True)

        if step_rec.get("summary"):
            prior_summaries.append({"step": name, **(step_rec["summary"] if isinstance(
                step_rec["summary"], dict) else {"summary": step_rec["summary"]})})

    if args.dry_run:
        log("dry-run 완료 (codex/git 미실행)")
        return 0

    # push / PR (CodeAct — 토큰 0)
    if not args.no_push:
        try:
            git("push", "-u", "origin", branch, check=True)
            log(f"push → origin/{branch}")
        except RuntimeError as e:
            log(f"!! push 실패 — PR 생략: {e}")
            return _finish(state, run_dir, halted=True)
    if not args.no_pr:
        body = _pr_body(state, prior_summaries)
        r = run_process(["gh", "pr", "create", "--base", base, "--head", branch,
                         "--title", f"{ticket}: {meta.get('title', branch)}", "--body", body])
        log(f"gh pr create: {(r.stdout or '').strip()[:200]}")
        if r.returncode != 0:
            log(f"!! gh pr create 실패(rc={r.returncode})")
            return _finish(state, run_dir, halted=True)

    # 교차 리뷰 (AI — 토큰 O)
    if not args.no_review:
        log("codex exec review (교차 리뷰) …")
        try:
            rc, findings, rtok = codex_review(
                codex, base, run_dir / "codex_review.json",
                run_dir / "review.events.jsonl", args.timeout, cwd=REPO)
            state["review"] = {"tokens": rtok,
                               "findings_count": len(findings.get("findings", []))
                               if isinstance(findings, dict) else None}
            log(f"   review tokens(in/out)={rtok['input']}/{rtok['output']} "
                f"· findings={state['review']['findings_count']}")
        except subprocess.TimeoutExpired:
            log("   ! review 타임아웃")

    return _finish(state, run_dir, halted=False)


def _pr_body(state, summaries) -> str:
    lines = [f"자동 실행: `execute.py` (티켓 {state['ticket']}, run {state['runid']})", ""]
    for s in state["steps"]:
        lines.append(f"- **{s['name']}** {s['title']} — {s['status']} (verify={s['verify']}, "
                     f"sha={s['sha']}, tokens in/out={s['tokens'].get('input')}/{s['tokens'].get('output')})")
    lines += ["", "> 교차 리뷰(codex exec review) 결과는 run 산출물 `codex_review.json` 참조.",
              "> 클로드가 diff + codex findings를 대조해 최종 판정합니다.", "",
              "🤖 Generated with [Claude Code](https://claude.com/claude-code)"]
    return "\n".join(lines)


def _finish(state, run_dir, halted) -> int:
    (run_dir / "report.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    ai_in = sum(s["tokens"].get("input", 0) for s in state["steps"])
    ai_out = sum(s["tokens"].get("output", 0) for s in state["steps"])
    log("=" * 56)
    log(f"RUN {'중단' if halted else '완료'} · {state['ticket']} · steps done="
        f"{sum(1 for s in state['steps'] if s['status'] == 'done')}/{len(state['steps'])}")
    log(f"AI 토큰 합계 in/out = {ai_in}/{ai_out}  (CodeAct 레이어=git/gh/verify=0)")
    log(f"산출물: {run_dir}")
    return 1 if halted else 0
