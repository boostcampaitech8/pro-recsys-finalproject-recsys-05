# Backend Refactoring — 계획 및 진행 (Rebaselined)

> 최초 작성 2026-07-07 · 재베이스 2026-07-07 (Phase A 완료 시점)
> 브랜치 `feature/backend-refactoring` (origin/dev를 `d42709b`로 머지 반영). 앵커(파일:행)는 Phase A 완료 후 기준.
> 실행 방식: 구현은 **codex plugin(`codex:codex-rescue`)에 위임**, 클로드가 diff 리뷰·검증·커밋. 검증은 **import 체크**로 진행하고, **Phase B 진입 전 pytest 체크포인트**(revive db/redis 필요).

---

## 0. 진행 요약

| Phase | 상태 |
|---|---|
| **A. 구조 정리 (동작 불변)** | ✅ **완료** |
| **B. 카드화 (백엔드, 구조화출력 캡처)** | ✅ **완료** (B1~B4, pytest 45 passed·1 skipped) |
| **C. 프론트 배선** | ✅ **완료** (2026-07-07, src 4파일·tsc+build green) |

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

## Phase B — 카드화 (백엔드) ✅ 완료

> **완료 (2026-07-07).** codex 흐름조사 결과 "텍스트 파싱"은 불안정이라 폐기하고, **도구/추천 파이프라인의 구조화 출력을 engine이 최종 답변으로 뭉개기 전에 캡처**하는 방식(Option B)으로 구현. 커밋: B1 `d554925`(GameCard+games 필드), B2 `8749886`(검색툴 3종·RAG SQL에 app_id 노출 + maybe_save app_id=None 버그수정), B3a `8f70e17`(에이전트 경로: `engine.run_turn`→`(text, collected)`, `services._build_game_cards`가 `get_games_by_app_ids`로 재조회), B3b `9b0eec6`(RAG 경로 opt-in `return_game_cards`), B4 `9340d37`(`_collect_games` 단위테스트). **pytest 45 passed·1 skipped**, `_build_game_cards` 라이브 DB 검증. 핵심 함정: `Game.id`(내부PK)≠`Game.app_id`(Steam) — 카드 조회는 app_id 기준. RAG 카드 score=None(similarity와 recommendation score 구분).
>
> 아래는 설계 당시 메모(참고용).

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

## Phase C — 프론트 배선 ✅ 완료 (2026-07-07)

> **완료 (2026-07-07).** codex 사전조사·diff 2회 코드리뷰 병행. 결정 **(a) 프론트 타입 정합 + 가드 / score null이면 ⭐라인 숨김**. **플랜 확장(핵심)**: 런타임 null 크래시가 `score`(:61,:104)뿐 아니라 `genres_kr`(:110)·`price`(:129)도였음 → 3종 모두 가드. `RecommendedGame`을 백엔드 `GameCard`와 정합(app_id 외 전부 nullable, 단일 소스)하자 **strict tsc가 가드 누락을 컴파일 단계에서 강제**(예: `img alt`가 `string|null` 거부) → 빌드가 안전망. 커밋 `e04923e`(src 4파일: userApi·gameApi·MainPage·LLMAnswerBox). 검증 **`tsc && vite build` green**. Known-nit(무해): price=null·release_date有 시 `justify-between` 좌측 정렬.
>
> 아래는 실행 스펙(참고용).

**엔드포인트 확인**: 프론트 `sendChatMessage`(`userApi.ts:14`)는 `POST /chat/chat/messages` = `chat_unified` = **에이전트 경로**(B3a에서 카드 배선함). SSE 미사용, 단발 fetch. → 카드가 흐른다.

**타입 대조 (거의 일치)**: 백엔드 `GameCard` vs 프론트 `RecommendedGame`(`gameApi.ts:6-15`) 필드명·타입 동일(app_id·name·score·header_image·short_description_kr·genres_kr:string[]·price:number·release_date). **차이**: 백엔드는 전부 nullable(특히 **검색/RAG 카드는 score=None**, 추천툴 카드만 score 有), 프론트 `RecommendedGame`은 대부분 non-null.

**수정 위치 (실측)**
1. `src/api/userApi.ts:7-10` — `UserChatResponse`에 `games: RecommendedGame[]` 추가(`import type { RecommendedGame } from "./gameApi"`).
2. `src/pages/MainPage.tsx:173-176` — 성공 응답 분기의 `games: []`(**175행**)만 `games: response.games ?? []`로. 나머지 `games: []`(92·104·134·146·194행)는 로컬 시스템/에러 메시지라 그대로 둠.

**✅ 결정됨 (null 크래시 — score/genres_kr/price)**: `LLMAnswerBox.tsx:61`(`game.score.toFixed(1)`)·`:104`(`selectedGame.score.toFixed(2)`)·`:110`(`genres_kr.map`)·`:129`(`price.toLocaleString`)가 non-null로 가정. 백엔드 chat 카드는 검색/RAG일 때 score=null(그 외 필드도 DB 결측 시 null 가능) → **null이면 런타임 크래시**. "컴포넌트 무변경" 가정 깨짐. 택1: (a) `LLMAnswerBox`에 null 가드(score/price는 `!= null`로 0 보존·⭐라인 숨김, genres_kr `?? []`) + `RecommendedGame`을 전부 nullable로, (b) 백엔드가 기본값(0 등) 부여(0이 최저점처럼 보이는 부작용), (c) chat 전용 카드 타입 분리. → **(a) 채택** (score만이 아니라 genres_kr·price까지 동일 가드). 구현·검증 완료.

**검증**: 프론트는 pytest 대신 `tsc`/빌드(`npm run build` 등)로 타입 확인. `dev` PR 전 `origin/dev` 재머지(현재 behind 6).

---

## 별도/보류 항목

- **레이어링**: `chat.maybe_save_recommendation`이 recommendation repo/service를 우회해 `Recommendation`을 직접 write. Option 1에서 의도적으로 A3 범위 제외. 별도 항목으로 추후 처리(chat → recommendation service 경유).

## 검증·커밋 규칙
- 페이즈(가능하면 항목)별 커밋 분리, 매 단계 import 검증. **Phase B 전 pytest 체크포인트**(revive 스택 필요).
- 푸시·PR(dev)은 사용자 지시 시. 현재 방식은 머지 유지(강제푸시 없음).
