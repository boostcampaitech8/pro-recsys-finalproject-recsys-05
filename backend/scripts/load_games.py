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

def build_game_data(row) -> dict:
    """row(dict 또는 pandas Series)에서 DB 적재용 데이터를 구성합니다."""
    return {
        "app_id": int(row.get("appid", 0)) if row.get("appid") else None,
        "name": row.get("name"),
        "price": int(row.get("price_int", 0)) if row.get("price_int") is not None else 0,
        "currency": row.get("price_currency", "KRW"),
        "release_date": str(row.get("release_date", "")),
        "short_description_kr": row.get("short_description_kr"),
        "short_description_en": row.get("short_description_en"),
        "genres_kr": row.get("genres_kr"),
        "genres_en": row.get("genres_en"),
        "header_image": row.get("header_image"),
        "screenshots": row.get("screenshots_thumbnail") or row.get("screenshots_full"),
        "movies": row.get("movies"),
        "specs": row.get("specs"),
        "supported_languages": row.get("supported_languages"),
        "tags_en": row.get("tags_en"),
        "categories": row.get("categories_kr") or row.get("categories_en"),
        "context": row.get("context") or (
            f"Game Name: {row.get('name')}\n"
            f"Genres: {', '.join(row.get('genres_en', []) or [])}\n"
            f"Tags: {', '.join(row.get('tags_en', []) or [])}\n"
            f"Description: {row.get('short_description_en') or row.get('short_description_kr') or ''}\n"
        ).strip(),
        "embedding": row.get("embedding") or row.get("vector"),
    }


async def insert_games(file_path: str, batch_size: int = 1000):
    """
    JSONL 또는 Parquet 파일을 읽어 DB에 적재합니다.
    JSONL은 메모리 절약을 위해 스트리밍 처리합니다.
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    print(f"📂 Loading data from {file_path}...")
    
    async with SessionLocal() as db:
        objects = []
        total_inserted = 0

        if file_path.endswith(".jsonl"):
            with open(file_path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f, start=1):
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                        game_data = build_game_data(row)
                        if not game_data["app_id"]:
                            continue
                        objects.append(Game(**game_data))
                    except Exception as e:
                        print(f"⚠️ Error parsing row {idx}: {e}")
                        continue

                    if len(objects) >= batch_size:
                        await save_batch(db, objects)
                        total_inserted += len(objects)
                        objects = []
                        print(f"   -> Inserted {total_inserted} records...")

        elif file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
            df = df.replace({np.nan: None})
            print(f"📊 Total records: {len(df)}")

            for idx, row in df.iterrows():
                try:
                    game_data = build_game_data(row)
                    if not game_data["app_id"]:
                        continue
                    objects.append(Game(**game_data))
                except Exception as e:
                    print(f"⚠️ Error parsing row {idx}: {e}")
                    continue

                if len(objects) >= batch_size:
                    await save_batch(db, objects)
                    total_inserted += len(objects)
                    objects = []
                    print(f"   -> Inserted {total_inserted} records...")

        else:
            print("❌ Unsupported file format. Use .jsonl or .parquet")
            return

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
