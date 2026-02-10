"""
게임 추천 시스템용 Function Call Tools

LLM(Clova X)이 호출할 게임 관련 함수들의 모음:
- 의미 검색 (RAG): search_by_embedding
- 필터링 검색: search_games_by_filter
- 개인화 추천: get_personalized_recommendations
- 게임 정보: get_game_info
- 게임 리뷰: get_game_reviews
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.logger import logger
from app.core.config import settings
from app.domains.recommendation.integrated_service import IntegratedRecommendationService
from app.domains.steam.service import SteamService
from app.domains.game.repository import GameRepository
from app.domains.recommendation.repository import RecommendationRepository
from app.domains.user.repository import UserRepository


class GameTools:
    """LLM이 호출할 게임 관련 도구 모음"""

    def __init__(
        self,
        db_session: AsyncSession,
        redis_client=None,
        embeddings_model=None,
        request=None,
        integrated_service: Optional[IntegratedRecommendationService] = None
    ):
        """
        초기화

        Args:
            db_session: SQLAlchemy AsyncSession (PostgreSQL 연결)
            redis_client: Redis 클라이언트 (세션 관리용, 선택사항)
            embeddings_model: 임베딩 모델 (RAG용, 선택사항)
            request: FastAPI Request 객체 (세션 추출용, 선택사항)
            integrated_service: IntegratedRecommendationService (개인화 추천용, 선택사항)
        """
        self.db = db_session
        self.redis = redis_client
        self.embeddings = embeddings_model
        self.request = request
        self.bentoml_url = settings.BENTOML_SERVICE_URL
        self.integrated_service = integrated_service

    # ============================================
    # Function 1: search_by_embedding (RAG)
    # ============================================

    async def search_by_embedding(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        의미 유사도 기반 게임 검색 (RAG)

        사용자의 쿼리와 임베딩 유사도가 높은 게임들을 반환합니다.

        Parameters:
            query (str): 검색어 (예: "로그라이크 게임")
            top_k (int): 상위 결과 개수 (기본값: 3, 최대: 10)

        Returns:
            List[Dict] with keys:
                - game_id (int): 게임 ID
                - name (str): 게임 이름
                - similarity_score (float): 유사도 점수 (0.0~1.0)
                - short_description_kr (str): 한국어 설명
                - genres_kr (List[str]): 장르
                - price (int): 가격 (KRW)
                - header_image (str): 헤더 이미지 URL

        Example:
            >>> await tools.search_by_embedding("로그라이크", top_k=3)
            [
                {
                    "game_id": 105600,
                    "name": "Hades",
                    "similarity_score": 0.92,
                    "genres_kr": ["액션", "로그라이크"],
                    "price": 19800,
                    ...
                },
                ...
            ]
        """
        logger.info(f"🔍 RAG 검색: '{query}' (top_k={top_k})")

        try:
            # 1. 쿼리 임베딩 생성 (embeddings_model 사용)
            if not self.embeddings:
                logger.warning("⚠️ embeddings_model이 없어 임베딩 생성 불가")
                return []

            query_embedding = self.embeddings.embed_query(query)

            # 2. pgvector 코사인 유사도 검색
            sql = """
            SELECT
                id, name, short_description_kr, genres_kr, price,
                header_image, (embedding <=> :query_embedding) AS distance
            FROM games
            ORDER BY distance ASC
            LIMIT :top_k
            """

            result = await self.db.execute(
                text(sql),
                {
                    "query_embedding": query_embedding,
                    "top_k": min(top_k, 10)  # 최대 10개
                }
            )
            rows = result.fetchall()

            # 3. 결과 구성 (distance를 similarity_score로 변환)
            response = []
            for row in rows:
                response.append({
                    "game_id": row.id,
                    "name": row.name,
                    "similarity_score": round(1.0 - row.distance, 3),  # 거리 -> 유사도
                    "short_description_kr": row.short_description_kr or "정보 없음",
                    "genres_kr": json.loads(row.genres_kr) if row.genres_kr else [],
                    "price": int(row.price) if row.price else 0,
                    "header_image": row.header_image or ""
                })

            logger.info(f"✅ {len(response)}개 게임 찾음")
            return response

        except Exception as e:
            logger.error(f"❌ RAG 검색 오류: {e}")
            return []

    # ============================================
    # Function 2: search_games_by_filter
    # ============================================

    async def search_games_by_filter(
        self,
        query: Optional[str] = None,
        max_price: Optional[int] = None,
        min_price: Optional[int] = None,
        genres: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        release_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        조건 기반 게임 검색 (필터링)

        Parameters:
            query (str, optional): 게임명 검색 (ILIKE)
            max_price (int, optional): 최대 가격 (KRW)
            min_price (int, optional): 최소 가격 (KRW)
            genres (List[str], optional): 장르 필터 (AND 조건)
            tags (List[str], optional): 태그 필터 (tags_en, OR 조건)
            release_year (int, optional): 출시 연도

        Returns:
            List[Dict] (최대 10개) with keys:
                - game_id (int)
                - name (str)
                - price (int)
                - genres_kr (List[str])
                - release_date (str)
                - header_image (str)

        Example:
            >>> await tools.search_games_by_filter(
            ...     max_price=10000,
            ...     genres=["RPG"],
            ...     platforms=["Windows"]
            ... )
        """
        logger.info(f"🔎 필터 검색: query={query}, price={min_price}-{max_price}, genres={genres}")

        try:
            # 1. 동적 WHERE 조건 빌더
            where_clauses = []
            params = {}

            if query:
                where_clauses.append("name ILIKE :query")
                params["query"] = f"%{query}%"

            if max_price is not None:
                where_clauses.append("price <= :max_price")
                params["max_price"] = max_price

            if min_price is not None:
                where_clauses.append("price >= :min_price")
                params["min_price"] = min_price

            if release_year is not None:
                where_clauses.append("EXTRACT(YEAR FROM TO_DATE(release_date, 'DD Mon, YYYY')) >= :release_year")
                params["release_year"] = release_year

            # 2. 장르 필터링 (JSONB @> 포함 검사)
            genre_conditions = []
            if genres:
                for i, genre in enumerate(genres):
                    genre_conditions.append(f"genres_kr @> :genre_{i}")
                    params[f"genre_{i}"] = json.dumps([genre], ensure_ascii=False)
                if genre_conditions:
                    where_clauses.append(f"({' AND '.join(genre_conditions)})")

            # 3. 태그 필터링 (OR 조건)
            tag_conditions = []
            if tags:
                for i, tag in enumerate(tags):
                    tag_conditions.append(f"tags_en @> :tag_{i}")
                    params[f"tag_{i}"] = json.dumps([tag], ensure_ascii=False)
                if tag_conditions:
                    where_clauses.append(f"({' OR '.join(tag_conditions)})")

            # 4. SQL 쿼리 빌드
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            query_sql = f"""
            SELECT
                id, name, price, genres_kr, release_date, header_image
            FROM games
            WHERE {where_sql}
            ORDER BY price ASC
            LIMIT 10
            """

            result = await self.db.execute(text(query_sql), params)
            games = result.fetchall()

            # 5. 결과 구성
            response = []
            for game in games:
                response.append({
                    "game_id": game.id,
                    "name": game.name,
                    "price": int(game.price) if game.price else 0,
                    "genres_kr": json.loads(game.genres_kr) if game.genres_kr else [],
                    "release_date": game.release_date or "",
                    "header_image": game.header_image or ""
                })

            logger.info(f"✅ {len(response)}개 게임 찾음")
            return response

        except Exception as e:
            logger.error(f"❌ 필터 검색 오류: {e}")
            return []

    # ============================================
    # Function 3: get_personalized_recommendations
    # ============================================

    async def get_personalized_recommendations(
        self,
        top_k: int = 5,
        steam_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        사용자의 플레이 이력 기반 개인화 추천 (Steam API + BentoML 통합)

        Parameters:
            top_k (int): 상위 추천 개수 (기본값: 5, 최대: 20)
            steam_id (str, optional): Steam 사용자 ID
                - None이면 Redis에서 저장된 값 사용
                - 저장된 값도 없으면 빈 리스트 반환 (LLM이 요청)

        Returns:
            List[Dict] with keys:
                - game_id (int)
                - name (str)
                - score (float): 추천 점수 (0.0~1.0)
                - reason (str): 추천 이유
                - genres (List[str])
                - header_image (str)

        Example:
            >>> await tools.get_personalized_recommendations(
            ...     top_k=5,
            ...     steam_id="76561198..."
            ... )
        """
        logger.info(f"🎯 개인화 추천: user={steam_id or 'session'}, top_k={top_k}")

        try:
            # 1. steam_id 확인
            if not steam_id and self.redis:
                steam_id = await self._get_steam_id_from_redis()

            if not steam_id:
                logger.warning("⚠️ steam_id 없음 - LLM이 입력 요청해야 함")
                return []

            # 2. IntegratedService를 통해 Steam API + BentoML 호출
            if not self.integrated_service:
                logger.error("❌ IntegratedRecommendationService가 초기화되지 않았습니다")
                return []

            result = await self.integrated_service.recommend_from_steam(
                steamid=steam_id,
                top_k=min(top_k, 20),
                save_history=False  # Function Call은 이력 저장 안 함
            )

            recommended_games = result.get("recommended_games", [])

            if not recommended_games:
                logger.warning(f"⚠️ 추천 결과 없음: {steam_id}")
                return []

            # 3. 응답 형식 변환 (app_id → game_id, genres_kr → genres)
            enriched = []
            for game in recommended_games[:top_k]:
                enriched.append({
                    "game_id": game["app_id"],
                    "name": game["name"],
                    "score": float(game.get("score", 0.0)),
                    "reason": self._generate_recommendation_reason(game),
                    "genres": game.get("genres_kr", []),
                    "header_image": game.get("header_image", "")
                })

            logger.info(f"✅ {len(enriched)}개 추천 생성 (Steam API + BentoML)")
            return enriched

        except ValueError as e:
            # Steam API 오류 (비공개 계정, 게임 없음 등)
            logger.error(f"❌ Steam API 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ 추천 오류: {e}")
            return []

    # ============================================
    # Function 4: get_game_info
    # ============================================

    async def get_game_info(
        self,
        game_name: str,
        wanted: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        특정 게임의 상세 정보 조회

        Parameters:
            game_name (str): 게임 이름
            wanted (List[str], optional): 원하는 정보 필드
                - 가능한 값: ["price", "details", "requirements", "media"]
                - None이면 전체 정보 반환

        Returns:
            Dict with keys:
                - title (str): 게임 제목
                - game_id (int)
                - price (Dict): {current, original}
                - details (Dict): {genres, release_date, description}
                - requirements (Dict): {os, min_cpu, min_ram, min_gpu}
                - media (Dict): {header_image, screenshots}

        Example:
            >>> await tools.get_game_info("Elden Ring", wanted=["price", "details"])
        """
        logger.info(f"🎮 게임 정보 조회: {game_name}")

        try:
            # 1. 게임 검색 (ILIKE)
            query = """
            SELECT
                id, name, price, short_description_kr, genres_kr,
                specs, header_image, release_date, screenshots
            FROM games
            WHERE name ILIKE :game_name
            LIMIT 1
            """

            result = await self.db.execute(
                text(query),
                {"game_name": f"%{game_name}%"}
            )
            game = result.fetchone()

            if not game:
                logger.warning(f"❌ 게임 없음: {game_name}")
                return {"error": f"'{game_name}' 게임을 찾을 수 없습니다."}

            # 2. 전체 정보 구성
            specs = json.loads(game.specs) if game.specs else {}
            screenshots = json.loads(game.screenshots) if game.screenshots else []

            full_response = {
                "title": game.name,
                "game_id": game.id,
                "price": {
                    "current": int(game.price) if game.price else 0,
                    "original": int(game.price) if game.price else 0
                },
                "details": {
                    "genres": json.loads(game.genres_kr) if game.genres_kr else [],
                    "release_date": game.release_date or "Unknown",
                    "description": game.short_description_kr or ""
                },
                "requirements": {
                    "os": specs.get("pc_min", "").split("OS:")[1].split("Processor")[0].strip() if "pc_min" in specs and "OS:" in specs.get("pc_min", "") else "Unknown",
                    "min_cpu": "정보 없음",
                    "min_ram": "정보 없음",
                    "min_gpu": "정보 없음"
                },
                "media": {
                    "header_image": game.header_image or "",
                    "screenshots": screenshots[:5] if screenshots else []
                }
            }

            # 3. wanted 필터링 적용
            if wanted:
                filtered = {"title": full_response["title"], "game_id": full_response["game_id"]}
                for field in wanted:
                    if field in full_response:
                        filtered[field] = full_response[field]
                logger.info(f"✅ 게임 정보 조회 완료 ({len(wanted)}개 필드)")
                return filtered

            logger.info(f"✅ 게임 정보 조회 완료 (전체)")
            return full_response

        except Exception as e:
            logger.error(f"❌ 게임 정보 조회 오류: {e}")
            return {"error": str(e)}

    # ============================================
    # Function 5: get_game_reviews
    # ============================================

    async def get_game_reviews(self, game_name: str) -> Dict[str, Any]:
        """
        게임의 리뷰 요약 조회

        Parameters:
            game_name (str): 게임 이름

        Returns:
            Dict with keys:
                - title (str): 게임 제목
                - keywords (List[str]): 주요 태그 (tags_en에서 추출)
                - description (str): 게임 설명

        Example:
            >>> await tools.get_game_reviews("Elden Ring")
        """
        logger.info(f"📝 리뷰 조회: {game_name}")

        try:
            # 1. 게임 검색
            query = """
            SELECT
                id, name, tags_en, short_description_kr
            FROM games
            WHERE name ILIKE :game_name
            LIMIT 1
            """

            result = await self.db.execute(
                text(query),
                {"game_name": f"%{game_name}%"}
            )
            game = result.fetchone()

            if not game:
                logger.warning(f"❌ 게임 없음: {game_name}")
                return {"error": f"'{game_name}' 게임을 찾을 수 없습니다."}

            # 2. 태그 추출 (상위 5개)
            tags = json.loads(game.tags_en) if game.tags_en else []
            keywords = tags[:5] if tags else []

            # 3. 결과 구성
            response = {
                "title": game.name,
                "keywords": keywords,
                "description": game.short_description_kr or "정보 없음"
            }

            logger.info(f"✅ 리뷰 조회 완료")
            return response

        except Exception as e:
            logger.error(f"❌ 리뷰 조회 오류: {e}")
            return {"error": str(e)}

    # ============================================
    # Helper Methods
    # ============================================

    def _generate_recommendation_reason(self, game: Dict[str, Any]) -> str:
        """추천 점수 기반 추천 이유 생성"""
        score = game.get("score", 0.0)
        if score >= 0.9:
            return "당신의 플레이 패턴과 매우 잘 맞습니다"
        elif score >= 0.7:
            return "당신이 좋아할 만한 게임입니다"
        else:
            return "맞춤 추천"

    async def _get_steam_id_from_redis(self) -> Optional[str]:
        """Redis에서 저장된 steam_id 조회"""
        try:
            if not self.redis:
                return None

            # 실제로는 Request 세션에서 user_id를 가져와서 키 구성
            # 여기서는 간단히 구현
            steam_id = await self.redis.get("steam_id")
            return steam_id.decode() if steam_id else None

        except Exception as e:
            logger.error(f"⚠️ Redis 조회 오류: {e}")
            return None

    async def _save_steam_id_to_redis(self, steam_id: str) -> bool:
        """Redis에 steam_id 저장 (TTL: 30분)"""
        try:
            if not self.redis:
                return False

            # TTL: 30분 (1800초)
            await self.redis.setex("steam_id", 1800, steam_id)
            logger.info(f"✅ steam_id 저장: {steam_id}")
            return True

        except Exception as e:
            logger.error(f"⚠️ Redis 저장 오류: {e}")
            return False

    async def _get_game_by_id(self, game_id: int) -> Optional[Dict]:
        """ID로 게임 정보 조회 (보강용)"""
        try:
            query = """
            SELECT id, name, genres_kr, header_image
            FROM games
            WHERE id = :id
            LIMIT 1
            """

            result = await self.db.execute(
                text(query),
                {"id": game_id}
            )
            game = result.fetchone()

            if game:
                return {
                    "id": game.id,
                    "name": game.name,
                    "genres": json.loads(game.genres_kr) if game.genres_kr else [],
                    "header_image": game.header_image or ""
                }
            return None

        except Exception as e:
            logger.error(f"⚠️ 게임 조회 오류: {e}")
            return None



# ============================================
# Dependency Injection Helper
# ============================================

def get_game_tools(
    db_session: AsyncSession,
    redis_client=None,
    embeddings_model=None,
    request=None
) -> GameTools:
    """
    FastAPI 의존성 주입용 헬퍼 함수

    IntegratedRecommendationService를 초기화하여 GameTools에 주입합니다.
    이를 통해 개인화 추천이 Steam API + BentoML 통합을 사용합니다.

    Example:
        @router.post("/chat")
        async def chat(
            request: ChatRequest,
            tools: GameTools = Depends(get_game_tools)
        ):
            ...
    """
    # IntegratedRecommendationService 초기화
    try:
        steam_service = SteamService()
        game_repository = GameRepository(db_session)
        recommendation_repository = RecommendationRepository(db_session)
        user_repository = UserRepository(db_session)

        integrated_service = IntegratedRecommendationService(
            steam_service=steam_service,
            game_repository=game_repository,
            recommendation_repository=recommendation_repository,
            user_repository=user_repository
        )
    except Exception as e:
        logger.warning(f"⚠️ IntegratedRecommendationService 초기화 실패: {e}")
        integrated_service = None

    return GameTools(
        db_session=db_session,
        redis_client=redis_client,
        embeddings_model=embeddings_model,
        request=request,
        integrated_service=integrated_service
    )
