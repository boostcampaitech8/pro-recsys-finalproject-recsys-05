import streamlit as st

class GameRecommenderUI:
    """
    View Layer: Handles Streamlit UI components and display logic.
    """
    def __init__(self):
        pass

    def setup_page(self):
        """Configure page settings and display header."""
        if not st.session_state.get('page_configured'):
            st.set_page_config(
                page_title="Steam Game Recommender",
                page_icon="🎮",
                layout="wide"
            )
            st.session_state['page_configured'] = True

        st.title("🎮 Steam 게임 추천 챗봇")
        st.markdown("""
            **Llama 3.2 3B (로컬)** & **PostgreSQL (PGVector)** 기반  
            Steam 게임에 대해 물어보세요! 설명, 태그, 가격 기반으로 추천해드립니다.
        """)

    def render_sidebar(self):
        """Render sidebar settings and return configuration."""
        with st.sidebar:
            st.header("설정")     
            return 0.0, 4096

    def display_chat_history(self):
        """Render chat messages from history."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # If there's debug info attached to the message, display it
                if "debug_info" in message:
                    self.display_debug_info(message["debug_info"])

    def get_user_input(self):
        """Capture user input via chat widget."""
        return st.chat_input("어떤 게임을 찾고 계신가요?")

    def display_user_message(self, message: str):
        """Display user message immediately."""
        st.chat_message("user").markdown(message)
        st.session_state.messages.append({"role": "user", "content": message})

    def display_assistant_response(self, response: str, duration: float, call_count: int, debug_data: dict = None):
        """Display assistant message, performance metrics, and debug info."""
        with st.chat_message("assistant"):
            st.markdown(response)
            
            # Performance Info
            with st.expander("⚡ 성능 정보"):
                st.write(f"**응답 시간**: {duration:.2f}초")
                st.write(f"**처리 속도**: ~{len(response.split()) / duration if duration > 0 else 0:.1f} 단어/초")
                st.write(f"**총 호출 횟수**: {call_count}")
                st.write(f"**모델**: llama3.2:3b (로컬)")
            
            # Debug Info
            if debug_data:
                self.display_debug_info(debug_data)

        # Save to history with debug info
        msg_entry = {
            "role": "assistant", 
            "content": response,
            "debug_info": debug_data
        }
        st.session_state.messages.append(msg_entry)

    def display_debug_info(self, debug_data: dict):
        """Render debug expander with context and prompt."""
        with st.expander("🛠️ 시스템 로직 확인 (Data & Prompt)"):
            st.subheader("1. 검색된 컨텍스트 (Retrieved Docs)")
            if debug_data.get("context_docs"):
                for i, doc in enumerate(debug_data["context_docs"]):
                    st.text_area(f"Doc {i+1}", doc.page_content, height=200, key=f"doc_{st.session_state.llm_call_count}_{i}")
            else:
                st.warning("검색된 문서가 없습니다.")

            st.subheader("2. 최종 프롬프트 (Final Prompt)")
            st.code(debug_data.get("full_prompt", ""), language="text")

    def show_error(self, message: str):
        """Display error message."""
        st.error(message)

    def show_ollama_help(self):
        """Display Ollama troubleshooting help."""
        st.info("**문제 해결:**")
        st.markdown("""
        1. **Ollama 설치**: https://ollama.com/download 에서 다운로드
        2. **Ollama 시작**: 터미널에서 `ollama serve` 실행
        3. **모델 다운로드**: `ollama pull llama3.2:3b` 실행
        4. **DB 확인**: PostgreSQL 컨테이너가 실행 중인지 확인
        """)
