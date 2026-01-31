import os
import time
import traceback
from typing import Optional, Tuple, List, Dict, Any

from app.core.logger import logger

from sqlalchemy.ext.asyncio import AsyncEngine
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

class chatbot:
    def __init__(self):
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        self.vectorstore: Optional[PGVector] = None
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
        clova_base_url: str = "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions",
        model_name: str = "HCX-DASH-001",
        temperature: float = 0.5,     # 추천 시스템은 할루시네이션 방지를 위해 낮게 설정 권장
        max_tokens: int = 1024,
        collection_name: str = "steam_games_bge_m3",
        top_k: int = 3
    ) -> bool:
        """
        리소스를 초기화합니다. NCP 인증 헤더 처리가 포함되어 있습니다.
        """
        if self._initialized:
            logger.info("⚠️ Chatbot service already initialized")
            return True

        try:
            logger.info(f"🚀 Initializing SteamChatbotService ({model_name})...")
            
            # 1. Embeddings (CPU 모드 명시, 비용 절감 및 호환성)
            logger.info("📦 Loading embeddings model (BAAI/bge-m3)...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-m3",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

            # 2. PGVector 연결
            logger.info(f"💾 Connecting to PGVector (collection: {collection_name})...")
            self.vectorstore = PGVector(
                embeddings=self.embeddings,
                collection_name=collection_name,
                connection=engine,
                use_jsonb=True,
                async_mode=True,
            )

            # 3. Retriever 설정
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": top_k}
            )

            # 4. CLOVA Studio LLM 초기화 (OpenAI 호환 모드 + 헤더 주입)
            logger.info(f"🤖 Connecting to CLOVA Studio ({model_name})...")
            
            self.llm = ChatOpenAI(
                base_url=clova_base_url,
                api_key=clova_api_key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                model_kwargs={
                    "top_p": 0.8,
                    "repetition_penalty": 1.2,
                }
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
            return True

        except Exception as e:
            logger.info(f"\n❌ Chatbot initialization failed: {e}")
            traceback.print_exc()
            await self.cleanup()
            return False

    def _setup_prompt(self):
        """
        시스템 프롬프트 강화: RAG 기반 추천의 정확도를 높이기 위한 지침 포함
        """
        template = """당신은 Steam 게임 추천 전문가 '스팀 봇'입니다. 
다음 [게임 데이터]를 바탕으로 사용자 질문에 대해 친절하고 정확하게 답변하세요.

[게임 데이터]
{context}

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
        user_query: str
    ) -> Tuple[str, List[Document], str, Dict[str, float]]:
        """
        RAG 파이프라인 실행 및 상세 정보 반환 (디버깅/모니터링 용)
        """
        if not self.is_ready():
            return "챗봇이 준비되지 않았습니다.", [], "", {}

        metrics = {}
        start_total = time.time()

        try:
            # 1. 문서 검색
            start_retr = time.time()
            retrieved_docs = await self.vectorstore.asimilarity_search(
                user_query, 
                k=self.config.get("top_k", 3)
            )
            metrics["retrieval_time"] = time.time() - start_retr

            # 2. 프롬프트 구성
            context_text = "\n\n".join([d.page_content for d in retrieved_docs])
            chain_input = {"context": context_text, "question": user_query}
            
            formatted_prompt_val = self.prompt_template.invoke(chain_input)
            formatted_prompt = formatted_prompt_val.to_string()

            # 3. LLM 생성
            start_gen = time.time()
            response_msg = await self.llm.ainvoke(formatted_prompt_val)
            response_text = self.output_parser.invoke(response_msg)
            metrics["generation_time"] = time.time() - start_gen

            metrics["total_time"] = time.time() - start_total
            return response_text, retrieved_docs, formatted_prompt, metrics

        except Exception as e:
            logger.info(f"❌ Generation error: {e}")
            return f"오류가 발생했습니다: {str(e)}", [], "", {"error": 1.0}

    async def generate_response(self, user_query: str) -> str:
        resp, _, _, _ = await self.generate_response_with_details(user_query)
        return resp
    
    async def cleanup(self):
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