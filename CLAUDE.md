# TailorPlay — CLAUDE.md (라우터)

Steam 게임 추천시스템 (FastAPI + pgvector + Redis + BentoML 3-stage + React · Oracle A1 + Vercel). 부스트캠프 2026-01~02 프로젝트, **현재 유지보수 모드**.

**단일 진입 정본 = `docs/SPEC.md`** (ADR-0006). 매 세션: SPEC §1(불변식) 준수 → SPEC §4(조사→분석→실행 프로토콜)로 진행 → 티켓·seam·step은 `docs/MAINTENANCE.md`(보드).

## 불변식 요약 (정본: SPEC §1 — 충돌 시 SPEC이 우선)

1. **EASE 폴백 항상 유지** — backend가 bentoml에 hard-depend 금지 (seam S3).
2. `ml_rec/scripts/stage4_serving/model_loader.py`의 **후보 JSON 로드 스킵 되돌리기 금지** (12GB OOM · seam S2).
3. **임베딩 bge-m3(1024차원) 교체 금지** (seam S6).
4. 배포 이미지는 ARM — **buildx arm64 필수**.
5. **seam 변경은 한 커밋으로** (MAINTENANCE §1).
6. 데이터/모델 아티팩트(`*.pkl`·`*.inter`·`*.jsonl` 등) **커밋 금지**.
7. **LLM 호출은 통신 계층 어댑터만 경유** (ADR-0007 · T18).
8. **모든 티켓 DoD에 테스트 포함** (test-with · 버그는 실패 재현 선작성).
9. **`docs/**` 정본은 main** (ADR-0006).

## 문서 지도 (ADR-0006)

| 문서 | 역할 |
|---|---|
| `docs/SPEC.md` | **단일 진입 정본** — 헌법·5축 지도·프로토콜·컨벤션·테스트 규칙·로드맵 |
| `docs/MAINTENANCE.md` | 보드 — seam registry · 티켓 백로그(status 정본) · step 보드 · 운영 참조 |
| `docs/adr/` | 설계 결정의 "왜" |
| `docs/execplan/` | 다단계 실행 스펙 + step별 실행 요약(인계 정본) |
| `docs/PRD.md` | 제품 방향 |
| GitHub Issues | 미러/알림 (정본은 리포 문서) |
| `docs/reactivation/` | reactivation 기록 — `REACTIVATION_LOG.md`(구 CLAUDE.md 로그)·`HANDOFF.md`·`BENTOML_VERIFY.md` |

## 브랜치·거버넌스

- **코드**: `feature → dev → main` (main 직행 금지, dev 스테이징).
- **문서(`docs/**`)**: main 직행 커밋 허용 (ADR-0006 — T14가 main에 도달한 후 발효).

## 로컬 개발 참고

- 백엔드 의존성: `cd backend && uv sync` (Python 3.11, `backend/.venv`)
- 로컬 구동: `docker compose up -d db redis` → `docker compose up -d --build --no-deps backend` (backend가 bentoml healthy에 의존 → `--no-deps` 필수). 헬스체크 `http://localhost:8000/health/db`
- 테스트: `cd backend && uv run pytest test/` (DB/Redis 필요 — compose 먼저)
- 루트 `README.md` 구조도는 구식 — 신뢰 금지 (T4·T15에서 재작성 예정)
- reactivation 상세(데이터 위치·서버 이력·검증 로그) = `docs/reactivation/REACTIVATION_LOG.md`
