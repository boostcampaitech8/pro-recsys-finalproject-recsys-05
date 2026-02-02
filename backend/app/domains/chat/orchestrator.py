import json
from enum import Enum
from typing import Optional, Tuple, List, Dict, Any
from pydantic import BaseModel, Field
from openai import AsyncOpenAI # Clova X가 OpenAI 호환이므로 이거 씁니다.
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

template_system="""
        당신은 Steam 게임 추천 서비스의 최상위 '의도 분류기(Intent Router)'입니다.
        사용자의 입력을 분석하여 다음 중 하나의 의도로 분류하고, 반드시 JSON 형식으로 응답하세요.
        아래 schema 속성만 답변해
        
        {schema}
        """

# 1. 의도(Intent) 정의: 라우터가 분류할 목적지
class UserIntent(str, Enum):
    RECOMMENDATION = "recommendation" # 추천 요청 ("할만한 게임 추천해줘")
    SEARCH = "search"                 # 단순 정보/검색 ("배그 가격 얼마야?")
    CHITCHAT = "chitchat"             # 일상 대화 ("안녕", "고마워")
    
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
            return IntentAnalysis(intent=UserIntent.CHITCHAT, reason="Error fallback")

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