---
ticket: T14
issue: 110
title: "docs(governance): SPEC 단일 진입 신설 + 문서 거버넌스 재편 (T14 · ADR-0006/0007)"
base_branch: dev
branch: feature/spec-governance
executor: claude-session   # execute.py 아님 — 세션 컨텍스트(결정 D1~D7) 필요한 문서 작업이라 클로드 직접 실행
---

# T14 · 문서 거버넌스 개편 — 실행 기록 (execplan)

배경: 2026-07-09 SPEC 재설계 인터뷰로 결정 7개(D1~D7) + 수정 3(부트스트랩·인계 요약·execplan step 요약) 확정. 이 문서가 **인계 정본**(SPEC §4.6 — 다단계·ADR 동반 트랙): step별 `[실행 요약]`을 실행 주체가 작성한다.

## step1 · dev 역병합 (diverged 해소)

**[실행 요약]**
- 커밋: `3a0f6ef` (origin/dev push 완료)
- 내용: main↔dev diverged(3↔4) 해소. main에만 있던 3커밋은 전부 dev→main 병합커밋(PR #85·#98·#103)이라 `git diff HEAD^1 HEAD` 공집합 — **내용 변화 0, 히스토리 연결만**.
- 다음 step에 주는 것: dev가 main을 포함 → 여기서 분기하면 승격 경로 깨끗.

## step2 · feature/spec-governance 분기 + T13 트랙 흡수

**[실행 요약]**
- 커밋: `82124a6` (merge `origin/feature/T13-execute-py`)
- 내용: ADR-0005 · `docs/execplan/`(README·_schemas·T4 파일럿) · `scripts/execute.py`(481줄) 등 728줄 흡수. merge-base가 `aad8ace`(step1 역병합 이전의 dev tip)라 무충돌.
- 다음 step에 주는 것: execplan 레이아웃이 리포에 존재 → T14 execplan(이 문서)이 그 구조를 따름. T13 잔여 검증(T4 파일럿)은 T13에 남음.

## step3 · 문서 개편 (SPEC·라우터·보드·ADR)

**[실행 요약]**
- 신설: `docs/SPEC.md`(§1 헌법 9불변식 · §2 5축 지도 · §3 아키텍처 규칙 · §4 조사→분석→실행 프로토콜〔intake·레인·DoD·인계 요약·교차 리뷰·sweep·자율 경계 흡수〕 · §5 컨벤션 · §6 테스트 규칙 · §7 로드맵), `docs/adr/0006`(문서 거버넌스 — ADR-0002 Supersede), `docs/adr/0007`(LLM 통신 계층 결정), `docs/reactivation/REACTIVATION_LOG.md`(구 CLAUDE.md 로그 이관).
- 개편: `CLAUDE.md` → 라우터(불변식 요약+문서 지도+로컬 참고만), `docs/MAINTENANCE.md` → 보드(§1 seam · §2 티켓 서식 · §3 백로그〔status 정본으로 승격〕 · §4 step 보드〔정본으로 승격〕 · 부록).
- 유의: "docs main 직행"은 T14가 main 도달 후 발효 — 이 PR 자체는 구 규칙(feature→dev→main).

## step4 · 티켓 등록 (§3 + Issues)

**[실행 요약]**
- Issues 생성: **T13 #109(소급 — sweep 갭 해소)** · T14 #110 · T15 #111 · T16 #112 · T17 #113 · T18 #114 · T19 #115 · T20 #116 · T21 #117. 라벨 신설: `step:H`·`step:5`~`step:8`.
- MAINTENANCE §3에 정의 등록(T14~T21) + §4 step 보드 5·6·7·8 행 추가. 의존: T18←T16, T19←T18, T20←T17, T21 후속.

## step5 · PR → dev + 교차 리뷰

**[실행 요약]**
- PR: #118 (feature/spec-governance → dev). 이후 dev → main 승격 PR로 발효.
- 교차 리뷰: codex 헤드리스(task-mrd7l7cw-2xqnnm, 2026-07-09) 완료 — findings 7건(high 0 · med 4 · low 3), 아래 메모로 기록(SPEC §4.7). 클로드 셀프 체크가 F1을 독립 재현(교차 확인됨). **2026-07-09 사용자 판정 → 7건 전부 반영**(아래 메모 헤더 참조).

## [교차 리뷰 메모] (판정 완료 — 2026-07-09 사용자 승인 → 7건 전부 반영)

**판정(SPEC §4.7)**: 사용자가 2026-07-09 F1~F7 **전부 반영** 승인. 아래 "수정 후보"대로 이 커밋에서 일괄 적용됨 — F5(SPEC §4.4 규칙 복원)·F1(ADR-0003/0004 상태줄 주석)·F4·F3(execplan README 참조)·F6(ADR-0005 정련 주석+README:68+schema)·F2(T4 task 참조)·F7(문구). ADR 본문은 불변, 상태줄 주석만 추가.

codex verdict: *"high 블로커 없음, 단 med 4건은 T14 거버넌스 취지를 흔들므로 병합 전 수정 권고."* 클로드 판정 병기:

| # | sev | 위치 | 발견 | 클로드 판정 | 수정 후보 |
|---|---|---|---|---|---|
| F1 | med | `docs/adr/0003:12,16`·`0004:21` | Accepted ADR들이 사라진 `MAINTENANCE §0`(및 구 §2 seam)을 참조 | **CONFIRMED** (셀프 체크로 독립 재현). 단 "ADR 본문 재작성 금지" 원칙과 충돌 | 본문 불변 + 상태줄에 1줄 주석 "(구 §0/§2 → 현행 SPEC §4 · MAINTENANCE §1, ADR-0006)" |
| F2 | low | `docs/execplan/T4/task.md:24` | 컴포넌트 지도를 `MAINTENANCE §1`로 지시(현행 §1=seam, 지도=SPEC §2) | CONFIRMED | 참조 1줄 교체 |
| F3 | low | `docs/execplan/README.md:38` | `seam_guards`가 "seam(§2)" 지시(현행 seam=§1) | CONFIRMED | 참조 교체 |
| F4 | med | `docs/execplan/README.md:32` | `issue` 키 설명이 "GitHub Issue 번호 (live status)" — ADR-0006(status 정본=MAINTENANCE §3)과 모순 | CONFIRMED | "(미러 — status 정본=MAINTENANCE §3)"로 교체 |
| F5 | med | `docs/SPEC.md` §4.4 | 구 §0의 "ops 작업 중 코드 수정 필요 → code 서브티켓 분리" 규칙이 이관에서 누락(내용 손실) | **CONFIRMED — 실질 손실, 우선 수정 권고** | §4.4 ops 레인에 1줄 복원 |
| F6 | med | `docs/adr/0005:39`·`execplan/README.md:68`·`findings.schema.json:4` | ADR-0005 fix-forward 서술이 SPEC §4.7(메모·사용자 판정)과 충돌 | 부분 완화됨(SPEC §4.7에 한정 조항 기작성). ADR 본문 잔존 서술은 CONFIRMED drift | ADR-0005 상태줄 주석 + README:68·schema description 문구 정합화 |
| F7 | low | `docs/execplan/T14/task.md:25` | "merge-base가 직전 dev tip(aad8ace)" 표현 — step1 이후 dev tip은 3a0f6ef라 모호 | PLAUSIBLE(표현 문제 — aad8ace는 step1 역병합 *이전*의 dev tip. 내용상 참, 문구 모호) | "(step1 이전 dev tip)"으로 명확화 |

처리 방침: 사용자 판정 후 반영. F5(내용 손실) > F1·F4·F6(정합 drift) > F2·F3·F7(참조/문구) 순 권고. → **2026-07-09 전건 반영 완료(사용자 승인)**, 이후 PR #118 dev 병합.
