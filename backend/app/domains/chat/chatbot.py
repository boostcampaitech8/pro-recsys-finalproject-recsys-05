import os
import time
import json
import traceback
from typing import Optional, Tuple, List, Dict, Any

from app.core.logger import logger

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class chatbot:
    def __init__(self):
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        # self.vectorstore: Optional[PGVector] = None
        self.engine = None
        self.llm: Optional[ChatOpenAI] = None
        self.retriever = None
        self.prompt_template: Optional[ChatPromptTemplate] = None
        self.output_parser = StrOutputParser()
        self.config: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(
        self,
        engine: AsyncEngine,
        clova_api_key: str,          # Studio API Key
        clova_base_url: str = "https://clovastudio.stream.ntruss.com/v1/openai/",
        model_name: str = "HCX-DASH-001",
        temperature: float = 0.5,     # 추천 시스템은 할루시네이션 방지를 위해 낮게 설정 권장
        max_tokens: int = 1024,
        # collection_name: str = "steam_games_bge_m3",
        top_k: int = 3
    ):
        """
        리소스를 초기화합니다. NCP 인증 헤더 처리가 포함되어 있습니다.
        """
        if self._initialized:
            logger.info("⚠️ Chatbot service already initialized")
            return

        try:
            logger.info(f"🚀 Initializing SteamChatbotService ({model_name})...")
            
            # 1. Embeddings (CPU 모드 명시, 비용 절감 및 호환성)
            logger.info("📦 Loading embeddings model (BAAI/bge-m3)...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-m3",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

            self.engine = engine
            
            # 4. CLOVA Studio LLM 초기화 (OpenAI 호환 모드 + 헤더 주입)
            logger.info(f"🤖 Connecting to CLOVA Studio ({model_name})...")
            
            self.llm = ChatOpenAI(
                base_url=clova_base_url,
                api_key=clova_api_key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # 5. Prompt Template 설정
            self._setup_prompt()

            # 설정 저장
            self.config = {
                "model": model_name,
                "temperature": temperature,
                "top_k": top_k,
                "base_url": clova_base_url
            }

            self._initialized = True
            logger.info("✅ Chatbot initialization complete!")
            return 

        except Exception as e:
            logger.info(f"\n❌ Chatbot initialization failed: {e}")
            traceback.print_exc()
            self.cleanup()
            raise

    def _setup_prompt(self):
        """
        시스템 프롬프트 강화: RAG 기반 추천의 정확도를 높이기 위한 지침 포함
        """
        template = """당신은 Steam 게임 추천 전문가 '스팀 봇'입니다. 
다음 [게임 데이터]와 [이전 대화]를 바탕으로 사용자 질문에 대해 친절하고 정확하게 답변하세요.

[게임 데이터]
{context}

[이전 대화]
{history}

[답변 가이드라인]
1. 반드시 위 [게임 데이터]에 있는 정보만 사용하여 답변하세요. 없는 게임을 지어내지 마세요.
2. 추천할 때는 **게임 이름**, **장르**, **가격**, **추천 이유**를 명확히 포함하세요.
3. [게임 데이터]에 정보가 부족하다면 "죄송합니다, 해당 조건에 맞는 게임 정보를 찾지 못했습니다."라고 솔직하게 말하세요.
4. 한국어로 답변하고, '~해요', '~입니다' 체를 사용하여 정중하게 대답하세요.

사용자 질문: {question}
답변:"""
        self.prompt_template = ChatPromptTemplate.from_template(template)
        
    async def generate_response_with_details(
        self,
        user_query: str,
        history_text: str = ""
    ) -> Tuple[str, List[Dict[str, Any]], str, Dict[str, float]]:
        """
        RAG 파이프라인 실행 및 상세 정보 반환 (디버깅/모니터링 용)
        
        Returns:
            Tuple[str, List[Dict], str, Dict]:
                - response_text: LLM 생성 응답
                - retrieved_docs: 검색된 문서 리스트 (dict 형태)
                - formatted_prompt: LLM에 전달된 최종 프롬프트 (DEBUG_MODE용)
                - metrics: 성능 메트릭 딕셔너리
        """
        if not self.is_ready():
            return "챗봇이 준비되지 않았습니다.", [], "", {}

        metrics = {}
        retrieved_games = None
        
        search_sql = text("""
        SELECT 
            name,
            context,
            genres_kr::text as genres,
            price,
            header_image,
            release_date,
            1 - (embedding <=> (:query_embedding)::vector) as similarity
        FROM games
        WHERE embedding IS NOT NULL
        -- 여기에 추후 가격이나 장르 필터링 조건 추가 (예: AND price = 0)
        ORDER BY embedding <=> (:query_embedding)::vector
        LIMIT :top_k
    """)
        
        start_total = time.time()
        
        try:
            # 1. 쿼리 임베딩 생성
            start_embed = time.time()
            query_embedding = self.embeddings.embed_query(user_query)
            metrics["embedding_time"] = time.time() - start_embed

            # 2. 문서 검색
            start_retr = time.time()
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    search_sql,
                    {
                        "query_embedding": json.dumps(query_embedding), # 드라이버에 따라 list 그대로 전달 가능 여부 확인 필요
                        "top_k": self.config.get("top_k", 3)
                    }
                )
                retrieved_games = result.fetchall()
            metrics["retrieval_time"] = time.time() - start_retr
            
            if not retrieved_games:
                metrics["total_time"] = time.time() - start_total
                logger.warning(f"No games retrieved for query: {user_query}")
                return "\uac80\uc0c9 \uacb0\uacfc\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.", [], "", metrics
            
            # 3. ?? ??? dict ??? ?? (API ???)
            retrieved_docs = []
            for row in retrieved_games:
                retrieved_docs.append({
                    "name": row.name,
                    "genres": row.genres,
                    "price": float(row.price) if row.price else 0.0,
                    "similarity": float(row.similarity),
                    "header_image": row.header_image,
                    "release_date": str(row.release_date) if row.release_date else None
                })

            # 4. 프롬프트 구성
            context_text = "\n\n".join([row.context for row in retrieved_games])

            # History Injection
            chain_input = {
                "context": context_text, 
                "question": user_query,
                "history": history_text
            }
            
            formatted_prompt_val = self.prompt_template.invoke(chain_input)
            formatted_prompt = formatted_prompt_val.to_string()

            # 5. LLM 생성
            start_gen = time.time()
            response_msg = await self.llm.ainvoke(formatted_prompt_val)
            response_text = self.output_parser.invoke(response_msg)
            metrics["generation_time"] = time.time() - start_gen

            metrics["total_time"] = time.time() - start_total
            
            return response_text, retrieved_docs, formatted_prompt, metrics

        except Exception as e:
            logger.error(f"❌ Generation error: {e}")
            metrics["total_time"] = time.time() - start_total
            return f"오류가 발생했습니다: {str(e)}", [], "", metrics

    async def generate_response(self, user_query: str) -> str:
        resp, _, _, _ = await self.generate_response_with_details(user_query)
        return resp
    
    def cleanup(self):
        logger.info("🧹 Cleaning up chatbot resources...")
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self._initialized = False

    def is_ready(self) -> bool:
        return self._initialized and self.llm is not None
    
# 싱글톤 인스턴스
chatbot_instance: Optional["chatbot"] = None

# 의존성 주입 도우미
def get_chatbot() -> chatbot:
    global chatbot_instance
    if chatbot_instance is None:
        chatbot_instance = chatbot()
    # 주의: 여기서 initialize를 호출하지 않습니다. lifespan에서 해야 합니다.
    return chatbot_instance

def reset_chatbot() -> None:
    """싱글톤 인스턴스를 완전히 초기화합니다. (테스트/재시작 시 사용)"""
    global chatbot_instance
    chatbot_instance = None
