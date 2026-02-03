# Backend 통합 구조 및 오케스트레이션 메뉴얼

**작성일:** 2025-02-03
**대상:** Backend 리드 / 오케스트레이터 개발자
**목표:** Function Calling을 포함한 완전한 Backend 아키텍처 설계 및 구현 가이드

---

## 📌 목차

1. [현재 상황 분석](#현재-상황-분석)
2. [Backend 전체 아키텍처](#backend-전체-아키텍처)
3. [Function Calling 통합 설계](#function-calling-통합-설계)
4. [구현 단계별 가이드](#구현-단계별-가이드)
5. [데이터 흐름 상세](#데이터-흐름-상세)
6. [통합 테스트 전략](#통합-테스트-전략)
7. [배포 및 모니터링](#배포-및-모니터링)
8. [트러블슈팅](#트러블슈팅)

---

## 현재 상황 분석

### 📊 Backend 현재 구조

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 애플리케이션 엔트리포인트
│   ├── core/
│   │   ├── config.py             # 환경변수 설정
│   │   ├── logger.py             # 로깅 설정
│   │   └── database.py           # DB 연결 (PostgreSQL)
│   ├── domains/
│   │   ├── chat/
│   │   │   ├── chatbot.py        # 🔴 RAG 기반 챗봇 (현재)
│   │   │   ├── router.py         # FastAPI 라우터
│   │   │   ├── schemas.py        # Pydantic 모델
│   │   │   ├── models.py         # SQLAlchemy 모델
│   │   │   ├── tools.py          # 🟢 새로 추가할 파일
│   │   │   └── orchestrator.py   # 🟢 새로 추가할 파일
│   │   ├── recommendation/
│   │   │   ├── service.py        # 추천 모델 API
│   │   │   ├── router.py
│   │   │   └── ...
│   │   ├── steam/
│   │   │   └── ...
│   │   └── user/
│   │       └── ...
│   └── routers/
│       └── health.py              # 헬스체크
├── tests/
├── scripts/
├── docker/
├── .env
└── main.py                        # FastAPI 애플리케이션 실행
```

### 🔴 현재의 문제점

| 문제 | 원인 | 영향 |
|------|------|------|
| **데이터 정확도 부족** | RAG 검색만 사용 → 최신 정보 반영 불가 | 사용자가 오래된 게임 정보 조회 |
| **동적 필터링 불가** | LLM이 가격/장르 필터링 안 함 | "1만원 이하 RPG" 같은 복잡한 요청 처리 불가 |
| **추천 모델 미사용** | RAG 결과만 사용 | 개인화 추천 불가 |
| **Function Call 미지원** | 단순 RAG + LLM 파이프라인 | 조회 → 선택 → 상세 정보 같은 다단계 대화 불가 |

### 🟢 개선 방향

```
┌─────────────────────────────────────────────────┐
│ User Query                                      │
│ "1만원 이하 RPG 추천해줘"                        │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ Router: /single_chat (FastAPI)                  │
│ - 요청 검증                                      │
│ - User ID 추출                                   │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ Orchestrator (새로운 오케스트레이션 레이어)      │
│ - LLM에게 사용자 쿼리 해석 요청                   │
│ - Function call 결정: search_games_by_filter()  │
│   (query="RPG", max_price=10000)                │
└───────────────────┬─────────────────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
    ┌────────────┐      ┌─────────────┐
    │  Tools     │      │  LLM 호출   │
    │  (DB)      │      │  (CLOVA)    │
    │ 게임 검색  │      │             │
    └────────────┘      └─────────────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ Chatbot: generate_response()                    │
│ - 검색 결과 + LLM 응답 조합                      │
│ - "추천 게임 3개: ..."                           │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ Response: ChatResponse                          │
│ {                                               │
│   "text": "추천 게임은...",                      │
│   "game_list": [{...}, {...}],                  │
│   "debug": {...}                                │
│ }                                               │
└─────────────────────────────────────────────────┘
```

---

## Backend 전체 아키텍처

### 🏗️ 계층별 구조 (Layered Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│                    (FastAPI Routes)                      │
│                                                         │
│  /chat/single_chat  /chat/echo  /health  etc.          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│               Business Logic Layer                       │
│                  (Orchestrator)                          │
│                                                         │
│  - LLM 요청 라우팅                                       │
│  - Function call 판단 및 실행                            │
│  - 응답 조합 및 포맷팅                                    │
└────────────────────┬────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
┌─────▼────┐  ┌──────▼────┐  ┌─────▼────┐
│ Tools    │  │  Chatbot  │  │ Services │
│ (DB)     │  │  (RAG)    │  │ (Models) │
│          │  │           │  │          │
│ - Search│  │ - Embed   │  │- Recomm. │
│ - Info  │  │ - Retrieve│  │- Review  │
│ - Filter│  │ - Generate│  │          │
└─────────┘  └───────────┘  └──────────┘
      │              │              │
└─────┴──────────────┴──────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                Data Access Layer                         │
│                                                         │
│  - PostgreSQL (games, reviews, user_history)           │
│  - Redis (cache)                                         │
│  - Vector DB (pgvector for embeddings)                  │
│  - External APIs (Steam, BentoML)                       │
└──────────────────────────────────────────────────────────┘
```

### 🔗 컴포넌트 간 상호작용

```
User Request
    ↓
[FastAPI Router] ─────────────────────┐
                                      │
                              ┌───────▼────────┐
                              │ Orchestrator   │
                              │ (NEW)          │
                              └───────┬────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
            ┌───────▼────────┐ ┌──────▼────────┐ ┌─────▼──────┐
            │ LLM (CLOVA)    │ │ Tools.py      │ │ Chatbot    │
            │ Function Call  │ │ - Query DB    │ │ (RAG)      │
            │ Decision       │ │ - Filter Data │ │            │
            └────────────────┘ └───────────────┘ └────────────┘
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      │
                          ┌───────────▼───────────┐
                          │ Response Generation   │
                          │ (Combine all results) │
                          └───────────┬───────────┘
                                      │
                                      ↓
                              Response to User
```

---

## Function Calling 통합 설계

### 📋 Function Calling 워크플로우

```
1️⃣ User Query 분석
   ↓
"1만원 이하 RPG 추천해줘"
   ↓
2️⃣ LLM에게 의도 파악 요청 (Intent Detection)
   ↓
LLM: "이 사용자는 게임을 검색(search)하고 싶어"
LLM이 인식: max_price=10000, tags=["RPG"]
   ↓
3️⃣ Function Call 실행
   ↓
search_games_by_filter(
    max_price=10000,
    tags=["RPG"]
)
   ↓
4️⃣ Tools에서 DB 쿼리 실행
   ↓
[
    {"id": 1, "title": "Game A", "price": 5000, ...},
    {"id": 2, "title": "Game B", "price": 9800, ...},
    ...
]
   ↓
5️⃣ LLM에게 검색 결과 전달 및 응답 생성
   ↓
LLM: "1만원 이하 RPG로는 Game A, Game B가 있습니다..."
   ↓
6️⃣ 사용자에게 응답 반환
   ↓
Response
```

### 🔄 Function Call 종류

| 종류 | 예시 | 호출 조건 | 우선순위 |
|------|------|---------|---------|
| **Search** | search_games_by_filter() | "1만원 이하 RPG", "할인 게임" | 🔴 필수 |
| **Info** | get_game_info() | "엘든링 가격", "이 게임 요구사항" | 🔴 필수 |
| **Recommend** | get_personalized_recommendations() | "추천해줘", "내 취향 게임" | 🔴 필수 |
| **Review** | get_game_reviews() | "평가는?", "리뷰 어때?" | 🟡 선택 |
| **Trending** | get_trending_games() | "요즘 인기 게임", "최신 게임" | 🟡 선택 |

---

## 구현 단계별 가이드

### 📍 Phase 1: 기초 준비 (1-2일)

#### 1.1 tools.py 구현

**위치:** `backend/app/domains/chat/tools.py`

참고: [Function Call Tools 개발 메뉴얼](./FUNCTION_CALL_TOOLS_DEVELOPMENT.md) 참조

**체크리스트:**
```python
# ✅ 필수 4개 함수
class GameTools:
    async def get_game_info(self, game_name: str, wanted: Optional[List[str]] = None)
    async def get_personalized_recommendations(self, top_k: int = 5)
    async def search_games_by_filter(self, query=None, max_price=None, tags=None, ...)
    async def get_game_reviews(self, game_name: str)  # 선택

# ✅ 의존성 주입
def get_game_tools(db_session: AsyncSession, redis_client=None) -> GameTools
```

#### 1.2 Schemas 확장

**위치:** `backend/app/domains/chat/schemas.py`

Function Call 관련 Pydantic 모델 추가:

```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Existing
class ChatRequest(BaseModel):
    text: str

class ChatResponse(BaseModel):
    text: str
    game_list: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# New - Function Call 관련
class FunctionCall(BaseModel):
    """LLM이 호출하기로 결정한 함수"""
    name: str  # "search_games_by_filter", "get_game_info", etc.
    arguments: Dict[str, Any]  # 함수 매개변수

class FunctionResult(BaseModel):
    """함수 실행 결과"""
    function_name: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class OrchestrationContext(BaseModel):
    """오케스트레이션 컨텍스트 (내부용)"""
    user_query: str
    detected_intent: str  # "search", "info", "recommend"
    function_calls: List[FunctionCall] = []
    function_results: List[FunctionResult] = []
    llm_response: Optional[str] = None
```

---

### 📍 Phase 2: 오케스트레이션 레이어 구축 (2-3일)

#### 2.1 Orchestrator 클래스 생성

**위치:** `backend/app/domains/chat/orchestrator.py`

```python
"""
LLM Function Calling Orchestrator

역할:
1. 사용자 의도 파악 (Intent Detection)
2. 필요한 함수 결정 및 호출
3. 함수 결과 조합 및 LLM 응답 생성
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.domains.chat.tools import GameTools
from app.domains.chat.schemas import (
    FunctionCall, FunctionResult, OrchestrationContext
)
from app.core.logger import logger

logger = logging.getLogger(__name__)


class Orchestrator:
    """Function Calling 오케스트레이션을 관리합니다"""

    def __init__(self, tools: GameTools, llm):
        """
        초기화

        Args:
            tools (GameTools): DB/API 접근 도구
            llm: CLOVA Studio LLM 인스턴스
        """
        self.tools = tools
        self.llm = llm
        self.context: Optional[OrchestrationContext] = None

    async def orchestrate(
        self,
        user_query: str,
        steam_id: Optional[str] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """
        사용자 쿼리를 처리하는 메인 메서드

        Args:
            user_query (str): 사용자의 자연어 쿼리
            steam_id (str, optional): 사용자 ID (추천용)

        Returns:
            Tuple[str, List[Dict]]:
                - response_text: LLM이 생성한 최종 응답
                - game_list: 추천/검색된 게임 목록 (있으면)

        Flow:
            1. Intent Detection (LLM)
            2. Function Call Execution (Tools)
            3. Response Generation (LLM)
        """
        logger.info(f"🎯 Orchestrating: {user_query[:50]}...")

        # 0. 컨텍스트 초기화
        self.context = OrchestrationContext(user_query=user_query)

        try:
            # 1️⃣ Step 1: Intent Detection
            logger.info("Step 1: Intent Detection...")
            intent = await self._detect_intent(user_query)
            self.context.detected_intent = intent
            logger.info(f"   ✅ Detected intent: {intent}")

            # 2️⃣ Step 2: Function Call Planning
            logger.info("Step 2: Function Call Planning...")
            function_calls = await self._plan_function_calls(user_query, intent)
            self.context.function_calls = function_calls
            logger.info(f"   ✅ Planned {len(function_calls)} function call(s)")

            # 3️⃣ Step 3: Function Execution
            logger.info("Step 3: Executing Functions...")
            function_results = await self._execute_functions(function_calls, steam_id)
            self.context.function_results = function_results
            logger.info(f"   ✅ Executed {len(function_results)} function(s)")

            # 4️⃣ Step 4: Combine Results & Generate Response
            logger.info("Step 4: Generating Response...")
            response_text, game_list = await self._generate_final_response(
                user_query,
                intent,
                function_results
            )
            self.context.llm_response = response_text
            logger.info(f"   ✅ Response generated")

            return response_text, game_list

        except Exception as e:
            logger.error(f"❌ Orchestration failed: {e}")
            return f"오류가 발생했습니다: {str(e)}", None

    # ============================================
    # Step 1: Intent Detection
    # ============================================

    async def _detect_intent(self, user_query: str) -> str:
        """
        사용자의 의도를 판단합니다

        Returns:
            str: "search" | "info" | "recommend" | "review" | "other"
        """
        intent_prompt = f"""다음 사용자 쿼리의 의도를 한 가지만 골라주세요.

사용자: {user_query}

의도 분류:
- "search": 게임을 검색하거나 필터링 (예: "1만원 이하 RPG", "할인 게임")
- "info": 특정 게임의 정보 조회 (예: "엘든링 가격", "이 게임 요구사항")
- "recommend": 개인화된 추천 요청 (예: "추천해줘", "내 취향 게임")
- "review": 게임 리뷰/평점 조회 (예: "평가는?", "리뷰 어때?")
- "other": 위에 해당하지 않는 일반 대화

**응답: 의도 분류 단어 하나만 반환하세요** (예: "search")"""

        try:
            # LLM에 의도 분류 요청
            response = await self.llm.ainvoke(intent_prompt)
            intent = response.content.strip().lower()

            # 유효한 의도 값만 허용
            valid_intents = ["search", "info", "recommend", "review", "other"]
            return intent if intent in valid_intents else "other"

        except Exception as e:
            logger.error(f"❌ Intent detection error: {e}")
            return "other"

    # ============================================
    # Step 2: Function Call Planning
    # ============================================

    async def _plan_function_calls(
        self,
        user_query: str,
        intent: str
    ) -> List[FunctionCall]:
        """
        필요한 함수 호출을 계획합니다
        """
        if intent == "search":
            # 동적 쿼리 파라미터 생성
            params = await self._extract_search_params(user_query)
            return [FunctionCall(name="search_games_by_filter", arguments=params)]

        elif intent == "info":
            # 게임 이름 추출
            game_name = await self._extract_game_name(user_query)
            return [
                FunctionCall(
                    name="get_game_info",
                    arguments={"game_name": game_name}
                )
            ]

        elif intent == "recommend":
            return [
                FunctionCall(
                    name="get_personalized_recommendations",
                    arguments={"top_k": 5}
                )
            ]

        elif intent == "review":
            game_name = await self._extract_game_name(user_query)
            return [
                FunctionCall(
                    name="get_game_reviews",
                    arguments={"game_name": game_name}
                )
            ]

        else:  # "other"
            return []  # 함수 호출 없이 LLM 응답만

    # ============================================
    # Helper Methods
    # ============================================

    async def _extract_search_params(self, user_query: str) -> Dict[str, Any]:
        """
        사용자 쿼리에서 검색 파라미터를 추출합니다

        Example:
            Input: "1만원 이하 RPG 게임 찾아줘"
            Output: {"max_price": 10000, "tags": ["RPG"]}
        """
        extraction_prompt = f"""다음 쿼리에서 게임 검색 조건을 JSON으로 추출해주세요.

사용자: {user_query}

추출할 필드:
- max_price: 최대 가격 (숫자, 없으면 null)
- tags: 장르 (배열, 없으면 null)
- query: 검색어 (문자열, 없으면 null)
- on_sale: 할인 여부 (boolean, 기본 false)

**응답: 유효한 JSON만 반환하세요**
예:
{{"max_price": 10000, "tags": ["RPG"], "query": null, "on_sale": false}}"""

        try:
            response = await self.llm.ainvoke(extraction_prompt)
            params_json = response.content.strip()

            # JSON 파싱
            params = json.loads(params_json)

            # null 값 제거 (함수 호출에서 선택적 매개변수로만 사용)
            cleaned_params = {k: v for k, v in params.items() if v is not None}
            return cleaned_params

        except Exception as e:
            logger.error(f"❌ Parameter extraction error: {e}")
            return {}

    async def _extract_game_name(self, user_query: str) -> str:
        """사용자 쿼리에서 게임 이름을 추출합니다"""
        extraction_prompt = f"""다음 사용자 쿼리에서 게임 이름을 추출해주세요.

사용자: {user_query}

**응답: 게임 이름만 반환하세요** (예: "Elden Ring")"""

        try:
            response = await self.llm.ainvoke(extraction_prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"❌ Game name extraction error: {e}")
            return ""

    async def _execute_functions(
        self,
        function_calls: List[FunctionCall],
        steam_id: Optional[str] = None
    ) -> List[FunctionResult]:
        """
        계획된 함수들을 실행하고 결과를 수집합니다
        """
        results = []

        for func_call in function_calls:
            logger.info(f"   Executing: {func_call.name}")

            try:
                # 함수 호출 (reflection 사용)
                result = await self._call_function(func_call, steam_id)

                results.append(
                    FunctionResult(
                        function_name=func_call.name,
                        success=True,
                        result=result
                    )
                )
                logger.info(f"   ✅ {func_call.name} completed")

            except Exception as e:
                logger.error(f"   ❌ {func_call.name} failed: {e}")
                results.append(
                    FunctionResult(
                        function_name=func_call.name,
                        success=False,
                        error=str(e)
                    )
                )

        return results

    async def _call_function(
        self,
        func_call: FunctionCall,
        steam_id: Optional[str] = None
    ) -> Any:
        """
        함수 이름과 인자를 받아 실제 함수를 호출합니다 (Reflection)
        """
        func_name = func_call.name
        arguments = func_call.arguments

        # steam_id는 모든 함수에 자동 주입
        if steam_id and "steam_id" not in arguments:
            arguments["steam_id"] = steam_id

        # 함수 호출
        if func_name == "search_games_by_filter":
            return await self.tools.search_games_by_filter(**arguments)
        elif func_name == "get_game_info":
            return await self.tools.get_game_info(**arguments)
        elif func_name == "get_personalized_recommendations":
            return await self.tools.get_personalized_recommendations(**arguments)
        elif func_name == "get_game_reviews":
            return await self.tools.get_game_reviews(**arguments)
        else:
            raise ValueError(f"Unknown function: {func_name}")

    async def _generate_final_response(
        self,
        user_query: str,
        intent: str,
        function_results: List[FunctionResult]
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """
        함수 실행 결과를 바탕으로 최종 응답을 생성합니다
        """
        # 함수 결과를 문자열로 포맷
        results_summary = ""
        game_list = None

        for result in function_results:
            if result.success:
                if result.function_name == "search_games_by_filter":
                    game_list = result.result
                    results_summary += f"\n검색 결과: {json.dumps(result.result, ensure_ascii=False)}"
                elif result.function_name == "get_game_info":
                    results_summary += f"\n게임 정보: {json.dumps(result.result, ensure_ascii=False)}"
                elif result.function_name == "get_personalized_recommendations":
                    game_list = result.result
                    results_summary += f"\n추천 결과: {json.dumps(result.result, ensure_ascii=False)}"
                elif result.function_name == "get_game_reviews":
                    results_summary += f"\n리뷰: {json.dumps(result.result, ensure_ascii=False)}"
            else:
                results_summary += f"\n⚠️ {result.function_name} 실패: {result.error}"

        # LLM에게 최종 응답 생성 요청
        response_prompt = f"""다음 정보를 바탕으로 사용자 질문에 친절하게 답변해주세요.

사용자 질문: {user_query}

함수 실행 결과:
{results_summary}

**답변 가이드:**
1. 위 데이터만 사용해서 답변하세요
2. 게임명, 장르, 가격을 명확히 포함하세요
3. 친절하고 자연스러운 한국어로 대답하세요
4. 데이터가 없으면 솔직하게 "정보를 찾을 수 없습니다"라고 말하세요

**답변:**"""

        try:
            response = await self.llm.ainvoke(response_prompt)
            response_text = response.content.strip()
            return response_text, game_list

        except Exception as e:
            logger.error(f"❌ Response generation error: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}", game_list
```

#### 2.2 Chatbot 클래스 수정

**위치:** `backend/app/domains/chat/chatbot.py` (기존 파일 수정)

기존 `generate_response_with_details()` 메서드 위에 함수 호출 옵션 추가:

```python
class chatbot:
    def __init__(self):
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        self.engine = None
        self.llm: Optional[ChatOpenAI] = None
        self.retriever = None
        self.prompt_template: Optional[ChatPromptTemplate] = None
        self.output_parser = StrOutputParser()
        self.config: Dict[str, Any] = {}
        self._initialized = False
        self.orchestrator: Optional["Orchestrator"] = None  # 🆕 추가

    async def initialize(
        self,
        engine: AsyncEngine,
        clova_api_key: str,
        clova_base_url: str = "https://clovastudio.stream.ntruss.com/v1/openai/",
        model_name: str = "HCX-DASH-001",
        temperature: float = 0.5,
        max_tokens: int = 1024,
        top_k: int = 3,
        use_function_calling: bool = True  # 🆕 추가
    ):
        """기존 코드 + orchestrator 초기화"""
        # ... 기존 초기화 코드 ...

        # 🆕 Orchestrator 초기화
        if use_function_calling:
            from app.domains.chat.tools import GameTools
            from app.domains.chat.orchestrator import Orchestrator

            game_tools = GameTools(db_session=engine)
            self.orchestrator = Orchestrator(tools=game_tools, llm=self.llm)
            logger.info("✅ Orchestrator initialized (Function Calling enabled)")

    async def generate_response_with_details(
        self,
        user_query: str,
        use_function_calling: bool = True,  # 🆕 추가
        steam_id: Optional[str] = None       # 🆕 추가
    ) -> Tuple[str, List[Dict[str, Any]], str, Dict[str, float]]:
        """
        응답 생성 (Function Calling 선택)

        Args:
            user_query: 사용자 질문
            use_function_calling: True면 Orchestrator 사용, False면 RAG만 사용
            steam_id: 추천용 사용자 ID

        Flow:
            1. use_function_calling이 True이면 Orchestrator 호출
            2. False면 기존 RAG 방식 사용
        """
        if not self.is_ready():
            return "챗봇이 준비되지 않았습니다.", [], "", {}

        metrics = {}
        start_total = time.time()

        try:
            # 🆕 Function Calling 모드
            if use_function_calling and self.orchestrator:
                logger.info(f"[Function Calling Mode] {user_query[:50]}...")
                response_text, game_list = await self.orchestrator.orchestrate(
                    user_query=user_query,
                    steam_id=steam_id
                )
                metrics["mode"] = "function_calling"
                metrics["total_time"] = time.time() - start_total
                return response_text, game_list or [], "", metrics

            # ❌ Fallback to RAG Mode
            else:
                logger.info(f"[RAG Mode] {user_query[:50]}...")
                # 기존 코드 유지
                return await self._generate_response_rag(user_query, metrics)

        except Exception as e:
            logger.error(f"❌ Generation error: {e}")
            metrics["total_time"] = time.time() - start_total
            return f"오류가 발생했습니다: {str(e)}", [], "", metrics

    async def _generate_response_rag(
        self,
        user_query: str,
        metrics: Dict[str, float]
    ) -> Tuple[str, List[Dict[str, Any]], str, Dict[str, float]]:
        """기존 RAG 파이프라인 (별도 메서드로 분리)"""
        # 기존 generate_response_with_details 코드 이동
        # ...
        pass
```

---

### 📍 Phase 3: Router 통합 (1-2일)

#### 3.1 Router 수정

**위치:** `backend/app/domains/chat/router.py`

```python
@router.post(
    "/single_chat",
    response_model=ChatResponse,
    summary="게임 추천 (Function Calling 지원)"
)
async def single_chat_recommend(
    request: ChatRequest,
    response: Response,
    user_id: str = Header(..., alias="id"),
    use_function_calling: bool = Query(
        default=True,
        description="True: Function Calling 활성화, False: RAG만 사용"
    ),
    bot: chatbot = Depends(get_chatbot)
):
    """
    개선된 게임 추천 API

    **새로운 기능:**
    - Function Calling 지원 (기본 활성화)
    - 동적 필터링 가능
    - 추천 모델 연동
    - 다단계 대화 지원

    **쿼리 파라미터:**
    - use_function_calling: Function Calling 활성화 여부
    """

    if not bot.is_ready():
        logger.error(f"Chatbot not ready for user {user_id}")
        raise HTTPException(
            status_code=500,
            detail="챗봇 서비스가 준비되지 않았습니다."
        )

    try:
        logger.info(
            f"[v2][{user_id}] Request (FC={use_function_calling}): {request.text[:50]}..."
        )

        # 🆕 Function Calling 옵션 전달
        response_text, game_list, formatted_prompt, metrics = await bot.generate_response_with_details(
            user_query=request.text,
            use_function_calling=use_function_calling,
            steam_id=user_id
        )

        response.headers["id"] = user_id

        response_data = {
            "text": response_text,
            "game_list": game_list
        }

        if DEBUG_MODE:
            response_data["debug"] = {
                "metrics": {
                    "total_ms": metrics.get("total_time", 0) * 1000,
                    "mode": metrics.get("mode", "rag")
                }
            }

        return ChatResponse(**response_data)

    except Exception as e:
        logger.error(f"[v2][{user_id}] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 📍 Phase 4: 통합 및 테스트 (2-3일)

#### 4.1 main.py 수정 (Lifespan)

**위치:** `backend/app/main.py`

```python
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan 이벤트"""

    # Startup
    logger.info("🚀 Starting up...")

    # 1. DB 엔진 생성
    engine = create_async_engine(
        DATABASE_URL,
        echo=DEBUG_MODE,
        pool_size=20,
        max_overflow=0
    )

    # 2. 챗봇 초기화
    from app.domains.chat.chatbot import get_chatbot
    bot = get_chatbot()

    await bot.initialize(
        engine=engine,
        clova_api_key=CLOVA_API_KEY,
        use_function_calling=True  # 🆕
    )

    logger.info("✅ Startup complete!")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    bot.cleanup()
    await engine.dispose()
    logger.info("✅ Shutdown complete!")

# FastAPI 앱
app = FastAPI(
    title="RecSys Chat API",
    version="2.0",
    lifespan=lifespan
)

# 라우터 등록
from app.domains.chat.router import router as chat_router
app.include_router(chat_router, prefix="/chat", tags=["chat"])
```

---

## 데이터 흐름 상세

### 📊 전체 데이터 흐름도

```
┌─────────────────────────────────────────────────────────────────┐
│ Client Request                                                  │
│ POST /chat/single_chat                                          │
│ Body: {"text": "1만원 이하 RPG"}                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Router (FastAPI)                                                │
│ - 요청 검증                                                      │
│ - User ID 추출                                                   │
│ - use_function_calling 플래그 확인                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Chatbot.generate_response_with_details()                        │
│                                                                 │
│ if use_function_calling:                                       │
│     → Orchestrator.orchestrate()                                │
│ else:                                                           │
│     → _generate_response_rag()                                  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼ (FC Mode)          ▼ (RAG Mode)
   ┌──────────┐         ┌──────────┐
   │Orchestrator    │    │Chatbot   │
   └──────────┘         └──────────┘
        │                     │
        ├─ Intent Detection   ├─ Embedding
        │  (LLM)             │  (HF)
        │                    │
        ├─ Function Planning │
        │  (LLM)             ├─ Vector Search
        │                    │  (pgvector)
        ├─ Tools Execution   │
        │  │                 ├─ Context Retrieval
        │  ├─ search_games_by_filter()  │
        │  │   └─ PostgreSQL Query      │
        │  │                 ├─ Prompt Building
        │  ├─ get_game_info()
        │  │   └─ PostgreSQL Query      ├─ LLM Response Gen
        │  │                 │  (CLOVA)
        │  ├─ get_recommendations()
        │  │   └─ BentoML Call
        │  │
        │  └─ get_game_reviews()
        │      └─ PostgreSQL Query
        │
        └─ Response Generation
           (LLM)
            │
            ▼
    ┌──────────────────┐
    │ Final Response   │
    │ - text: str      │
    │ - game_list: [] │
    └──────────────────┘
            │
            ▼
    Return to Client
```

### 🔄 상세 시퀀스 다이어그램

```
User              Router           Chatbot          Orchestrator       Tools          LLM
│                  │                 │                  │               │             │
├─Query─────────>  │                 │                  │               │             │
│                  ├─validate────>    │                  │               │             │
│                  │                  ├─orchestrate─>    │               │             │
│                  │                  │                  ├─detect_intent─────────>    │
│                  │                  │                  │               │        response
│                  │                  │                  |<─intent───────────────────┤
│                  │                  │                  │               │             │
│                  │                  │                  ├─plan_functions            │
│                  │                  │                  │               │             │
│                  │                  │                  ├─extract_params────────>   │
│                  │                  │                  │               │        response
│                  │                  │                  |<─params───────────────────┤
│                  │                  │                  │               │             │
│                  │                  │                  ├─execute_functions         │
│                  │                  │                  │  ├─search────────────>DB
│                  │                  │                  │  |<─results─────────────┤
│                  │                  │                  │  ├─info─────────────>DB
│                  │                  │                  │  |<─results─────────────┤
│                  │                  │                  │  └─recommend────>BentoML
│                  │                  │                  │    |<─results─────────────┤
│                  │                  │                  │               │             │
│                  │                  │                  ├─generate_response────>    │
│                  │                  │                  │               │        response
│                  │                  │                  |<─response─────────────────┤
│                  │                  │<─response────    │               │             │
│<─response────────│<─ChatResponse────┤                  │               │             │
```

---

## 통합 테스트 전략

### 🧪 Unit Test (함수별)

**위치:** `backend/test/test_tools.py`

```python
import pytest
from app.domains.chat.tools import GameTools
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def mock_db():
    """Mock DB 세션"""
    # SQLite 메모리 DB 사용 (테스트용)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # ... 테이블 생성 및 샘플 데이터 삽입 ...
    return engine

@pytest.mark.asyncio
async def test_get_game_info(mock_db):
    """get_game_info 테스트"""
    tools = GameTools(mock_db)

    result = await tools.get_game_info("Elden Ring")

    assert result["title"] == "ELDEN RING"
    assert "price" in result
    assert "details" in result

@pytest.mark.asyncio
async def test_search_games_by_filter(mock_db):
    """search_games_by_filter 테스트"""
    tools = GameTools(mock_db)

    result = await tools.search_games_by_filter(
        max_price=50000,
        tags=["RPG"]
    )

    assert isinstance(result, list)
    assert all(r["price"] <= 50000 for r in result)
```

### 🧪 Integration Test (전체 흐름)

**위치:** `backend/test/test_orchestrator.py`

```python
@pytest.mark.asyncio
async def test_orchestration_search():
    """검색 오케스트레이션 테스트"""
    # Setup
    tools = GameTools(mock_db)
    llm = MockClovaLLM()  # 테스트용 Mock LLM
    orchestrator = Orchestrator(tools, llm)

    # Execute
    response_text, game_list = await orchestrator.orchestrate(
        user_query="1만원 이하 RPG"
    )

    # Assert
    assert len(response_text) > 0
    assert isinstance(game_list, list)
    assert all(g["price"] <= 10000 for g in game_list)

@pytest.mark.asyncio
async def test_orchestration_info():
    """정보 조회 오케스트레이션 테스트"""
    response_text, _ = await orchestrator.orchestrate(
        user_query="엘든링 가격이 얼마예요?"
    )

    assert "엘든링" in response_text or "Elden Ring" in response_text
```

### 🧪 E2E Test (Router 레벨)

**위치:** `backend/test/test_router.py`

```python
from fastapi.testclient import TestClient

def test_single_chat_with_function_calling(client: TestClient):
    """단일 채팅 API 테스트 (Function Calling)"""
    response = client.post(
        "/chat/single_chat",
        json={"text": "1만원 이하 RPG"},
        headers={"id": "test_user_123"},
        params={"use_function_calling": True}
    )

    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "game_list" in data

def test_single_chat_rag_only(client: TestClient):
    """단일 채팅 API 테스트 (RAG Only)"""
    response = client.post(
        "/chat/single_chat",
        json={"text": "재미있는 게임 추천해줘"},
        headers={"id": "test_user_123"},
        params={"use_function_calling": False}
    )

    assert response.status_code == 200
```

### 🧪 성능 테스트

**위치:** `backend/test/test_performance.py`

```python
@pytest.mark.asyncio
async def test_search_latency():
    """검색 성능 테스트"""
    import time

    tools = GameTools(db)
    start = time.time()

    for _ in range(10):
        await tools.search_games_by_filter(
            max_price=50000,
            tags=["RPG"]
        )

    elapsed = (time.time() - start) / 10
    print(f"Average search latency: {elapsed*1000:.2f}ms")

    assert elapsed < 0.5, "Search should complete in < 500ms"
```

---

## 배포 및 모니터링

### 🚀 배포 체크리스트

#### Pre-Deployment

- [ ] 모든 테스트 통과 (`pytest`)
- [ ] 코드 커버리지 >= 80% (`pytest-cov`)
- [ ] 린트 체크 통과 (`ruff`, `mypy`)
- [ ] 시크릿 스캔 완료 (`truffleHog`)
- [ ] DB 마이그레이션 준비 완료

#### Deployment

```bash
# 1. 환경 변수 확인
echo $CLOVA_API_KEY
echo $DATABASE_URL
echo $REDIS_URL

# 2. 이미지 빌드
docker build -t recsys-backend:v2.0 .

# 3. 컨테이너 실행 (예: Docker Compose)
docker-compose up -d

# 4. 헬스체크
curl http://localhost:8000/health

# 5. API 테스트
curl -X POST http://localhost:8000/chat/single_chat \
  -H "Content-Type: application/json" \
  -H "id: test_user" \
  -d '{"text": "1만원 이하 게임"}'
```

### 📊 모니터링 메트릭

#### 핵심 메트릭 (KPI)

| 메트릭 | 목표 | 모니터링 |
|--------|------|---------|
| **평균 응답 시간** | < 2초 | Prometheus |
| **Function Call 성공률** | > 99% | CloudWatch |
| **캐시 히트율** | > 80% | Redis |
| **DB 연결 풀 사용률** | < 80% | PostgreSQL |
| **LLM API 오류율** | < 1% | CLOVA Logs |

#### 로그 구조

```json
{
    "timestamp": "2025-02-03T12:34:56Z",
    "level": "INFO",
    "user_id": "steam_123",
    "module": "chat.orchestrator",
    "message": "Intent detection: search",
    "duration_ms": 245,
    "function_calls": ["search_games_by_filter"],
    "function_results": [
        {
            "function": "search_games_by_filter",
            "success": true,
            "duration_ms": 178
        }
    ],
    "total_duration_ms": 1234
}
```

#### Prometheus 메트릭 예시

```python
# app/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# 카운터
function_call_counter = Counter(
    'function_calls_total',
    'Total function calls',
    ['function_name', 'success']
)

# 히스토그램
function_call_duration = Histogram(
    'function_call_duration_seconds',
    'Function call duration',
    ['function_name']
)

# 게이지
active_requests = Gauge(
    'active_requests',
    'Number of active requests'
)
```

---

## 트러블슈팅

### 🔴 일반적인 문제 및 해결법

#### 1. LLM이 Function Call을 하지 않음

**증상:** 쿼리가 들어와도 `detect_intent()`가 "other"를 반환

**원인:**
- CLOVA API 키 만료
- Prompt가 명확하지 않음
- LLM 모델 선택 오류

**해결:**
```python
# 1. API 키 확인
print(os.getenv("CLOVA_API_KEY"))

# 2. Prompt 개선 (한국어 명시)
intent_prompt = """당신은 게임 추천 봇입니다. 한국어로 응답하세요.
[구체적인 예시 추가]
"""

# 3. 모델 확인
# HCX-DASH-001 (권장) vs HCX-003 등
```

#### 2. Tools 함수 반환값이 빈 리스트

**증상:** `search_games_by_filter()`가 `[]` 반환

**원인:**
- 조건과 일치하는 게임 없음
- SQL 쿼리 오류
- DB 인덱스 미사용

**해결:**
```python
# 1. 데이터 확인
SELECT COUNT(*) FROM games WHERE price < 10000 AND genres_kr @> '["RPG"]';

# 2. 로그 레벨 상향
logger.debug(f"Query SQL: {query_sql}")
logger.debug(f"Params: {params}")

# 3. 인덱스 추가
CREATE INDEX idx_games_price_genres ON games(price, genres_kr);
```

#### 3. LLM 응답 생성이 느림

**증상:** `/single_chat` 응답 시간 > 5초

**원인:**
- LLM API 레이턴시 높음
- DB 쿼리 느림
- Prompt 너무 길음

**해결:**
```python
# 1. Prompt 길이 단축
# Before: 전체 게임 정보 포함
# After: 필요한 정보만 포함

# 2. 캐싱 추가
@app.get("/trending")
@cache(expire=3600)  # 1시간 캐싱
async def get_trending():
    ...

# 3. 병렬 처리
# Tools 함수들을 동시 실행
results = await asyncio.gather(
    tools.search_games_by_filter(...),
    tools.get_recommendations(...)
)
```

#### 4. 메모리 누수

**증상:** 시간 경과에 따라 메모리 사용량 증가

**원인:**
- 임베딩 모델 메모리 미정리
- LLM 인스턴스 재생성
- 캐시 정리 미비

**해결:**
```python
# 1. Lifespan 정리 확인
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    ...
    yield
    # Shutdown - 명시적 정리
    bot.cleanup()
    embeddings = None
    gc.collect()

# 2. Redis TTL 설정
redis.setex(key, ttl=3600, value=data)
```

### 🟡 성능 최적화

#### Caching 전략

```python
# app/core/cache.py

from functools import wraps
from redis import Redis

redis_client = Redis(host='localhost', port=6379)

def cache_result(ttl: int = 3600):
    """함수 결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # 캐시 확인
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # 캐시 미스 → 함수 실행
            result = await func(*args, **kwargs)

            # 결과 캐싱
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )

            return result
        return wrapper
    return decorator

# 사용
@cache_result(ttl=7200)
async def get_game_info(self, game_name: str):
    # ...
```

#### 데이터베이스 최적화

```sql
-- 필수 인덱스
CREATE INDEX idx_games_name ON games USING GIN (name);
CREATE INDEX idx_games_price_genres ON games(price, genres_kr);
CREATE INDEX idx_games_release_date ON games(release_date);
CREATE INDEX idx_embedding_similarity ON games USING ivfflat (embedding);

-- 파티셔닝 (필요시)
CREATE TABLE games_2024 PARTITION OF games
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

---

## 📚 추가 참고자료

### 문서
- [Function Call Tools 개발 메뉴얼](./FUNCTION_CALL_TOOLS_DEVELOPMENT.md)
- [LangChain Tool Documentation](https://python.langchain.com/docs/modules/tools/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)

### 코드 예시
- `backend/app/domains/chat/tools.py` - 함수 구현
- `backend/app/domains/chat/orchestrator.py` - 오케스트레이션
- `backend/test/` - 테스트 코드

### 배포 가이드
- `backend/docker-compose.yml`
- `backend/nginx/default.conf`

---

## 체크리스트: 완전한 백엔드 통합

### Phase 1: 기초 (1-2일)
- [ ] `tools.py` 구현 (Mock 버전)
- [ ] `schemas.py` 확장
- [ ] `orchestrator.py` 생성

### Phase 2: 오케스트레이션 (2-3일)
- [ ] Orchestrator 클래스 완성
- [ ] Chatbot 수정 (orchestrator 통합)
- [ ] Intent Detection LLM 프롬프트 작성

### Phase 3: 라우팅 (1-2일)
- [ ] Router 수정 (use_function_calling 파라미터)
- [ ] Lifespan 이벤트 수정
- [ ] 의존성 주입 설정

### Phase 4: 테스트 (2-3일)
- [ ] Unit 테스트 작성
- [ ] Integration 테스트 작성
- [ ] E2E 테스트 작성
- [ ] 성능 테스트

### Phase 5: 배포 (1-2일)
- [ ] 환경 변수 설정
- [ ] Docker 이미지 빌드
- [ ] Staging 배포 및 테스트
- [ ] Production 배포

### Phase 6: 모니터링 (지속)
- [ ] 로깅 수집 (ELK Stack 등)
- [ ] 메트릭 수집 (Prometheus)
- [ ] 알림 설정 (PagerDuty 등)
- [ ] 정기적 성능 리뷰

---

**최종 목표:**
LLM이 사용자 쿼리를 이해하고, 필요한 도구 함수를 선택해서 호출하고, 결과를 조합해 사용자에게 정확하고 유용한 답변을 제공하는 완전한 Function Calling 시스템 구축! 🚀
