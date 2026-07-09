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
- 내용: ADR-0005 · `docs/execplan/`(README·_schemas·T4 파일럿) · `scripts/execute.py`(481줄) 등 728줄 흡수. merge-base가 직전 dev tip(`aad8ace`)이라 무충돌.
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
- 교차 리뷰: codex 서브에이전트 위임 — findings는 아래 메모로만 기록(즉시 수정 금지, 사용자 판정 대기 · SPEC §4.7).

## [교차 리뷰 메모] (미수정 — 사용자 판정 대기)

> step5 리뷰 완료 후 기재.
