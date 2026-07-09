# Architecture Decision Records (ADR)

설계·아키텍처 결정을 **결정 단위로** 기록한다 (MADR 경량 포맷). 역할 분리(ADR-0006):

- 결정의 **"왜"** → 여기(ADR)
- 단일 진입 정본(헌법·프로토콜·컨벤션) → `docs/SPEC.md` (`CLAUDE.md`는 라우터)
- 제품 방향성 → `docs/PRD.md`
- 보드(seam registry·티켓 정의·status·step) → `docs/MAINTENANCE.md`
- 다단계 실행 스펙·step 실행 요약 → `docs/execplan/`
- GitHub Issues → 미러/알림(정본은 리포 문서)

## 규칙
- 파일명 `NNNN-title.md` (4자리 일련번호).
- 상태: `Proposed` / `Accepted` / `Superseded (→ ADR-XXXX)`.
- **새 결정은 새 파일**로 추가. 기존 ADR은 재작성하지 않고, 뒤집을 땐 새 ADR을 쓰고 옛 것을 `Superseded`로 표시.

## 목록
- [0001](0001-maintenance-harness.md) — 유지보수 하네스 도입
- [0002](0002-doc-architecture.md) — 유지보수 문서 아키텍처 *(Superseded → 0006)*
- [0003](0003-ops-execution-lane.md) — 운영(ops) 티켓 실행 레인
- [0004](0004-harness-admission-gate.md) — 하네스 admission gate(intake·DoD·sweep)
- [0005](0005-codex-exec-orchestration.md) — codex exec 다단계 실행기(execute.py)
- [0006](0006-doc-governance-spec.md) — 문서 거버넌스 재편(SPEC 단일 진입·docs main 직행)
- [0007](0007-llm-transport-layer.md) — LLM 통신 계층(포트/어댑터·스택 통일·Langfuse)
