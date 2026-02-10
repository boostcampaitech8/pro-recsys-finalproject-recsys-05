
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domains.chat import services
from app.domains.chat.schemas import MessageResponse

@pytest.mark.asyncio
async def test_manual_user_flow_logic(db):
    """
    Test the User-ID based chat flow logic manually.
    Run with: RUN_MANUAL_USER_FLOW=1 pytest backend/test/domains/chat/manual_user_flow_test.py
    """
    if os.getenv("RUN_MANUAL_USER_FLOW") != "1":
        pytest.skip("Set RUN_MANUAL_USER_FLOW=1 to run this manual test.")

    # Mock Chatbot
    mock_bot = MagicMock()
    mock_bot.is_ready.return_value = True
    
    # Mock generate_response_with_details response
    # Return: response_text, retrieved_docs, formatted_prompt, metrics
    mock_bot.generate_response_with_details = AsyncMock(return_value=(
        "Hello from Mock Bot", 
        [], # empty docs
        "prompt", 
        {"time": 0.1}
    ))

    print("\n--- [Step 1] Guest User Request (First Visit) ---")
    # 1. user_id=None Request
    ai_msg, ret_docs, debug, conv_id, new_user_id = await services.process_chat_by_user(
        db=db,
        bot=mock_bot,
        user_id=None,
        user_content="Hello, I am new here."
    )

    print(f"Created User ID: {new_user_id}")
    print(f"Created Conversation ID: {conv_id}")
    print(f"AI Response: {ai_msg.content}")

    assert new_user_id is not None
    assert conv_id is not None
    assert ai_msg.content == "Hello from Mock Bot"

    print("\n--- [Step 2] Returning User Request (Second Visit) ---")
    # 2. user_id=new_user_id Request
    ai_msg_2, ret_docs_2, debug_2, conv_id_2, user_id_2 = await services.process_chat_by_user(
        db=db,
        bot=mock_bot,
        user_id=new_user_id,
        user_content="I am back."
    )

    print(f"Returned User ID: {user_id_2}")
    print(f"Returned Conversation ID: {conv_id_2}")
    
    # Should stay in the same user session
    assert user_id_2 == new_user_id
    # Should reuse the conversation (logic: get latest)
    assert conv_id_2 == conv_id 

    print("--- [Success] User Flow Verified ---")
