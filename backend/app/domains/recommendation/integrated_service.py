from app.domains.steam.service import SteamService
from app.services.ml_inference import GameRecommendationService, get_model_path
from app.domains.game.repository import GameRepository
from app.domains.recommendation.repository import RecommendationRepository
from app.domains.user.repository import UserRepository
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


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
        Steam ID로부터 게임 리스트를 가져와 EASE로 추천을 생성합니다.

        **이 메서드가 하는 일 (8단계)**:
        1. Steam API에서 유저 게임 데이터 가져오기
        2. 게임 ID 추출
        3. EASE 모델 추론
        4. 게임 ID 형식 변환
        5. DB에서 메타데이터 조인
        6. 점수와 메타데이터 병합
        7. 추천 이력 저장 (선택적)
        8. 결과 반환

        Args:
            steamid: Steam 64bit ID (예: "76561198123456789")
            top_k: 추천할 게임 개수 (기본값 10)
            save_history: DB에 추천 이력을 저장할지 여부

        Returns:
            추천 결과 딕셔너리

        Raises:
            ValueError: Steam 데이터 조회 실패 또는 게임이 없을 때
            FileNotFoundError: 모델 파일을 찾을 수 없을 때
        """
        # ========== 1단계: Steam API에서 유저 게임 데이터 가져오기 ==========
        logger.info(f"Fetching Steam data for {steamid}")
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

        # ========== 2단계: 게임 ID 추출 (정수 → 문자열) ==========
        # EASE 모델은 게임 ID를 문자열로 받기 때문에 변환합니다
        # 예: [730, 570, 440] → ["730", "570", "440"]
        played_game_ids = [str(game["appid"]) for game in games]
        logger.info(f"Found {len(played_game_ids)} games for user {steamid}")

        # ========== 3단계: EASE 모델 추론 ==========
        logger.info("Running EASE inference...")
        try:
            model_service = self._get_model_service()
            # EASE 모델에 유저가 플레이한 게임을 입력하면
            # 추천할 게임 리스트를 받습니다
            recommendations = model_service.recommend_for_new_user(
                played_games=played_game_ids,      # 유저가 플레이한 게임들
                top_k=top_k,                        # 몇 개를 추천할지
                aggregation='weighted_sum'          # 추천 점수 계산 방식
            )
        except Exception as e:
            logger.error(f"EASE inference failed: {e}")
            raise

        # 추론 실패 처리
        if not recommendations:
            raise ValueError(
                "No recommendations generated. "
                "User's games might not be in the model."
            )

        # ========== 4단계: item_id 문자열 → app_id 정수 변환 ==========
        # EASE 모델의 출력: {"item_id": "730", "score": 0.85}
        # 우리가 원하는 형식: {"app_id": 730, "score": 0.85}
        recommended_app_ids = [int(rec["item_id"]) for rec in recommendations]

        # ========== 5단계: DB에서 게임 메타데이터 조인 ==========
        # 추천된 게임들의 상세 정보 (이름, 이미지, 장르 등)를 DB에서 조회합니다
        logger.info(f"Fetching metadata for {len(recommended_app_ids)} games")
        games_from_db = await self.game_repository.get_games_by_app_ids(
            recommended_app_ids
        )

        # 조회 속도를 위해 게임을 딕셔너리로 변환합니다
        # {"730": Game(...), "570": Game(...), ...}
        game_map = {game.app_id: game for game in games_from_db}

        # ========== 6단계: 점수와 메타데이터 병합 ==========
        result_games = []
        for rec in recommendations:
            app_id = int(rec["item_id"])
            # 딕셔너리에서 게임을 찾습니다
            game = game_map.get(app_id)

            if game:
                # DB에 있으면 메타데이터를 추가합니다
                result_games.append({
                    "app_id": game.app_id,
                    "name": game.name,                      # 게임 이름
                    "score": round(rec["score"], 4),        # EASE 추천 점수 (4자리 반올림)
                    "header_image": game.header_image,      # 썸네일 이미지
                    "short_description_kr": game.short_description_kr,  # 한국어 설명
                    "genres_kr": game.genres_kr,            # 한국어 장르들
                    "price": game.price,                    # 가격
                    "release_date": game.release_date,      # 출시 날짜
                })
            else:
                # DB에 없는 게임은 기본 정보만 반환합니다
                # (매우 드문 경우: 최신 게임이거나 DB에 데이터가 없음)
                result_games.append({
                    "app_id": app_id,
                    "name": "Unknown Game",
                    "score": round(rec["score"], 4),
                    "header_image": None,
                })

        # ========== 7단계: 추천 이력 저장 (선택적) ==========
        # 나중에 사용자가 어떤 게임을 추천받았는지 추적하기 위해 저장합니다
        if save_history:
            try:
                # 유저 정보를 조회합니다
                user = await self.user_repository.get_user_by_steam_id(steamid)
                if user:
                    # 추천 결과를 DB에 저장합니다
                    await self.recommendation_repository.save_recommendation(
                        user_id=user.user_id,
                        recommended_games=result_games,
                        model_type="ease_cold_start"  # EASE 콜드스타트 모델 사용
                    )
                    logger.info(
                        f"Saved recommendation history for user {user.user_id}"
                    )
            except Exception as e:
                # 이력 저장 실패해도 추천은 진행합니다
                logger.warning(f"Failed to save recommendation history: {e}")

        # ========== 8단계: 결과 반환 ==========
        return {
            "steamid": steamid,
            "is_playtime_public": steam_data.get("is_playtime_public", True),
            "played_games_count": len(games),           # 유저가 플레이한 게임 수
            "recommended_games": result_games,          # 추천 게임 리스트
            "model_type": "ease_cold_start",            # 어떤 모델을 사용했는지
            "top_k": top_k,                             # 몇 개를 추천했는지
        }