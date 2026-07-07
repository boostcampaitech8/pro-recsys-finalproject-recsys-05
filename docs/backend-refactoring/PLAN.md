# Backend Refactoring — 계획 및 진행 (Rebaselined)

> 최초 작성 2026-07-07 · 재베이스 2026-07-07 (Phase A 완료 시점)
> 브랜치 `feature/backend-refactoring` (origin/dev를 `d42709b`로 머지 반영). 앵커(파일:행)는 Phase A 완료 후 기준.
> 실행 방식: 구현은 **codex plugin(`codex:codex-rescue`)에 위임**, 클로드가 diff 리뷰·검증·커밋. 검증은 **import 체크**로 진행하고, **Phase B 진입 전 pytest 체크포인트**(revive db/redis 필요).

---

## 0. 진행 요약

| Phase | 상태 |
|---|---|
| **A. 구조 정리 (동작 불변)** | ✅ **완료** (아래 커밋들) |
| **B. 카드화 (백엔드, 파싱 방식)** | ⏳ 대기 (Phase B 전 pytest 체크포인트) |
| **C. 프론트 배선** | ⏳ 대기 |

**브랜치 전략**: PR은 `dev`로 → dev 테스트 → dev→main. main 직행 금지. 현재 미푸시.

**테스트 실행법** (revive 스택 db/redis 재사용, `backend/`에서):
```bash
DATABASE_URL="postgresql+asyncpg://myuser:mypassword@localhost:5432/mydatabase" \
REDIS_URL="redis://localhost:6379" PYTHONPATH="$PWD" uv run pytest test/
```

---

## Phase A — 구조 정리 ✅ 완료

| # | 작업 | 커밋 |
|---|---|---|
| A0 | `services/ml_inference` → `domains/recommendation/ml_inference` 이동 | `b02babb` |
| A1 | `inference_service.py` 데모 코드(demo/main/`__main__`) 제거, print→`app.core.logger`, 데모용 pandas 제거 | `bab2531` |
| A4 | 잔재 엔드포인트 `POST /single_chat`·`/chat` + 죽은 `ChatRequest`/`ChatResponse`(죽은 `game_list` 포함) 제거 | `6e9241e` |
| A3 | `GameInfo` 정본화 (아래 아키텍처 결정) | `2fa0520` |
| A5 | `engine.py`의 `logging.basicConfig`(전역 root 재설정) 제거→core.logger, `tool_search.py` 중첩 `flatten_list` 2개→모듈레벨 `_flatten_list` | `8da1e3a` |
| A6 | `datetime.utcnow()` 7곳 교체(분리안), `maybe_save_recommendation` silent swallow→best-effort+로깅 | `8d77857` |
| A2 | RecommendationService 이름 충돌 → **무효**: 이미 `RecommendationService`(service.py) vs `IntegratedRecommendationService`(integrated_service.py)로 상이. 코드 변경 없음 | — |

### A3 아키텍처 결정 (codex 논의 → **Option 1** 채택)
- **`game.schemas`가 게임 DTO 정본.** `game/schemas.GameInfo`를 Pydantic v2로 통일, `chat/schemas.GameInfo` 중복 삭제. 의존 방향 `chat/recommendation → game` 유지.
- 죽은 `game_list` 필드(Multi/ChatTurnResponse)와 router 대입은 **A3에서 이미 제거 완료**.
- Pydantic v2 통일은 이로써 마무리(다른 v1 잔재 없음).

### A6 결정 사항
- **datetime 분리안**: 응답 DTO timestamp는 tz-aware `datetime.now(timezone.utc)`, naive DB 컬럼에 쓰는 `repository.updated_at`은 `.replace(tzinfo=None)`.
- **maybe_save_recommendation**: best-effort 유지 + 실패를 `logger.warning` 기록.

---

## Phase B — 카드화 (백엔드, **파싱 방식**)

> ⚠️ 제미나이 구조화 출력(response_format)은 **다른 브랜치 담당** — 여기서 안 함. 이 브랜치는 **파싱 방식**으로 game_id를 확보한다.

**핵심 근거 (Phase A 완료 후 실측)**
- recommendation 파이프라인이 이미 카드 형태를 생산: `integrated_service.py:~218`의 `recommended_games` = `{app_id, name, score, header_image, short_description_kr, genres_kr, price, release_date}`.
- `GameRepository.get_games_by_app_ids(app_ids: List[int])` (game/repository.py:97) = game_id 목록 → 카드 조회에 그대로 사용.
- 최종 답변 생성 지점: `chat/agent/engine.py:41 run_turn`(현재 `str` 반환). chitchat 분기는 engine 우회(`orchestrator.py:450 _run_chitchat`) → 카드 없음이 정상.
- chat 서비스 반환에 `retrieved_docs`가 이미 흐름(`services.process_chat_by_user`/`process_chat_turn`) — 현재 router에서 `_retrieved_docs`로 무시 중(A3에서 game_list 매핑 제거).

**작업 항목**
1. **`GameCard` 스키마 신설** — `game.schemas`에 위 recommended_games와 동일 필드로 정의(app_id·name·header_image·short_description_kr·genres_kr·price·release_date·score?). **recommendation.recommended_games와 chat.games가 이 GameCard를 공용**(매퍼 1개, 중복 재발 방지).
2. **game_id 파싱 경로** — 추천 파이프라인 결과(recommended_games) 또는 최종 답변에서 game_id 목록 확보 → `GameRepository.get_games_by_app_ids`로 카드 조회. LLM 구조화 출력 미사용. 파싱 실패 시 텍스트만(카드 빈 리스트) 폴백.
3. **응답 필드** — `ChatTurnResponse`(및 필요 시 MultiTurnChatResponse)에 `games: List[GameCard]` 추가. 시그니처 확장: 파싱 지점 → services → router.
4. **테스트** — mock LLM 단위 테스트. chitchat 분기는 카드 없음 확인.

**결정 필요 (Phase B 진입 시 인터뷰)**: game_id를 (a) recommendation 파이프라인 결과에서 취할지 (b) 최종 답변 텍스트에서 파싱할지 — 실측 후 결정.

---

## Phase C — 프론트 배선 (수정 2곳)

카드 UI는 이미 완성(`LLMAnswerBox.tsx`가 `games: RecommendedGame[]`를 카드+모달 렌더, `ChatMessage`·`ChatHistory` 전달까지).
1. `src/api/userApi.ts` `UserChatResponse`에 `games` 추가(`gameApi.ts`의 `RecommendedGame` 타입 재사용).
2. `MainPage.tsx`의 `games: []` 하드코딩 → 응답값 매핑.

프론트는 SSE 미사용, `POST /chat/chat/messages` 단발 fetch. 스키마 동일하면 컴포넌트 무변경.

---

## 별도/보류 항목

- **레이어링**: `chat.maybe_save_recommendation`이 recommendation repo/service를 우회해 `Recommendation`을 직접 write. Option 1에서 의도적으로 A3 범위 제외. 별도 항목으로 추후 처리(chat → recommendation service 경유).

## 검증·커밋 규칙
- 페이즈(가능하면 항목)별 커밋 분리, 매 단계 import 검증. **Phase B 전 pytest 체크포인트**(revive 스택 필요).
- 푸시·PR(dev)은 사용자 지시 시. 현재 방식은 머지 유지(강제푸시 없음).
