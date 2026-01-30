import asyncio
import sys
import os
import random
import numpy as np # Added numpy import

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal # Changed from get_db to SessionLocal
from app.domains.game.repository import GameRepository
from app.core.config import settings # Added settings import

# -----------------------------------------------------------------------------
# Test Vector Search
# -----------------------------------------------------------------------------
async def test_vector_search(): # Renamed function
    print("🚀 Vector Search Test Start")
    
    async with SessionLocal() as db: # Changed DB connection method
        repo = GameRepository(db)
        
        # 1. Create a random vector (768 dim)
        # 실제로는 ML 모델 출력값이 들어옴
        # Using config dimension to match schema
        dummy_vector = np.random.rand(settings.EMBEDDING_DIMENSION).tolist() # Modified dummy vector generation
        print(f"✅ Generated Dummy Vector (Dim: {len(dummy_vector)})")

        # 2. Test 1: Simple Search
        print("\n🔍 Test 1: Simple Vector Search (Top 3)")
        try:
            results = await repo.search_by_embedding(vector=dummy_vector, top_k=3)
            for game in results:
                print(f"   - [{game.app_id}] {game.name} (Price: {game.price})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            # pgvector extension이 없거나 데이터가 없으면 에러 발생 가능

        # 3. Test 2: Filter Search (Price + Genre)
        print("\n🔍 Test 2: Filter Search (Price <= 10000 OR Genre='Action')")
        try:
            results = await repo.search_by_embedding(
                vector=dummy_vector, 
                top_k=3,
                max_price=10000,
                genres=["Action"]
            )
            for game in results:
                print(f"   - [{game.app_id}] {game.name} | Price: {game.price} | Genres: {game.genres_kr}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_vector_search())
