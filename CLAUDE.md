# TailorPlay 재활성화 작업 가이드 (CLAUDE.md)

Steam 게임 추천시스템(FastAPI + pgvector + Redis + BentoML + React, 부스트캠프 2026년 1~2월 프로젝트)을 되살리는 작업 중이다. 이 파일이 **진행 상태의 단일 진실 소스**다 — 작업 시작 시 여기서 현재 상태를 파악하고, 단계가 완료되면 아래 체크리스트를 갱신할 것.

## 작업 규칙

- 재활성화 작업은 전부 `revive/reactivation` 브랜치에서 진행 (main은 최신 안정 상태).
- 계획/조사 문서는 `docs/reactivation/` 아래에만 작성. 마스터 플랜: `docs/reactivation/PLAN.md`.
- 루트 `README.md`의 프로젝트 구조도는 **구식이라 신뢰 금지** — 실제 트리는 `ml_rec/scripts/{preprocessing,stage1_retrieval,stage2_ranking,stage3_scoring,stage4_serving}` 기준 (상세: PLAN.md §3 버그 #5).
- `ml_rec/scripts/stage4_serving/model_loader.py`의 후보 JSON 로드 스킵을 되돌리지 말 것 (12GB 서버에서 OOM — PLAN.md §5).
- 데이터/모델 아티팩트(`*.pkl`, `*.inter`, `*.jsonl` 등)는 gitignore 대상 — 커밋 금지.

## 핵심 전제 (2026-07-06 실측)

- GCS `data-tailor-test`: 결제계정 closed로 **다운로드 403** (리스팅은 됨 = 데이터 미삭제). 복구는 결제 재연결 대기 중.
- CLOVA: 키는 살아있으나 지원 종료 → **Gemini(OpenAI 호환 엔드포인트)로 교체** 예정. 임베딩은 로컬 bge-m3 유지 (교체 금지 — 1024차원 정합).
- 배포 서버: GCP 사망 → **Oracle A1.Flex Always Free (2 OCPU / 12GB, 2026-06-15 축소됨)** 이전. ARM이라 buildx 멀티아치 빌드 필수.
- 이 노트북 Docker: `rec-server:latest` 이미지(데이터 없음), `postgres_data` 볼륨(과거 DB, 복구 후보) 생존.

## 진행 상태

### Phase 0 — 데이터 확보 ✅ 완료 (2026-07-06)
- [x] GCP 결제계정 재연결 (사용자)
- [x] GCS 전체 백업: 32개 7.82GB, 실패 0 → `C:\Users\rlaqu\Documents\recsys05_gcs_backup`
- [x] Gdrive 복사: `G:\내 드라이브\부스트캠프\backup\gcs_data-tailor-test` (robocopy 32/32, FAILED 0)
- [x] `item_similarity.pkl` 포맷 확인 → **RecBole EASE 체크포인트로 확정** (버그 #3 실재 — `other_parameter.item_similarity` dense 17,792×17,792 + `interaction_matrix` csr 97,870×17,792. 백엔드용 dict 변환 스크립트 필요, token 맵은 `steam_optimal` dataset 재로드로 추출)
- ~~메인컴퓨터/팀원 수색~~ (GCS 확보로 불필요해짐)
- [ ] (선택) `postgres_data` 볼륨 pg_dump — games 테이블 임베딩이 살아있으면 재적재 시간 절약

### Phase 1 — 로컬 재기동
- [ ] GCS 키 경로 통일 (버그 #1, #2 — PLAN.md §3)
- [ ] 데이터 배치 → `docker compose up` → 헬스체크/벡터검색 검증
- [ ] `item_similarity.pkl` 포맷 확인, 필요 시 변환 스크립트 작성 (버그 #3)

### Phase 2 — LLM 교체 (CLOVA → Gemini)
- [ ] Gemini 키 발급, env 교체 (`base_url`, 모델명)
- [ ] `providers/clova.py` extra_body → 표준 파라미터화, 모델명 하드코딩 7곳 env 통일 (버그 #7)
- [ ] 리랭커 비활성화 확인, chat 테스트 통과

### Phase 3 — 재배포 (Oracle A1.Flex 12GB)
- [ ] 인스턴스 프로비저닝 (Ubuntu ARM + Docker + Tailscale + 스왑 8GB)
- [ ] buildx 멀티아치 빌드 전환, frontend CI 누락 수정 (버그 #4)
- [ ] GitHub secrets 17개 재설정 (목록: PLAN.md 부록 A) → 배포 → 헬스체크

## 로컬 개발 참고

- 백엔드 의존성: `cd backend && uv sync` (Python 3.11, `backend/.venv` 존재)
- 로컬 구동: `docker compose up` (base + override 자동 병합), 헬스체크 `http://localhost:8000/health/db`
- 테스트: `cd backend && uv run pytest test/` (DB/Redis 필요 — compose로 먼저 기동)
