# ADR-0004 · 하네스 admission gate — intake·확장 DoD·세션 sweep

- **상태**: Accepted (2026-07-08)
- **맥락**: T9(Gemini 유료키 폴백, Issue #96)가 GitHub Issue·PR·코드로만 존재하고 `MAINTENANCE.md` §3 durable 정의가 없는 갭이 발생. 개별 실수가 아니라 워크플로 결함의 증상이다:
  1. CLAUDE.md 진입점이 **수동 포인터** — 실행 전 §0 통과가 강제되지 않음.
  2. §0 ritual이 **"기존 티켓 선택"형** — 세션 중 생긴 신규 작업의 조사→step→티켓화 경로 부재.
  3. `done` 게이트가 **작업 완료만** 검사(등록·seam·ADR 미검사).
  4. ADR-0002의 durable(MAINTENANCE)↔live(Issues) **분리에 정합(reconcile) 장치 없음** — 이중기록 drift.
  5. ops 레인(ADR-0003)의 실행 가속이 bookkeeping 생략 확률을 높임.

## 결정
1. **CLAUDE.md 진입점 = admission gate(관문)** — non-trivial 유지보수 작업은 **실행 전** §0 intake를 통과해야 한다(수동 포인터 → 전제조건).
2. **threshold(과관료화 방지)**:
   - 관문 필수 = 코드/인프라/prod 변경 · seam 접촉 · 2개 이상 컴포넌트 횡단.
   - 인라인 허용(로그만) = 읽기전용 조사 · 문서 오타 · 단일파일 자명 수정.
3. **intake (front door)** — 신규 작업 진입 시 **MAINTENANCE §3 정의 + GitHub Issue를 동시 생성**, 그 자리에서 `kind`(code/ops) · 걸린 seam · **step 배치(기존 편입 또는 신규 개설)** · **ADR 필요성**을 판정. 다 채워야 `scoped`.
4. **확장 DoD (back door)** — `done` = 작업 검증 **+ §3 상태 갱신 + 걸린 seam registry 갱신 + Issue close + ADR 판단 완료** (5종).
5. **세션 종료 sweep (안전망)** — 세션에서 건드린 모든 Issue ↔ §3 정의가 **1:1** 인지 확인. intake를 놓쳐도 여기서 drift 검출.

## 결과
- 상세 절차 = `docs/MAINTENANCE.md` §0(진입 ritual·intake·확장 DoD·sweep). `CLAUDE.md` 진입점이 관문으로 강화됨.
- ADR-0001(하네스)·0003(ops 레인)을 **보완**(대체 아님) — front door·back door·sweep의 3중 정합.
- **트레이드오프**: intake 5항목·sweep 1회의 오버헤드가 늘지만, durable↔live drift(T9류)와 seam·ADR 누락이 구조적으로 차단된다. threshold로 자명 작업은 인라인 유지해 ops 속도 보존.
- **첫 적용**: T9 §3 done 정의 소급 등록 + seam S7 갱신(무료·유료 2 클라이언트), 그리고 이 결정 자체(T10 · Issue #99)를 새 intake(front door)로 처리해 규칙 작동을 시연.
