# ADR-0006 · 문서 거버넌스 재편 — SPEC 단일 진입 + docs main 직행

- **상태**: Accepted (2026-07-09)
- **맥락**: ADR-0002는 라이브 상태를 Issues로 빼고 문서는 `feature→dev→main`으로 승격하게 했다. 실제 운영 결과 **거버넌스 문서가 브랜치에 고였다** — main은 T11·ADR-0004에서 정지, T12는 dev에만, T13·ADR-0005·`docs/execplan/`은 feature 브랜치에만 존재. 닫힌/열린 Issue(#104·#107)가 가리키는 문서가 main에서 404가 났다. 진입 문서도 `CLAUDE.md`(헌법)+`MAINTENANCE.md`(SSOT) 이중 구조라 "연결을 따라가면 일이 진행되는" 상태가 아니었다.

## 결정

1. **`docs/**`의 정본은 main.** `docs/**` 변경은 **main 직행 커밋 허용** — 코드 승격 경로(`feature→dev→main`)의 명시적 예외. 거버넌스 문서가 브랜치에 고이는 구조적 원인을 제거한다.
2. **Issues는 미러/알림으로 강등.** main 직행으로 문서의 브랜치 충돌 원인이 사라지므로, ADR-0002가 Issues로 뺐던 **티켓 status 정본을 리포 문서(MAINTENANCE §3)로 되돌린다.** Issue는 알림·토론·감사추적(검증 로그 코멘트)용.
3. **단일 진입 = `docs/SPEC.md` 신설.** 헌법(불변식 9)·5축 지도·작업 프로토콜(조사→분석→실행)·컨벤션·테스트 규칙·로드맵을 한 문서로. `CLAUDE.md`는 라우터로 축소(reactivation 로그는 `docs/reactivation/REACTIVATION_LOG.md`로 이관), `MAINTENANCE.md`는 보드(seam registry·티켓·step)로 축소.
4. **발효 시점**: 본 ADR·SPEC이 main에 도달한 뒤부터. 부트스트랩(T14) 자체는 구 규칙으로 승격한다 — 새 규칙으로 새 규칙을 도입하는 순환을 피한다.

## 결과

- **ADR-0002를 Supersede** (문서 역할·status 정본 재정의).
- 문서 지도: SPEC(정본 규칙) / MAINTENANCE(보드) / adr(왜) / execplan(다단계 실행·step 요약) / PRD(제품) / Issues(미러) / reactivation(기록).
- **트레이드오프**: docs main 직행은 리뷰 없는 커밋을 허용한다 — 코드가 아닌 `docs/**` 한정으로 리스크를 수용하고, 코드 승격 경로는 불변. 문서 정합 책임은 세션 sweep(SPEC §4.8)이 진다.
- 이행 = T14 (Issue #110), 실행 기록 = `docs/execplan/T14/`.
