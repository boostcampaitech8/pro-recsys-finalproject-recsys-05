import pytest
from app.domains.chat.repository import ChatRepository
from app.domains.chat import services

@pytest.mark.asyncio
async def test_multiturn_chat_history_db(db):
    """
    Test Multi-turn Chat History using DB repository independently of API.
    Simulates:
    1. Create Conversation
    2. Add User Message
    3. Add AI Message
    4. Retrieve History and Verify Order
    """
    repo = ChatRepository(db)

    # 1. Create Conversation
    print("\n[Test] Creating Conversation...")
    conv = await repo.create_conversation(user_id=1)
    assert conv.conversation_id is not None
    print(f"[Test] Conversation Created: {conv.conversation_id}")

    # 2. Simulate Turn 1 (User -> AI)
    print("[Test] Turn 1: User 'Hello' -> AI 'Hi'")
    await repo.add_message(conv.conversation_id, "user", "Hello")
    await repo.add_message(conv.conversation_id, "assistant", "Hi there!")

    # 3. Simulate Turn 2 (User -> AI)
    print("[Test] Turn 2: User 'Rec game' -> AI 'Hades'")
    await repo.add_message(conv.conversation_id, "user", "Recommend me a game")
    # For simulation, we assume AI processed it
    await repo.add_message(conv.conversation_id, "assistant", "I recommend Hades.")

    # 4. Verify History Retrieval (Service Logic)
    print("[Test] Retrieving Recent Messages (Limit 5)...")
    history = await services.get_recent_messages(db, conv.conversation_id, limit=5)
    
    # Check length
    assert len(history) == 4
    
    # Check Order (Oldest first)
    assert history[0].role == "user" and history[0].content == "Hello"
    assert history[1].role == "assistant" and history[1].content == "Hi there!"
    assert history[2].role == "user" and history[2].content == "Recommend me a game"
    assert history[3].role == "assistant" and history[3].content == "I recommend Hades."
    
    print("[Test] History Order Verified OK")
    
    # 5. Verify String Formatting
    print("[Test] Verifying Format...")
    formatted_text = services.format_history(history)
    print(f"[Test] Formatted History:\n---\n{formatted_text}\n---")
    
    expected_fragment = "User: Hello\nAssistant: Hi there!"
    assert expected_fragment in formatted_text
    
    print("[Test] Formatting Verified OK")
