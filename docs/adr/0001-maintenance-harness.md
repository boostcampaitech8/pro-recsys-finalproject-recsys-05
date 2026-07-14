# ADR-0001 · 유지보수 하네스 도입

- **상태**: Accepted (2026-07-07)
- **맥락**: reactivation Phase 0~4 + backend-refactoring A/B/C 완료. 남은 유지보수를 안전·반복적으로 처리하고, 구현을 codex에 신뢰성 있게 위임하려면 재사용 가능한 체계가 필요하다. 일회성 처리가 아니라 상시 운영 틀을 목표로 한다.

## 결정
1. **컴포넌트 택소노미 2계층** — L1 배포 컴포넌트(frontend / backend / ai-recsys / ci-cd) × L2 backend 코드 도메인(chat〔=AI orchestration〕/ recommendation / game / steam / user). orchestration은 별도 배포단위가 아니라 backend/chat 하위.
2. **risk = seam 우선** — 컴포넌트 경계를 넘는 seam을 1급 항목으로 관리(guard·걸친 컴포넌트·재발 사례). registry S1~S7.
3. **실행 = codex 위임 기본** — `codex:codex-rescue`에 bounded task로 위임, 클로드가 diff 리뷰·커밋.
4. **경량 lifecycle + 조사 게이트** — 티켓 `open→scoped→doing→done`(+`blocked`). `scoped`(조사·요약 완료) 전엔 위임 금지. 조사 주체는 하이브리드(작은 건 클로드 인라인, 큰 건 Explore/codex 진단). 위임 시 자기완결 `[위임 요약]` 블록 전달.
5. **step = 크로스컴포넌트 마일스톤** — 같은 seam이 걸린 티켓을 한 step으로 묶어 "나눴을 때의 risk"를 완화. 순서는 risk·severity 우선.

## 결과
- 상세 구조·프로토콜·티켓은 `docs/MAINTENANCE.md`.
- 라이브 진행상태는 GitHub Issues(→ ADR-0002).
- **트레이드오프**: 조사·위임 오버헤드가 늘지만, seam 사고와 위임 drift가 줄어든다.
