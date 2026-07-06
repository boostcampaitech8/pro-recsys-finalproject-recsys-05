import json
import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from app.domains.chat.providers.base import LLMProvider
from app.domains.chat.tools.base import Tool
from app.domains.chat.agent.engine import AgentEngine
from app.domains.chat.interfaces import UserIntent
from app.domains.chat.tools.tools import get_game_tools
from app.core.logger import logger


# Prompt Templates
PROMPT_RECOMMENDATION = """당신은 스팀 게임 전문 큐레이터 '스팀봇'입니다.
사용자에게 딱 맞는 게임을 찾아 추천해주는 것이 목표입니다.

[지침]
1. 친근하고 열정적인 톤으로 대화하세요 (이모지 적절히 사용).
2. 추천할 때는 반드시 **'추천 이유'**와 **'게임의 핵심 매력'**을 강조하세요.
3. 가격 정보가 있다면 원화(KRW)로 알려주세요.
4. 사용자가 모호하게 말하면 구체적인 취향(장르, 난이도 등)을 물어보세요.
5. markdown을 사용해서 답변하지마세요.
"""

PROMPT_SEARCH = """당신은 게임 정보 검색 요원입니다.
사용자가 요청한 게임에 대한 사실 정보를 정확하고 간결하게 전달하세요.

[지침]
1. 건조하고 객관적인 톤을 유지하세요.
2. 불필요한 미사여구를 빼고 핵심 정보(가격, 출시일, 평가, 사양 등) 위주로 요약하세요.
3. 정보가 없으면 솔직하게 모른다고 답하세요.
4. markdown을 사용해서 답변하지마세요.
"""

PROMPT_CHICHAT = """당신은 스팀봇(Steambot)의 친절한 대화 파트너입니다.

목표:
사용자의 일상적인 대화(잡담)에 자연스럽게 호응해주면서, 최종적으로는 스팀 게임 추천이나 검색 기능을 사용하도록 부드럽게 유도하세요.

지침:
1. 친절하고 재치 있는 어조를 유지하세요. 딱딱한 말투보다는 부드러운 구어체를 사용하세요.
2. 사용자의 기분이나 상황에 공감해주되, 이를 게임 플레이 동기로 연결해 보세요. (예: "피곤하실 땐 힐링 게임이 최고죠!")
3. 노골적으로 게임을 강요하지 말고, 호기심을 자극하세요.
4. 직접 게임 데이터를 검색하거나 가격을 알려주지 마세요. (이 모드는 잡담 전용입니다)
5. 사용자가 구체적인 게임 정보를 묻거나 추천을 원하면, "그럼 본격적으로 게임을 찾아볼까요?"라고 말하며 대화를 마무리하세요.
6. markdown을 사용해서 답변하지마세요
"""

template_system="""
당신은 Steam 게임 추천 서비스의 '의도 분류기(Intent Router)'입니다.

**역할:** 사용자 메시지를 분석하여 3가지 의도 중 하나로 정확하게 분류

**의도 정의:**
1. RECOMMENDATION: 사용자의 게임 기록을 기반으로 개인화된 추천을 요청하는 경우
   - 핵심: "나에게", "내가", "내 취향", "내 플레이 스타일", "내 게임처럼", "나를 위해"
   - 예: "나에게 맞는 게임 추천해", "내가 좋아할 만한 게임", "나의 게임처럼 비슷한 게임"

2. SEARCH: 일반적인 게임 정보 조회 또는 일반 추천 요청
   - 개인화되지 않은 추천: "액션 게임 뭐 있어?", "인기 게임 추천해", "요즘 핫한 게임"
   - 게임 정보 조회: "가격이 뭐야?", "평점이", "지원해?", "출시됐어?", "그 게임 리뷰 어떻게 돼?"

3. CHITCHAT: 게임과 무관한 일상 대화
   - 예: "안녕", "감사합니다", "오늘 날씨 좋네" (게임 관련 없음)

**분류 예시:**
- 사용자: "나에게 맞는 게임 추천해줘"
  의도: RECOMMENDATION
  키워드: ["개인화 추천"]

- 사용자: "내가 좋아할 만한 액션 게임 있어?"
  의도: RECOMMENDATION
  키워드: ["액션"]

- 사용자: "요즘 핫한 재미있는 게임 뭐 있어?"
  의도: SEARCH
  키워드: ["최근", "재미있는"]

- 사용자: "사이버펑크 2077 한글 지원돼?"
  의도: SEARCH
  키워드: ["사이버펑크 2077", "한글 지원"]

- 사용자: "좋은 하루 보내!"
  의도: CHITCHAT
  키워드: []

**경계 케이스 (핵심 - "나/내"가 있는가?):**
- "배그 같은 게임 추천해" → SEARCH (일반 게임 추천, "나에게"가 없음)
- "내가 해본 배그처럼 재미있는 게임 있어?" → RECOMMENDATION (개인화 추천, "내가"가 있음)
- "최근 인기 게임이 뭐야?" → SEARCH (일반 정보)
- "내 취향에 맞는 게임 추천해줄래?" → RECOMMENDATION (명시적 개인화)
- "액션 게임 추천해" → SEARCH (장르별 일반 추천)
- "나의 플레이 스타일과 비슷한 게임" → RECOMMENDATION (개인화)

**주의사항:**
- 🔑 RECOMMENDATION의 핵심: "나에게", "내가", "내 취향", "내 플레이 스타일" 등 **개인화 단서**가 명시적으로 있어야 함
- "추천해"만 있고 "나에게"가 없으면 → SEARCH (일반 추천)
- 게임의 속성, 가격, 평점, 지원 여부를 묻거나 일반적인 게임 추천은 → SEARCH
- 게임 관련 내용이 없는 순수 대화는 → CHITCHAT
- keywords는 사용자가 언급한 게임명, 장르, 특징, 속성만 추출 (최대 3개)

반드시 JSON 형식으로만 응답하세요:
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

class SteamBotOrchestrator:
    # 클래스 레벨 캐시 - 모든 인스턴스에서 공유
    _embedding_model_cache: Optional[HuggingFaceEmbeddings] = None

    def __init__(self, provider: LLMProvider):
        """
        Orchestrator initialized with an LLM Provider.
        도구는 요청마다 get_game_tools()로 생성된다 (DB 세션 의존).
        """
        self.provider = provider
        self.parser = PydanticOutputParser(pydantic_object=IntentAnalysis)

        # 라우팅을 위한 전용 시스템 프롬프트 (Simple string format)
        self.router_system_prompt = template_system.format(schema=json.dumps(self._get_clova_schema(), indent=2, ensure_ascii=False))

    def _normalize_intent(self, intent_value: Any) -> Optional[UserIntent]:
        """Normalize diverse intent labels into UserIntent."""
        if isinstance(intent_value, UserIntent):
            return intent_value
        if not isinstance(intent_value, str):
            return None

        key = intent_value.strip().lower()
        aliases = {
            "recommendation": UserIntent.RECOMMENDATION,
            "recommend": UserIntent.RECOMMENDATION,
            "rec": UserIntent.RECOMMENDATION,
            "search": UserIntent.SEARCH,
            "find": UserIntent.SEARCH,
            "lookup": UserIntent.SEARCH,
            "info": UserIntent.SEARCH,
            "chitchat": UserIntent.CHITCHAT,
            "chat": UserIntent.CHITCHAT,
            "smalltalk": UserIntent.CHITCHAT,
            "small_talk": UserIntent.CHITCHAT,
            "small-talk": UserIntent.CHITCHAT,
        }
        return aliases.get(key)

    def _parse_intent_payload(self, payload: Any) -> Optional[IntentAnalysis]:
        """Build IntentAnalysis from parsed JSON-like payload."""
        if not isinstance(payload, dict):
            return None

        normalized_intent = self._normalize_intent(payload.get("intent"))
        if normalized_intent is None:
            return None

        raw_keywords = payload.get("keywords", [])
        if isinstance(raw_keywords, str):
            candidates = [raw_keywords]
        elif isinstance(raw_keywords, list):
            candidates = raw_keywords
        else:
            candidates = []

        keywords: List[str] = []
        for item in candidates:
            if not isinstance(item, str):
                continue
            value = item.strip()
            if value and value not in keywords:
                keywords.append(value)
            if len(keywords) >= 5:
                break

        return IntentAnalysis(intent=normalized_intent, keywords=keywords)

    def _parse_intent_with_recovery(self, raw_content: str) -> Optional[IntentAnalysis]:
        """Parse model output with fallbacks when strict JSON is broken."""
        if not raw_content:
            return None

        try:
            return self.parser.parse(raw_content)
        except Exception:
            pass

        json_candidates: List[str] = []

        for match in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", raw_content, flags=re.IGNORECASE | re.DOTALL):
            json_candidates.append(match)

        first_brace = raw_content.find("{")
        last_brace = raw_content.rfind("}")
        if 0 <= first_brace < last_brace:
            json_candidates.append(raw_content[first_brace:last_brace + 1])

        json_candidates.extend(re.findall(r"\{.*?\}", raw_content, flags=re.DOTALL))

        seen = set()
        for candidate in json_candidates:
            normalized = candidate.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)

            try:
                payload = json.loads(normalized)
            except Exception:
                continue

            parsed = self._parse_intent_payload(payload)
            if parsed is not None:
                return parsed

        return None

    def _extract_keywords(self, user_message: str) -> List[str]:
        tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", user_message)
        stop_words = {
            "게임", "추천", "추천해", "추천해줘", "추천해주세요", "검색", "검색해줘",
            "좀", "그냥", "그리고", "근데", "요즘", "최근", "지금", "할만한",
            "찾아줘", "찾아봐", "알려줘", "정보", "있어", "해주세요", "가능",
        }
        keywords: List[str] = []
        for token in tokens:
            if token in stop_words:
                continue
            if token not in keywords:
                keywords.append(token)
            if len(keywords) >= 3:
                break
        return keywords

    def _heuristic_intent_analysis(self, user_message: str) -> IntentAnalysis:
        text = user_message.lower()

        personal_markers = [
            "나에게", "내게", "내가", "나랑", "나의",
            "내 취향", "내스타일", "내 스타일", "내 플레이", "내가 해본",
            "for me", "my taste", "my style", "for my",
        ]
        search_markers = [
            "검색", "찾아", "알려", "가격", "평점", "리뷰", "출시", "지원",
            "정보", "뭐야", "어때", "compare", "difference", "vs",
        ]

        has_personal = any(marker in text for marker in personal_markers)
        has_search = any(marker in text for marker in search_markers)
        has_recommend = ("추천" in text) or ("recommend" in text)
        has_game_context = ("게임" in text) or ("game" in text)

        if has_personal:
            return IntentAnalysis(intent=UserIntent.RECOMMENDATION, keywords=self._extract_keywords(user_message))
        if has_search or has_recommend or has_game_context:
            return IntentAnalysis(intent=UserIntent.SEARCH, keywords=self._extract_keywords(user_message))
        return IntentAnalysis(intent=UserIntent.CHITCHAT, keywords=[])

    def _apply_intent_guardrail(self, analysis: IntentAnalysis, user_message: str) -> IntentAnalysis:
        heuristic = self._heuristic_intent_analysis(user_message)

        if analysis.intent == UserIntent.CHITCHAT and heuristic.intent != UserIntent.CHITCHAT:
            return heuristic

        if analysis.intent == UserIntent.SEARCH and heuristic.intent == UserIntent.RECOMMENDATION:
            return heuristic

        if analysis.intent == UserIntent.RECOMMENDATION and heuristic.intent == UserIntent.SEARCH:
            text = user_message.lower()
            has_personal = any(
                marker in text
                for marker in ["나에게", "내게", "내가", "나랑", "나의", "내 취향", "내 스타일", "내 플레이"]
            )
            if not has_personal:
                return heuristic

        return analysis

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
            parsed = self._parse_intent_with_recovery(raw_content)
            if parsed is not None:
                return self._apply_intent_guardrail(parsed, user_message)

            logger.warning("Routing parser failed; applying heuristic fallback. raw_content=%s", raw_content[:400])
            return self._heuristic_intent_analysis(user_message)

        except Exception as e:
            logger.warning("Routing Error: %s", e)
            return self._heuristic_intent_analysis(user_message)

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
            return await self._run_chitchat(user_message, history)
        

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
            max_iterations=3, # 추천은 빠르게
            steam_id=steam_id,
            embedding_model=embedding_model,
            system_prompt=PROMPT_RECOMMENDATION,
            llm_config={"temperature": 0.7} # 창의적인 추천
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
            embedding_model=embedding_model,
            system_prompt=PROMPT_SEARCH,
            llm_config={"temperature": 0.1} # 정확한 정보 전달
        )
        
        return await agent.run_turn(
            user_message=user_message,
            history=history
        )

    async def _run_chitchat(self, message: str, history: List[Dict[str, Any]]):
        """단순 잡담 처리 (가벼운 호출)"""
        # History 반영
        messages = []
        messages.append({"role": "system", "content": PROMPT_CHICHAT})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        # 도구 없이 LLM만 호출
        response = await self.provider.chat(
            messages=messages,
            tools=None,
            max_tokens=100
        )
        return response.content
