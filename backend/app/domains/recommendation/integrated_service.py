from app.domains.steam.service import SteamService
from app.domains.recommendation.ml_inference import GameRecommendationService, get_model_path
from app.domains.game.repository import GameRepository
from app.domains.recommendation.repository import RecommendationRepository
from app.domains.user.repository import UserRepository
from app.core.redis_cache import RecommendationCache
from typing import Dict, List, Optional
import logging
import httpx
import os
import time

logger = logging.getLogger(__name__)


class BentoMLServiceError(Exception):
    """BentoML이 HTTP 200으로 응답했지만 시맨틱 실패(status != 'success')를 보고한 경우."""


class IntegratedRecommendationService:
    """
    Steam API + EASE 모델 통합 추천 서비스

    **이 클래스의 역할**:
    모든 추천 로직을 한 곳에서 관리합니다.
    - Steam API 호출
    - EASE 모델 추론
    - DB 메타데이터 조인
    - 추천 이력 저장
    """

    def __init__(
        self,
        steam_service: SteamService,
        game_repository: GameRepository,
        recommendation_repository: RecommendationRepository,
        user_repository: UserRepository
    ):
        # 각 서비스/저장소를 주입받아 저장합니다 (의존성 주입 패턴)
        self.steam_service = steam_service
        self.game_repository = game_repository
        self.recommendation_repository = recommendation_repository
        self.user_repository = user_repository
        # 모델은 처음엔 None, 처음 사용할 때만 로드합니다 (Lazy Loading)
        self._model_service: Optional[GameRecommendationService] = None
        # Week 4: BentoML 서비스 URL (docker-compose에서 설정됨)
        self.bentoml_service_url = os.getenv(
            "BENTOML_SERVICE_URL",
            "http://bentoml:3000"
        )
        # Redis 캐시
        self.rec_cache = RecommendationCache()

    def _get_model_service(self) -> GameRecommendationService:
        """
        모델 서비스를 싱글톤으로 로드합니다.

        **싱글톤 패턴이란?**
        모델은 매우 무거운 파일(150MB)이므로, 한 번만 메모리에 로드합니다.
        매 요청마다 다시 로드하면 시간이 너무 오래 걸립니다.

        **흐름**:
        첫 번째 호출 → 모델 로드 (시간 걸림)
        두 번째 호출 → 이미 로드된 모델 재사용 (빠름)
        """
        if self._model_service is None:
            try:
                # 모델 파일 경로를 알아냅니다
                model_path = get_model_path()
                # GameRecommendationService에 경로를 주고 모델을 로드합니다
                self._model_service = GameRecommendationService(model_path)
                logger.info("EASE model loaded successfully")
            except FileNotFoundError as e:
                logger.error(f"Model file not found: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to load EASE model: {e}")
                raise
        return self._model_service

    async def recommend_from_steam(
        self,
        steamid: str,
        top_k: int = 10,
        save_history: bool = True
    ) -> Dict:
        """
        Steam ID로부터 게임 리스트를 가져와 BentoML 3-Stage 파이프라인으로 추천을 생성합니다.

        **이 메서드가 하는 일 (9단계)**:
        1. Redis 온라인 캐시 확인
        2. Steam API에서 유저 게임 데이터 가져오기
        3. 게임 ID 추출
        4. BentoML HTTP POST 호출
        5. 게임 ID 형식 변환
        6. DB에서 메타데이터 조인
        7. 점수와 메타데이터 병합
        8. Redis 온라인 캐시 저장
        9. 추천 이력 저장 (선택적)
        10. 결과 반환

        Args:
            steamid: Steam 64bit ID (예: "76561198123456789")
            top_k: 추천할 게임 개수 (기본값 10)
            save_history: DB에 추천 이력을 저장할지 여부

        Returns:
            추천 결과 딕셔너리

        Raises:
            ValueError: Steam 데이터 조회 실패 또는 게임이 없을 때
        """
        start_time = time.time()

        # ========== 1단계: Redis 온라인 캐시 확인 (Week 4) ==========
        logger.info(f"[Step 1] Checking Redis cache for {steamid}...")
        cached_result = await self.rec_cache.get_online(steamid, top_k)
        if cached_result:
            elapsed = time.time() - start_time
            logger.info(f"✓ Cache hit! ({elapsed*1000:.1f}ms)")
            return cached_result

        # ========== 2단계: Steam API에서 유저 게임 데이터 가져오기 ==========
        logger.info(f"[Step 2] Fetching Steam data for {steamid}")
        steam_data = await self.steam_service.get_user_data(
            steam_id=steamid,
            save_to_file=False  # 파일로 저장하지 않습니다
        )

        # Steam API 호출 실패 처리
        if not steam_data:
            raise ValueError(
                "Failed to fetch Steam data. "
                "Check steamid and privacy settings."
            )

        # 게임 리스트 추출
        games = steam_data.get("games", [])
        if not games:
            raise ValueError("No games found for this user.")

        # ========== 3단계: 게임 ID 추출 ==========
        # BentoML은 게임 ID를 정수로 받습니다
        played_game_ids = [int(game["appid"]) for game in games]
        logger.info(f"[Step 3] Found {len(played_game_ids)} games for user {steamid}")

        # ========== 4단계: BentoML HTTP POST 호출 (Week 4) ==========
        logger.info(f"[Step 4] Calling BentoML service...")
        model_type = "bentoml_3stage"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.bentoml_service_url}/recommend",
                    json={
                        "user_id": steamid,
                        "user_games": played_game_ids,
                        "top_k": top_k
                    }
                )
                response.raise_for_status()
                bentoml_result = response.json()

            # BentoML 응답 확인 — HTTP 200이어도 시맨틱 실패면 폴백 대상 (불변식 1)
            if bentoml_result.get("status") != "success":
                raise BentoMLServiceError(
                    f"BentoML error: {bentoml_result.get('error')}"
                )

            recommendations = bentoml_result.get("recommendations", [])
            logger.info(f"✓ BentoML returned {len(recommendations)} recommendations")

        except (httpx.HTTPError, BentoMLServiceError) as e:
            logger.error(f"BentoML call failed: {e}")
            # Fallback: BentoML이 안 되면 기존 EASE 모델 사용
            logger.warning("Falling back to EASE model...")
            try:
                model_service = self._get_model_service()
                played_game_ids_str = [str(gid) for gid in played_game_ids]
                recommendations_ease = model_service.recommend_for_new_user(
                    played_games=played_game_ids_str,
                    top_k=top_k,
                    aggregation='weighted_sum'
                )
                # EASE 출력을 BentoML 형식으로 변환
                recommendations = [
                    {
                        "rank": i+1,
                        "item_id": int(rec["item_id"]),
                        "game_id": int(rec["item_id"]),
                        "score": rec["score"],
                        "source": "ease_fallback"
                    }
                    for i, rec in enumerate(recommendations_ease)
                ]
                model_type = "ease_fallback"
                logger.info(f"✓ EASE fallback returned {len(recommendations)} recommendations")
            except Exception as fallback_error:
                logger.error(f"Both BentoML and EASE failed: {fallback_error}")
                raise

        # 추론 실패 처리
        if not recommendations:
            raise ValueError("No recommendations generated.")

        # ========== 5단계: 추천 게임 ID 추출 ==========
        # BentoML 출력: [{"item_id": 730, "score": 0.95, ...}, ...]
        recommended_app_ids = [rec["item_id"] for rec in recommendations]

        # ========== 6단계: DB에서 게임 메타데이터 조인 ==========
        logger.info(f"[Step 5] Fetching metadata for {len(recommended_app_ids)} games")
        games_from_db = await self.game_repository.get_games_by_app_ids(
            recommended_app_ids
        )

        # 조회 속도를 위해 게임을 딕셔너리로 변환합니다
        game_map = {game.app_id: game for game in games_from_db}

        # ========== 7단계: 점수와 메타데이터 병합 ==========
        result_games = []
        for rec in recommendations:
            app_id = rec["item_id"]
            game = game_map.get(app_id)

            if game:
                # DB에 있으면 메타데이터를 추가합니다
                result_games.append({
                    "app_id": game.app_id,
                    "name": game.name,                      # 게임 이름
                    # BentoML/EASE fallback 모두 "score" 키로 반환한다 ("combined_score"는 3-stage 결합 점수가 있을 때만)
                    "score": round(rec.get("combined_score", rec.get("score", 0)), 4),
                    "header_image": game.header_image,      # 썸네일 이미지
                    "short_description_kr": game.short_description_kr,  # 한국어 설명
                    "genres_kr": game.genres_kr,            # 한국어 장르들
                    "price": game.price,                    # 가격
                    "release_date": game.release_date,      # 출시 날짜
                })
            else:
                # DB에 없는 게임은 기본 정보만 반환합니다
                result_games.append({
                    "app_id": app_id,
                    "name": "Unknown Game",
                    "score": round(rec.get("combined_score", rec.get("score", 0)), 4),
                    "header_image": None,
                })

        # ========== 8단계: Redis 온라인 캐시 저장 (Week 4) ==========
        logger.info(f"[Step 6] Saving to Redis cache...")
        result_dict = {
            "steamid": steamid,
            "is_playtime_public": steam_data.get("is_playtime_public", True),
            "played_games_count": len(games),
            "recommended_games": result_games,
            "model_type": model_type,  # 폴백 발생 시 ease_fallback으로 정직 보고
            "top_k": top_k,
        }

        await self.rec_cache.set_online(steamid, top_k, result_dict)

        # ========== 9단계: 추천 이력 저장 (선택적) ==========
        if save_history:
            try:
                user = await self.user_repository.get_user_by_steam_id(steamid)
                if user:
                    await self.recommendation_repository.save_recommendation(
                        user_id=user.user_id,
                        recommended_games=result_games,
                        model_type=model_type
                    )
                    logger.info(f"✓ Saved recommendation history for user {user.user_id}")
            except Exception as e:
                logger.warning(f"Failed to save recommendation history: {e}")

        # ========== 10단계: 결과 반환 ==========
        elapsed = time.time() - start_time
        logger.info(f"✓ Recommendation complete ({elapsed*1000:.1f}ms)")
        return result_dict