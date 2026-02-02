import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.database import SessionLocal
from app.domains.chat import services

async def main():
    print("🧪 Testing Multi-turn Chat System...")
    
    async with SessionLocal() as db:
        # 1. Create Conversation
        print("1. Creating Conversation...")
        conv = await services.create_conversation(db, user_id=1, title="Test Chat")
        print(f"✅ Created specific Conversation ID: {conv.conversation_id}")
        
        # 2. Add User Message
        print("2. Adding User Message...")
        msg1 = await services.add_message(db, conv.conversation_id, "user", "Hello, recommend me a game.")
        print(f"✅ User Message Saved: {msg1.content}")
        
        # 3. Add AI Message
        print("3. Adding AI Message...")
        msg2 = await services.add_message(db, conv.conversation_id, "assistant", "Sure! How about Hades?")
        print(f"✅ AI Message Saved: {msg2.content}")
        
        # 4. Get History
        print("4. Retrieving History...")
        history = await services.get_chat_history(db, conv.conversation_id)
        print(f"✅ History Length: {len(history)}")
        for m in history:
            print(f"   - [{m.role}] {m.content}")
            
        assert len(history) == 2
        
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
