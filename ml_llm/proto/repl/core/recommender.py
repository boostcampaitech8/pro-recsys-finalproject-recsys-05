import os
import streamlit as st
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class SteamRecommender:
    """
    Model Layer: Handles Logic, Data Access, and RAG Pipeline.
    Refactored for granular control and logging.
    """
    def __init__(self):
        self.vectorstore = None
        self.llm = None
        self.retriever = None
        self.prompt_template = None
        self.output_parser = StrOutputParser()

    @st.cache_resource
    def load_resources(_self, temperature: float, num_ctx: int):
        """
        Load heavy resources (Embeddings, Vector DB, LLM).
        Cached by Streamlit to prevent reloading on interaction.
        """
        try:
            print("\n" + "="*70)
            print("🔧 INITIALIZING LOCAL RESOURCES (MVC: Model)")
            print("="*70 + "\n")
            
            # 1. Initialize Embeddings
            print("📦 Loading embeddings model...")
            embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-m3",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            print("✅ Embeddings loaded\n")
            
            # 2. Load PostgreSQL (PGVector)
            # Use environment variable for DB host (default to localhost for local dev)
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_user = os.getenv("DB_USER", "postgres")
            db_password = os.getenv("DB_PASSWORD", "postgres") # Default password for local/docker
            db_name = os.getenv("DB_NAME", "postgres")
            
            db_connection = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            collection_name = "steam_games_bge_m3"
            
            print(f"💾 Connecting to PostgreSQL [{db_connection}]...")
            try:
                vectorstore = PGVector(
                    embeddings=embeddings,
                    collection_name=collection_name,
                    connection=db_connection,
                    use_jsonb=True,
                )
                print("✅ PostgreSQL Connected\n")
            except Exception as e:
                print(f"❌ Failed to connect to PostgreSQL: {e}")
                st.error(f"PostgreSQL 연결 실패: {e}")
                return None, None
            
            # 3. Setup Local LLM (Llama 3.2 3B via Ollama)
            # Use environment variable for Ollama host (important for Docker)
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            print(f"🤖 Initializing Llama 3.2 3B (Local) at {ollama_base_url}...")
            
            llm = ChatOllama(
                base_url=ollama_base_url,
                model="llama3.2:3b",
                temperature=temperature,
                num_ctx=num_ctx,
                num_gpu=1,
                num_thread=6,
            )
            
            print("✅ Local LLM initialized")
            print("="*70 + "\n")
            
            return vectorstore, llm
            
        except Exception as e:
            print(f"\n❌ Error during initialization: {e}\n")
            return None, None

    def initialize(self, temperature: float, num_ctx: int) -> bool:
        """Initialize resources and setup components."""
        self.vectorstore, self.llm = self.load_resources(temperature, num_ctx)
        
        if not self.vectorstore or not self.llm:
            return False

        # Setup Retriever
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        
        # Setup Prompt Template
        self.setup_prompt()
        return True

    def setup_prompt(self):
        """Define Prompts."""
        template = """당신은 Steam 게임 추천 전문가입니다.
사용자의 의도를 파악하고 다음 컨텍스트에 기반하여 게임을 추천해주세요.

컨텍스트:
{context}

질문: {question}

규칙:
- 사용자가 게임 추천을 요청하면, 구체적인 게임 이름, 설명, 그리고 왜 적합한지 이유를 제시하세요.
- 컨텍스트에 가격 정보가 있다면 언급하세요.
- 컨텍스트에 정보가 없는 경우, "제 데이터베이스에 해당 게임에 대한 정보가 없습니다."라고 말하되 최대한 도움이 되도록 하세요.
- 컨텍스트에 없는 게임을 만들어내지 마세요.
- 간결하고 친근하게 답변하세요.
- 반드시 한국어로 답변하세요.

답변:"""
        self.prompt_template = ChatPromptTemplate.from_template(template)

    def generate_response_with_details(self, user_query: str):
        """
        Execute RAG steps manually to capture intermediate data and granular timings.
        Returns: (response_text, retrieved_docs, formatted_prompt, app_metrics)
        """
        import time
        if not self.llm or not self.vectorstore:
            raise ValueError("Resources not initialized.")

        app_metrics = {}

        # 1. Embedding
        start_embed = time.time()
        # retriever uses the same embeddings key
        query_vector = self.vectorstore.embeddings.embed_query(user_query)
        end_embed = time.time()
        app_metrics["embedding_time"] = end_embed - start_embed

        # 2. Retrieval
        start_retrieval = time.time()
        # Equivalent to search_kwargs={"k": 5} defined in initialize
        retrieved_docs = self.vectorstore.similarity_search_by_vector(query_vector, k=5)
        end_retrieval = time.time()
        app_metrics["retrieval_time"] = end_retrieval - start_retrieval
        
        context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)

        # 3. Prompt Formatting
        prompt_value = self.prompt_template.invoke({
            "context": context_text,
            "question": user_query
        })
        formatted_prompt = prompt_value.to_string()

        # 4. Generate
        start_gen = time.time()
        response_msg = self.llm.invoke(prompt_value)
        response_text = self.output_parser.invoke(response_msg)
        end_gen = time.time()
        app_metrics["generation_time"] = end_gen - start_gen

        return response_text, retrieved_docs, formatted_prompt, app_metrics
