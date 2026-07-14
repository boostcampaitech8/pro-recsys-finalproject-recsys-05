# ADR-0007 · LLM 통신 계층 — 포트/어댑터 · 이중 스택 통일 · Langfuse

- **상태**: Accepted (2026-07-09) — 이행 T18(#114) · T19(#115)
- **맥락**: 같은 Gemini(OpenAI 호환) 엔드포인트를 **2개 스택이 따로 호출**한다.
  - **Stack A** = `providers/gemini.py` `GeminiProvider`(openai SDK) — 에이전트·의도분류 경로. 3단 모델 폴백 + 유료키 2단 폴백(T9).
  - **Stack B** = LangChain `ChatOpenAI` 직결 — 구형 RAG·스트리밍·llm-only 4개 엔드포인트(`chatbot.py`·`services.py`), `with_fallbacks` 체인(T11).
  - timeout=30·max_retries=1이 4곳 하드코딩, `GEMINI_*` env 로드 2곳, 폴백 모델 문자열 3곳 중복. **T11(유료 폴백을 Stack B에 수동 복제)이 이중 스택 유지비의 실측 증거.** LangChain은 프레임워크가 아니라 부분 래퍼로만 쓰이는 중(chain/langgraph 없음). 관측성 전무.

## 결정

1. **통신 계층 분리**: `backend/app/llm/` 신설. 도메인 계층(의도분류·에이전트·RAG 구성·대화 CRUD)은 외부 API를 모른다. 클라이언트 생성·키·타임아웃·폴백·관측성은 통신 계층이 **유일한 관문** (SPEC 불변식 7).
2. **포트/어댑터**: 포트 = `LLMProvider` 인터페이스(테스트 스텁 지점). 어댑터 = **openai SDK 유지**.
3. **LiteLLM은 조건부 어댑터 교체**: "2번째 벤더 도입 또는 벤더 간 폴백 필요" 시점에 어댑터만 교체(도메인 무수정). 단일 벤더(Gemini)인 지금 도입은 기각 — 추상화 비용 > 효익.
4. **LangChain 전면 통일 기각**: 자체 Tool/orchestrator 에이전트 엔진 재작성 비용이 크다. 대신 Stack B 4개 엔드포인트를 통신 계층으로 이관하며 LangChain 의존을 축소한다.
5. **설정 단일화**: `GEMINI_*`·타임아웃·재시도·폴백 체인 = `core/config.py Settings` 단일 소스.
6. **관측성 = Langfuse cloud free tier**: 어댑터 관문 1곳에 openai SDK drop-in(`langfuse.openai`). self-host 기각(v3는 ClickHouse 요구 — 12GB 서버 부담). LiteLLM/LangChain 없이 성립한다.

## 결과

- seam **S7**(Gemini 타임아웃 규약)은 계층 단일화로 구조적 해소 예정 — T18 완료까지 레지스트리 유지.
- `ml_llm/`은 무관: 오프라인 임베딩 파이프라인(로컬 SentenceTransformer bge-m3)으로 외부 LLM API 호출 없음 — 계약(S6)만 공유.
- 이행 순서: **T16(테스트 안전망) → T18 → T19.** 학습환경 재조성은 직교 문제(backend 재구조화와 무관, S6 계약만 유지하면 됨).
- **트레이드오프**: 이관 중 구형 엔드포인트 회귀 리스크 — T16의 마커·격리 테스트가 안전망. 어댑터 1곳 경유로 계층이 하나 늘지만, 4곳 중복 동기화 비용(T9→T11 재발 패턴)을 제거한다.
