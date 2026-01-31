import pytest
import os
import json
import tempfile
from app.domains.game.repository import GameRepository
from app.domains.game.service import GameService
from app.core.logger import logger
from scripts.load_games import insert_games

@pytest.mark.asyncio
async def test_game_flow(db):
    """
    Game 도메인 검증:
    1. 샘플 데이터 생성 및 load_games.py 실행
    2. 데이터 조회 (Steam ID, 전체/장르별)
    3. 상세 조회 로직 테스트
    """
    repo = GameRepository(db)
    service = GameService(repo)
    
    logger.info("[테스트 시작] Game Flow 검증 시작")

    # 1. 샘플 데이터 생성 (Temporary JSONL)
    sample_game = {
        "appid": 999999,
        "name": "Test Game For Flow",
        "price_int": 10000,
        "price_currency": "KRW",
        "release_date": "2024-01-01",
        "short_description_kr": "테스트 게임입니다.",
        "short_description_en": "This is a test game.",
        "genres_kr": ["액션", "인디"],
        "genres_en": ["Action", "Indie"],
        "tags_en": ["FPS", "Multiplayer"],
        "header_image": "http://example.com/image.jpg",
        "supported_languages": "English, Korean",
        # 필요한 다른 필드들도 load_games.py 로직에 맞춰 추가 가능
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp_file:
        json.dump(sample_game, tmp_file)
        tmp_file_path = tmp_file.name
    
    try:
        # load_games 실행하여 DB 적재
        logger.info(f"0. 데이터 적재 시도: {tmp_file_path}")
        await insert_games(tmp_file_path, batch_size=1)
        logger.info("   -> 데이터 적재 완료")

        # 2. 데이터 조회 테스트
        all_games = await repo.get_all_games(limit=1)
        assert all_games, "데이터 적재 후에도 DB가 비어있습니다."
        
        target_game = None
        for g in all_games:
            if g.app_id == sample_game["appid"]:
                target_game = g
                break
        
        # 만약 limit=1이라서 안 보일 수도 있으니 직접 조회 시도
        if not target_game:
            target_game = await repo.get_game_by_id(sample_game["appid"])

        assert target_game is not None, f"적재한 게임(ID: {sample_game['appid']})을 찾을 수 없습니다."
        logger.info(f"1. 게임 조회 성공: {target_game.name}")

        # 3. 상세 조회 테스트
        detail = await service.get_game_detail(target_game.app_id)
        assert detail is not None
        assert detail.name == sample_game["name"]
        logger.info("   -> 상세 조회 성공")

    finally:
        # 테스트 종료 후 임시 파일 삭제
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
