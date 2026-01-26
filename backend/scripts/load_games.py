import asyncio
import json
import os
import sys
import argparse
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from collections import defaultdict

# backend 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # backend/
sys.path.append(parent_dir)

from app.core.database import SessionLocal, engine
from app.core.database import Base # 테이블 생성을 위해 필요
from app.domains.game.models import Game
from app.domains.game.schemas import GameDetailResponse # 검증용

async def init_db():
    """DB 테이블 생성 (없으면 생성)"""
    async with engine.begin() as conn:
        # pgvector 확장 설치
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # 모든 테이블 생성
        await conn.run_sync(Base.metadata.create_all)
    print("✅ DB Schema Initialized.")

async def insert_games(file_path: str, batch_size: int = 1000):
    """
    JSONL 또는 Parquet 파일을 읽어 DB에 적재합니다.
    데이터 포맷이 다양할 수 있으므로 판다스로 로드 후 dict로 변환하여 처리합니다.
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    print(f"📂 Loading data from {file_path}...")
    
    # 확장자에 따른 로드
    if file_path.endswith(".jsonl"):
        df = pd.read_json(file_path, lines=True)
    elif file_path.endswith(".parquet"):
        df = pd.read_parquet(file_path)
    else:
        print("❌ Unsupported file format. Use .jsonl or .parquet")
        return

    # NaN 처리 (None으로 변환)
    df = df.replace({np.nan: None})
    
    print(f"📊 Total records: {len(df)}")

    async with SessionLocal() as db:
        objects = []
        total_inserted = 0
        
        for idx, row in df.iterrows():
            # JSON 포맷이 복잡하므로 필요한 필드를 추출하여 매핑
            # row 접근 시 .get() 사용 불가 (Series 객체임) -> row['field'] 사용하되 예외 처리 필요
            
            try:
                # 1. 기본 정보 매핑
                game_data = {
                    "app_id": int(row.get("appid", 0)) if row.get("appid") else None,
                    "name": row.get("name"),
                    "price": int(row.get("price_int", 0)) if row.get("price_int") is not None else 0,
                    "currency": row.get("price_currency", "KRW"),
                    "release_date": str(row.get("release_date", "")),
                    
                    # 2. 로컬라이제이션
                    "short_description_kr": row.get("short_description_kr"),
                    "short_description_en": row.get("short_description_en"),
                    "genres_kr": row.get("genres_kr"), # JSONB - List 그대로 저장
                    "genres_en": row.get("genres_en"),
                    
                    # 3. 미디어 및 메타데이터
                    "header_image": row.get("header_image"),
                    "screenshots": row.get("screenshots_thumbnail") or row.get("screenshots_full"), # 썸네일 우선
                    "movies": row.get("movies"),
                    "specs": row.get("specs"),
                    "supported_languages": row.get("supported_languages"),
                    "tags_en": row.get("tags_en"),
                    "categories": row.get("categories_kr") or row.get("categories_en"), # 한글 카테고리 우선
                    
                    # 4. Context for RAG (종합 텍스트 정보)
                    # 데이터에 명시적인 context 컬럼이 없으면, 주요 정보를 조합해 생성
                    "context": row.get("context") or (
                        f"Game Name: {row.get('name')}\n"
                        f"Genres: {', '.join(row.get('genres_en', []) or [])}\n"
                        f"Tags: {', '.join(row.get('tags_en', []) or [])}\n"
                        f"Description: {row.get('short_description_en') or row.get('short_description_kr') or ''}\n"
                    ).strip(),

                    # 5. 임베딩 (데이터에 이미 vector가 있다면)
                    "embedding": row.get("embedding") # 없으면 None
                }

                # 필수 필드 체크
                if not game_data["app_id"]:
                    continue

                # Game 객체 생성
                game = Game(**game_data)
                objects.append(game)
                
            except Exception as e:
                print(f"⚠️ Error parsing row {idx}: {e}")
                continue

            # Batch Insert
            if len(objects) >= batch_size:
                await save_batch(db, objects)
                total_inserted += len(objects)
                objects = []
                print(f"   -> Inserted {total_inserted} records...")
            
        # 남은 데이터 처리
        if objects:
            await save_batch(db, objects)
            total_inserted += len(objects)
        
        print(f"✅ Data Load Complete! Total inserted: {total_inserted}")

async def save_batch(db: AsyncSession, objects: list):
    try:
        # bulk_save_objects는 async session에서 직접 지원 안될 수 있음 -> add_all 사용
        db.add_all(objects)
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"❌ Batch Insert Error: {e}")
        # 중복 에러 등 발생 시 개별 처리 로직이 필요할 수 있음 (일단 건너뜀)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser(description="Load Game Data to DB")
    parser.add_argument("file", help="Path to data file (.jsonl or .parquet)")
    parser.add_argument("--reset", action="store_true", help="Reset DB table before loading")
    args = parser.parse_args()

    async def main():
        if args.reset:
            async with engine.begin() as conn:
                print("🗑️ Resetting 'games' table...")
                await conn.execute(text("DROP TABLE IF EXISTS games CASCADE"))
        
        await init_db()
        await insert_games(args.file)
    
    asyncio.run(main())
