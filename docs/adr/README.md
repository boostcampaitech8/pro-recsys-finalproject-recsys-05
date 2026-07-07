# Architecture Decision Records (ADR)

설계·아키텍처 결정을 **결정 단위로** 기록한다 (MADR 경량 포맷). 역할 분리:

- 결정의 **"왜"** → 여기(ADR)
- AI 세션 불변식·진입점 → `CLAUDE.md` (헌법)
- 제품 방향성 → `docs/PRD.md`
- 유지보수 구조·티켓 정의 → `docs/MAINTENANCE.md`
- 라이브 진행상태(status·현재 step) → GitHub Issues/Projects

## 규칙
- 파일명 `NNNN-title.md` (4자리 일련번호).
- 상태: `Proposed` / `Accepted` / `Superseded (→ ADR-XXXX)`.
- **새 결정은 새 파일**로 추가. 기존 ADR은 재작성하지 않고, 뒤집을 땐 새 ADR을 쓰고 옛 것을 `Superseded`로 표시.

## 목록
- [0001](0001-maintenance-harness.md) — 유지보수 하네스 도입
- [0002](0002-doc-architecture.md) — 유지보수 문서 아키텍처
