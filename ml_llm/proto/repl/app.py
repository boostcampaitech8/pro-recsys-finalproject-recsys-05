import streamlit as st
from ui.interface import GameRecommenderUI
from core.recommender import SteamRecommender
import time

def main():
    # 1. Initialize View & Model
    ui = GameRecommenderUI()
    recommender = SteamRecommender()

    # 2. Setup Page (Calls st.set_page_config internally)
    ui.setup_page()
    
    # 3. Render Sidebar & Get Settings
    temperature, num_ctx = ui.render_sidebar()

    # 4. Initialize Resources (DB connection, LLM)
    # This might take a moment, so we do it after rendering basic UI structure
    with st.spinner("시스템 초기화 중... (DB 연결 및 모델 로드)"):
        success = recommender.initialize(temperature, num_ctx)
    
    if not success:
        ui.show_error("시스템 초기화에 실패했습니다. 로그를 확인해주세요.")
        st.stop()

    # 5. Display Chat Interface
    ui.display_chat_history()

    # 6. Handle User Input
    if user_input := ui.get_user_input():
        # Display user message
        ui.display_user_message(user_input)

        # Generate Response
        start_time = time.time()
        
        try:
            with st.spinner("답변 생성 중..."):
                response_text, retrieved_docs, formatted_prompt = recommender.generate_response_with_details(user_input)
            
            duration = time.time() - start_time
            
            # Update counters
            if "llm_call_count" not in st.session_state:
                st.session_state.llm_call_count = 0
            st.session_state.llm_call_count += 1
            
            # Display assistant response
            debug_data = {
                "context_docs": retrieved_docs,
                "full_prompt": formatted_prompt
            }
            ui.display_assistant_response(response_text, duration, st.session_state.llm_call_count, debug_data)
            
        except Exception as e:
            ui.show_error(f"오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()
