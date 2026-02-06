import sys
import os
import asyncio

# Add backend directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import get_db

async def load_data():
    """
    ETL Process Skeleton
    1. Extract: Load Raw Data
    2. Transform: Vectorize using shared config
    3. Load: Insert into PGVector
    """
    print(f"🚀 ETL Start with Model: {settings.EMBEDDING_MODEL_NAME} (Dim: {settings.EMBEDDING_DIMENSION})")

    # 1. Load Data (Mock for now, or file)
    # For MVP, let's look for a parquet file or use dummy data if none found
    # In real scenario, we might read from 'data/games_metadata.parquet'
    
    # Mock Data for Verification matching the Template Logic
    dummy_games = [
        {
            "app_id": 10,
            "name": "Counter-Strike",
            "short_description": "Play the world's number 1 online action game.",
            "genres": ["Action"],
            "tags": ["FPS", "Shooter", "Multiplayer"],
            "developers": ["Valve"],
            "categories": ["Multi-player", "PvP"],
            "supported_languages": ["English", "French", "German"],
            "full_audio_languages": ["English"]
        }
    ]
    
    # 2. Initialize Model
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    
    # 3. Transform & Load
    for game in dummy_games:
        # Replicating ml_llm/doc_template/default.j2 logic
        # Title: {{ title }}
        # Developer: {{ dev_list | join(', ') }}
        # Description: {{ desc }} ...
        
        devs = ", ".join(game.get("developers", []))
        genres = ", ".join(game.get("genres", []))
        cats = ", ".join(game.get("categories", []))
        langs = ", ".join(game.get("supported_languages", []))
        audio = ", ".join(game.get("full_audio_languages", []))
        
        context_text = f"""Title: {game['name']}
Developer: {devs}

Description:
{game['short_description']}

Key Attributes:
- Genres: {genres}
- Categories: {cats}
- Interface & Subtitles Languages: {langs}
- Full Audio Languages: {audio}"""

        # Generate Embedding
        embedding = model.encode(context_text).tolist()
        
        if len(embedding) != settings.EMBEDDING_DIMENSION:
            print(f"❌ Dimension Mismatch! Config: {settings.EMBEDDING_DIMENSION}, Model: {len(embedding)}")
            return

        print(f"✅ Embedded '{game['name']}' -> Vector({len(embedding)})")
        # print(f"Context:\n{context_text}")
        
    print("✅ ETL Simulation Complete. (DB Insert skipped in this step to prevent mock data pollution)")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(load_data())
