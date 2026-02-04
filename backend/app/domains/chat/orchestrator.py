import json
from enum import Enum
from typing import Optional, Tuple, List, Dict, Any
from pydantic import BaseModel, Field
from openai import AsyncOpenAI # Clova X가 OpenAI 호환이므로 이거 씁니다.
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from app.domains.chat.providers.base import LLMProvider
from app.domains.chat.tools.base import Tool
from app.domains.chat.agent.engine import AgentEngine
from app.domains.chat.interfaces import UserIntent
from app.domains.chat.tools.tools import get_game_tools
from app.core.logger import logger

template_system="""
        당신은 Steam 게임 추천 서비스의 최상위 '의도 분류기(Intent Router)'입니다.
        사용자의 입력을 분석하여 다음 중 하나의 의도로 분류하고, 반드시 JSON 형식으로 응답하세요.
        아래 schema 속성만 답변해
        
        {schema}
        """
    
# 2. 출력 스키마(Schema) 정의: LLM이 뱉어야 할 JSON 구조
class IntentAnalysis(BaseModel):
    """의도 분석 결과 스키마"""
    intent: UserIntent = Field(..., description="사용자의 주 의도")
    keywords: List[str] = Field(default_factory=list, description="핵심 키워드 추출")
    model_config = {
        "extra": "forbid"  # additionalProperties: false와 동일
    }

class SteamOrchestrator:
    def __init__(self, api_key: str, base_url: str):
        """
        Clova X (OpenAI Compatible) 클라이언트 초기화
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url # Clova X 엔드포인트
        )
        self.parser = PydanticOutputParser(pydantic_object=IntentAnalysis)
        # 라우팅을 위한 전용 시스템 프롬프트
        self.router_system_prompt  = PromptTemplate.from_template(template_system).format(schema=self._get_clova_schema())
        
    async def classify_intent(self, user_message: str) -> IntentAnalysis:
        """
        [Phase 2 핵심] 사용자의 의도를 분석하여 구조화된 데이터로 반환
        """
        try:
            response = await self.client.chat.completions.create(
                model="HCX-007", # 실제 모델명으로 변경 필요
                messages=[
                    {"role": "system", "content": self.router_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1, # 분류는 창의성이 필요 없으므로 0에 가깝게
                # 중요: JSON 모드 강제 (Clova API 스펙에 맞춰 조정 가능)
                extra_body={
                    "type": "json",
                    "schema": {
                        "type": "object",
                        "responseFormat": self._get_clova_schema()
                    }
                }
            )

            # JSON 파싱 및 Pydantic 모델로 변환 (타입 검증)
            raw_content = response.choices[0].message.content

            return self.parser.parse(raw_content)

        except Exception as e:
            # 실패 시 기본값(Chitchat)으로 Fallback 처리
            print(f"Routing Error: {e}")
            return IntentAnalysis(intent=UserIntent.CHITCHAT, keywords=["Error fallback"])

    async def handle_request(self, user_message: str, session_id: str):
        """
        메인 진입점: 의도 파악 -> 적절한 함수 실행 -> 결과 반환
        """
        # 1. 의도 파악 (Routing)
        analysis = await self.classify_intent(user_message)
        print(f"🔎 분석 결과: [{analysis.intent}] 키워드: {analysis.keywords}")

        # 2. Dispatch (분기 처리)
        if analysis.intent == UserIntent.RECOMMENDATION:
            return await self._run_recommendation_agent(analysis, session_id)
        
        elif analysis.intent == UserIntent.SEARCH:
            return await self._run_search_tool(analysis)
        
        else: # UserIntent.CHITCHAT
            return await self._run_chitchat(user_message)
        

    def _get_clova_schema(self) -> Dict[str, Any]:
        """
        Pydantic 모델(IntentAnalysis)로부터 Clova Studio용 JSON Schema를 동적으로 생성합니다.
        SSOT(Single Source of Truth) 원칙을 준수하여 유지보수성을 높입니다.
        """
        # 1. Pydantic이 제공하는 기본 메서드로 JSON Schema 추출
        schema = IntentAnalysis.model_json_schema()
        
        # 2. (선택 사항) 토큰 절약을 위해 불필요한 'title' 필드 제거
        # LLM에게는 필드명과 설명이 중요하지, 스키마 자체의 제목은 중요하지 않습니다.
        if "title" in schema:
            del schema["title"]
            
        for prop in schema.get("properties", {}).values():
            if "title" in prop:
                del prop["title"]

        # 3. Clova Studio(OpenAI Compatible)가 요구하는 최종 구조로 래핑
        return schema

    # --- 아래는 Phase 3에서 구현할 Stub 메서드들 ---

    async def _run_recommendation_agent(self, analysis: IntentAnalysis, session_id: str):
        # TODO: Phase 3 - 추천 모델 API 호출 및 결과 생성
        return f"[추천 로직 실행] 키워드 '{analysis.keywords}'를 기반으로 게임을 찾고 있습니다..."

    async def _run_search_tool(self, analysis: IntentAnalysis):
        # TODO: Phase 3 - DB/Steam API 검색 도구 호출
        return f"[검색 도구 실행] '{analysis.keywords}'에 대한 정보를 DB에서 조회합니다."

    async def _run_chitchat(self, message: str):
        # 단순 대화는 바로 응답 (혹은 가벼운 LLM 호출)
        return "저는 스팀 게임 추천 봇입니다. 게임 추천이 필요하신가요?"

class SteamBotOrchestrator:
    # 클래스 레벨 캐시 - 모든 인스턴스에서 공유
    _embedding_model_cache: Optional[HuggingFaceEmbeddings] = None

    def __init__(self, provider: LLMProvider, tool_registry: Any):
        """
        Orchestrator initialized with a Provider and ToolRegistry.
        """
        self.provider = provider
        self.registry = tool_registry
        self.parser = PydanticOutputParser(pydantic_object=IntentAnalysis)

        # 라우팅을 위한 전용 시스템 프롬프트 (Simple string format)
        self.router_system_prompt = template_system.format(schema=json.dumps(self._get_clova_schema(), indent=2, ensure_ascii=False))
        

    async def classify_intent(self, user_message: str, history: List[Dict[str, Any]] = None) -> IntentAnalysis:
        """
        [Phase 2 핵심] 사용자의 의도를 분석하여 구조화된 데이터로 반환
        """
        try:
            # 메시지 구성: System -> History -> User
            messages = [{"role": "system", "content": self.router_system_prompt}]
            
            # History 추가 (System 바로 뒤에 배치하여 문맥 제공)
            if history:
                messages.extend(history)
            
            messages.append({"role": "user", "content": user_message})

            # Note: accessing inner client for JSON mode feature -> Use provider.chat
            response = await self.provider.chat(
                model=self.provider.default_model,
                messages=messages,
                temperature=0.1,
                response_format=self._get_clova_schema()
            )

            raw_content = response.content
            return self.parser.parse(raw_content)

        except Exception as e:
            print(f"Routing Error: {e}")
            return IntentAnalysis(intent=UserIntent.CHITCHAT, reason="Error fallback")

    def _get_or_load_embedding_model(self) -> Optional[HuggingFaceEmbeddings]:
        """
        임베딩 모델을 캐시에서 가져오거나, 캐시가 비어있으면 한 번만 로드합니다.
        Docker 시작 시 로드된 모델을 재사용하는 것이 주 목적이며,
        모델이 None인 경우 한 번만 로드하여 캐시합니다.

        Returns:
            Optional[HuggingFaceEmbeddings]: 로드된 임베딩 모델 (또는 None)
        """
        # 캐시가 있으면 반환
        if SteamBotOrchestrator._embedding_model_cache is not None:
            return SteamBotOrchestrator._embedding_model_cache

        try:
            logger.info("📦 Loading embeddings model from cache (BAAI/bge-m3)...")
            model = HuggingFaceEmbeddings(
                model_name="BAAI/bge-m3",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            # 캐시에 저장
            SteamBotOrchestrator._embedding_model_cache = model
            logger.info("✅ Embeddings model cached successfully")
            return model
        except Exception as e:
            logger.error(f"❌ Failed to load embeddings model: {e}")
            return None

    async def handle_request(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        db_session: Any,
        embedding_model: Any = None,
        steam_id: Optional[str] = None
    ):
        """
        메인 진입점: 의도 파악 -> 적절한 함수 실행 -> 결과 반환

        Args:
            user_message: 사용자 메시지
            history: 대화 이력
            db_session: DB 세션 (이 요청에 대해 할당된)
            embedding_model: 임베딩 모델 (Docker 시작 시 로드된 모델, 선택)
            steam_id: Steam 사용자 ID (추천 도구용, 선택)
        """
        # 0. 임베딩 모델 결정 (우선순위: 전달받은 모델 > 캐시된 모델)
        final_embedding_model = embedding_model if embedding_model is not None else self._get_or_load_embedding_model()

        # 1. 도구 생성 (Per Request)
        current_tools = get_game_tools(db_session, redis_client=None, embeddings_model=final_embedding_model)

        # 2. 의도 파악 (History 반영)
        analysis = await self.classify_intent(user_message, history)
        logger.info(f"🔎 분석 결과: [{analysis.intent}] 키워드: {analysis.keywords}")

        # 3. Dispatch
        if analysis.intent == UserIntent.RECOMMENDATION:
            return await self._run_recommendation_agent(analysis, user_message, history, current_tools, steam_id, final_embedding_model)

        elif analysis.intent == UserIntent.SEARCH:
            return await self._run_search_tool(analysis, user_message, history, current_tools, final_embedding_model)

        else: # UserIntent.CHITCHAT
            return await self._run_chitchat(user_message)
        

    def _get_clova_schema(self) -> Dict[str, Any]:
        schema = IntentAnalysis.model_json_schema()
        if "title" in schema: del schema["title"]
        for prop in schema.get("properties", {}).values():
            if "title" in prop: del prop["title"]
        return schema


    def _filter_tools(self, intent: UserIntent, tools: Dict[str, Tool]) -> Dict[str, Tool]:
        """Filter tools by intent tag."""
        filtered = {}
        for name, tool in tools.items():
            if intent in tool.tags:
                filtered[name] = tool
        return filtered

    async def _run_recommendation_agent(self, analysis: IntentAnalysis, user_message: str, history: List[Dict[str, Any]], tools: Dict[str, Tool], steam_id: Optional[str] = None, embedding_model: Optional[Any] = None):
        """추천 에이전트 실행"""
        # 추천 태그가 있는 도구만 필터링
        rec_tools = self._filter_tools(UserIntent.RECOMMENDATION, tools)

        logger.info(f"🤖 추천 에이전트 전환 (Tools: {list(rec_tools.keys())})")

        # AgentEngine을 즉석에서 생성하여 실행 (Stateless)
        agent = AgentEngine(
            llm_provider=self.provider,
            tools=rec_tools,
            max_iterations=3,  # 추천은 빠르게
            steam_id=steam_id,
            embedding_model=embedding_model
        )
        
        # 키워드를 문맥에 포함시켜줄 수도 있음
        context_message = f"{user_message}\n(Context: User is interested in keywords: {analysis.keywords})"
        
        return await agent.run_turn(
            user_message=context_message,
            history=history
        )

    async def _run_search_tool(self, analysis: IntentAnalysis, user_message: str, history: List[Dict[str, Any]], tools: Dict[str, Tool], embedding_model: Optional[Any] = None):
        """검색 에이전트 실행"""
        # 검색 태그가 있는 도구만 필터링
        search_tools = self._filter_tools(UserIntent.SEARCH, tools)

        logger.info(f"🕵️ 검색 에이전트 전환 (Tools: {list(search_tools.keys())})")

        agent = AgentEngine(
            llm_provider=self.provider,
            tools=search_tools,
            max_iterations=3,
            embedding_model=embedding_model
        )
        
        return await agent.run_turn(
            user_message=user_message,
            history=history
        )

    async def _run_chitchat(self, message: str):
        """단순 잡담 처리 (가벼운 호출)"""
        # 도구 없이 LLM만 호출
        response = await self.provider.chat(
            messages=[{"role": "user", "content": message}],
            tools=None,
            max_tokens=200
        )
        return response.content