import json
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# 기존 의존성 import (프로젝트 구조에 맞게 유지)
from app.core.logger import logger
# Tool Base Class import (사용자가 제공한 경로)
from app.domains.chat.tools.base import Tool
from app.domains.chat.interfaces import UserIntent
from app.domains.chat.reranker import ClovaReranker

class SearchByEmbeddingTool(Tool):
    """의미 유사도 기반 게임 검색 (RAG) 도구 - 2단계 파이프라인 (벡터 검색 → Reranking)"""

    def __init__(
        self,
        db_session: AsyncSession,
        embeddings_model=None,
        reranker: Optional[ClovaReranker] = None
    ):
        self.db = db_session
        self.embeddings = embeddings_model
        self.reranker = reranker

    @property
    def name(self) -> str:
        return "search_by_embedding"

    @property
    def description(self) -> str:
        return "사용자의 쿼리와 의미적으로 유사한 게임을 검색합니다. 장르나 키워드 매칭이 아닌, '분위기', '스타일', '느낌' 등을 검색할 때 유용합니다."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색할 게임의 특징, 분위기, 혹은 설명 (예: '로그라이크 게임', '어두운 분위기의 RPG')"
                },
                "top_k": {
                    "type": "integer",
                    "description": "반환할 결과 개수 (기본값: 3)",
                }
            },
            "required": ["query"]
        }

    @property
    def tags(self) -> list[UserIntent]:
        return [UserIntent.SEARCH]

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query")
        top_k = kwargs.get("top_k", 3)

        logger.info(f"🔍 RAG 검색: '{query}' (top_k={top_k})")

        try:
            # 1. 쿼리 임베딩 생성 (embeddings_model 사용)
            if not self.embeddings:
                logger.warning("⚠️ embeddings_model이 없어 임베딩 생성 불가")
                return json.dumps({"error": "Embeddings model is not available"}, ensure_ascii=False)

            query_embedding = self.embeddings.embed_query(query)

            # 2. Reranker 사용 여부 결정
            use_reranker = self.reranker and self.reranker.is_available()

            # Reranker 사용 시 더 많은 후보를 가져옴 (top_k * 3, 최소 20개)
            retrieval_limit = max(top_k * 3, 20) if use_reranker else min(top_k, 10)

            logger.info(f"{'🔄 2단계 파이프라인 (벡터 검색 → Reranking)' if use_reranker else '📊 단일 벡터 검색'}")

            # 3. pgvector 코사인 유사도 검색 (1단계: Retrieval)
            sql = """
            SELECT
                id, name, short_description_kr, short_description_en,
                genres_kr, price, header_image, context,
                (embedding <=> CAST(:query_embedding AS vector)) AS distance
            FROM games
            WHERE embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT :top_k
            """

            result = await self.db.execute(
                text(sql),
                {
                    "query_embedding": json.dumps(query_embedding),
                    "top_k": retrieval_limit
                }
            )
            rows = result.fetchall()

            logger.info(f"📥 벡터 검색 완료: {len(rows)}개 후보 검색됨")

            # 4. Reranker 적용 (2단계: Reranking)
            if use_reranker and len(rows) > 0:
                try:
                    # 문서 텍스트 구성 (context 우선, 없으면 description 사용)
                    documents = []
                    for row in rows:
                        doc_text = row.context or row.short_description_kr or row.short_description_en or row.name
                        documents.append(doc_text)

                    # Reranker 호출
                    reranked_results = await self.reranker.rerank(
                        query=query,
                        documents=documents,
                        top_k=top_k
                    )

                    # Reranked 결과를 게임 데이터로 매핑
                    response = []
                    for reranked_item in reranked_results:
                        original_index = reranked_item.get("index", 0)
                        rerank_score = reranked_item.get("score", 0.0)

                        if 0 <= original_index < len(rows):
                            row = rows[original_index]

                            # genres_kr 파싱
                            genres_kr = row.genres_kr
                            if isinstance(genres_kr, str):
                                genres_kr = json.loads(genres_kr)
                            elif not isinstance(genres_kr, list):
                                genres_kr = []

                            response.append({
                                "game_id": row.id,
                                "name": row.name,
                                "similarity_score": round(rerank_score, 3),  # Reranker 점수 사용
                                "short_description_kr": row.short_description_kr or "정보 없음",
                                "genres_kr": genres_kr or [],
                                "price": int(row.price) if row.price else 0,
                                "header_image": row.header_image or ""
                            })

                    logger.info(f"✅ Reranking 완료: {len(response)}개 게임 반환")
                    return json.dumps(response, ensure_ascii=False)

                except Exception as rerank_error:
                    logger.warning(f"⚠️ Reranker 실패, 벡터 검색 결과 사용: {rerank_error}")
                    # Reranker 실패 시 벡터 검색 결과로 폴백
                    use_reranker = False

            # 5. Reranker 미사용 또는 실패 시: 벡터 검색 결과 그대로 사용
            response = []
            for row in rows[:top_k]:  # top_k만큼만 반환
                # genres_kr 파싱
                genres_kr = row.genres_kr
                if isinstance(genres_kr, str):
                    genres_kr = json.loads(genres_kr)
                elif not isinstance(genres_kr, list):
                    genres_kr = []

                response.append({
                    "game_id": row.id,
                    "name": row.name,
                    "similarity_score": round(1.0 - row.distance, 3),  # 거리 -> 유사도
                    "short_description_kr": row.short_description_kr or "정보 없음",
                    "genres_kr": genres_kr or [],
                    "price": int(row.price) if row.price else 0,
                    "header_image": row.header_image or ""
                })

            logger.info(f"✅ {len(response)}개 게임 찾음")
            return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ RAG 검색 오류: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class SearchGamesByFilterTool(Tool):
    """조건 기반 게임 검색 (필터링) 도구"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @property
    def name(self) -> str:
        return "search_games_by_filter"

    @property
    def description(self) -> str:
        return "가격, 장르, 태그, 출시년도 등 구체적인 조건으로 게임을 검색합니다."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "게임 이름 검색 (선택사항)"
                },
                "max_price": {
                    "type": "integer",
                    "description": "최대 가격 (KRW) (예: '30000원 이하' -> max_price=30000)"
                },
                "min_price": {
                    "type": "integer",
                    "description": "최소 가격 (KRW) (예: '30000원 이상' -> min_price=30000)"
                },
                "genres": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "장르 목록 (AND 조건)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "태그 목록 (OR 조건)"
                },
                "release_year": {
                    "type": "integer",
                    "description": "출시 연도 (이후, >=) (예: '2023년 이후' -> 2023)"
                }
            },
            "required": []
        }

    @property
    def tags(self) -> list[UserIntent]:
        return [UserIntent.SEARCH]

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query")
        max_price = kwargs.get("max_price")
        min_price = kwargs.get("min_price")
        genres = kwargs.get("genres")
        tags = kwargs.get("tags")
        release_year = kwargs.get("release_year")

        logger.info(f"🔎 필터 검색: query={query}, price={min_price}-{max_price}, genres={genres}")
        logger.info(f"🐛 [DEBUG] genres 타입: {type(genres).__name__}, 값: {repr(genres)}")
        logger.info(f"🐛 [DEBUG] tags 타입: {type(tags).__name__}, 값: {repr(tags)}")

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
                logger.info(f"🔧 genres 타입: {type(genres)}, 값: {genres}")
                # genres가 JSON 문자열이면 파싱
                if isinstance(genres, str):
                    try:
                        genres = json.loads(genres)
                    except Exception as e:
                        logger.warning(f"⚠️ JSON 파싱 실패: {e}, 문자열 처리")
                        genres = [genres]
                # genres가 리스트가 아니면 리스트로 변환
                if not isinstance(genres, list):
                    genres = [genres]

                # 재귀적으로 모든 중첩된 리스트 펼치기
                def flatten_list(lst):
                    result = []
                    for item in lst:
                        if isinstance(item, list):
                            result.extend(flatten_list(item))
                        else:
                            result.append(item)
                    return result

                genres = flatten_list(genres)
                logger.info(f"✅ 처리된 genres: {genres}")

                for i, genre in enumerate(genres):
                    logger.info(f"🐛 [Loop {i}] genre 타입: {type(genre).__name__}, 값: {repr(genre)}")
                    if not genre or not isinstance(genre, str):
                        genre = str(genre) if genre else ""
                    logger.info(f"🐛 [Loop {i}] 변환 후 genre: {repr(genre)}, json.dumps 시도 전")
                    genre_conditions.append(f"genres_kr @> :genre_{i}")
                    try:
                        params[f"genre_{i}"] = json.dumps([genre], ensure_ascii=False)
                        logger.info(f"🐛 [Loop {i}] json.dumps 성공: {params[f'genre_{i}']}")
                    except Exception as e:
                        logger.error(f"🐛 [Loop {i}] json.dumps 실패: {type(e).__name__}: {e}, genre={repr(genre)}")
                        raise
                if genre_conditions:
                    where_clauses.append(f"({' AND '.join(genre_conditions)})")

            # 3. 태그 필터링 (OR 조건)
            tag_conditions = []
            if tags:
                logger.info(f"🔧 tags 타입: {type(tags)}, 값: {tags}")
                # tags가 JSON 문자열이면 파싱
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except Exception as e:
                        logger.warning(f"⚠️ JSON 파싱 실패: {e}, 문자열 처리")
                        tags = [tags]
                # tags가 리스트가 아니면 리스트로 변환
                if not isinstance(tags, list):
                    tags = [tags]

                # 재귀적으로 모든 중첩된 리스트 펼치기
                def flatten_list(lst):
                    result = []
                    for item in lst:
                        if isinstance(item, list):
                            result.extend(flatten_list(item))
                        else:
                            result.append(item)
                    return result

                tags = flatten_list(tags)
                logger.info(f"✅ 처리된 tags: {tags}")

                for i, tag in enumerate(tags):
                    logger.info(f"🐛 [TagLoop {i}] tag 타입: {type(tag).__name__}, 값: {repr(tag)}")
                    if not tag or not isinstance(tag, str):
                        tag = str(tag) if tag else ""
                    logger.info(f"🐛 [TagLoop {i}] 변환 후 tag: {repr(tag)}, json.dumps 시도 전")
                    tag_conditions.append(f"tags_en @> :tag_{i}")
                    try:
                        params[f"tag_{i}"] = json.dumps([tag], ensure_ascii=False)
                        logger.info(f"🐛 [TagLoop {i}] json.dumps 성공: {params[f'tag_{i}']}")
                    except Exception as e:
                        logger.error(f"🐛 [TagLoop {i}] json.dumps 실패: {type(e).__name__}: {e}, tag={repr(tag)}")
                        raise
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
            logger.info(f"🐛 SQL 실행 완료, 조회된 게임 수: {len(games) if games else 0}")

            # 5. 결과 구성
            response = []
            for idx, game in enumerate(games):
                logger.info(f"🐛 [Game {idx}] genres_kr 타입: {type(game.genres_kr).__name__}, 값: {repr(game.genres_kr)}")
                try:
                    # genres_kr이 이미 리스트면 그대로 사용, 문자열이면 json.loads
                    if isinstance(game.genres_kr, list):
                        genres_kr = game.genres_kr
                    elif game.genres_kr:
                        genres_kr = json.loads(game.genres_kr)
                    else:
                        genres_kr = []
                    logger.info(f"🐛 [Game {idx}] genres_kr 처리 완료: {genres_kr}")
                except Exception as genre_err:
                    logger.error(f"🐛 [Game {idx}] genres_kr 처리 실패: {type(genre_err).__name__}: {genre_err}")
                    genres_kr = []

                response.append({
                    "game_id": game.id,
                    "name": game.name,
                    "price": int(game.price) if game.price else 0,
                    "genres_kr": genres_kr,
                    "release_date": game.release_date or "",
                    "header_image": game.header_image or ""
                })

            logger.info(f"✅ {len(response)}개 게임 찾음, 최종 response 생성 중...")
            final_response = json.dumps(response, ensure_ascii=False)
            logger.info(f"✅ 최종 응답 생성 완료")
            return final_response

        except Exception as e:
            logger.error(f"❌ 필터 검색 오류: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

class GameInfoTool(Tool):
    """게임 상세 정보 조회 도구"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @property
    def name(self) -> str:
        return "get_game_info"

    @property
    def description(self) -> str:
        return "특정 게임의 상세 정보(가격, 장르, 사양, 스크린샷 등)를 조회합니다."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "game_name": {
                    "type": "string",
                    "description": "게임 이름"
                },
                "wanted": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["price", "details", "requirements", "media"]
                    },
                    "description": "원하는 정보 필드 (선택사항, 없으면 전체)"
                }
            },
            "required": ["game_name"]
        }

    @property
    def tags(self) -> list[UserIntent]:
        return [UserIntent.SEARCH]

    async def execute(self, **kwargs: Any) -> str:
        game_name = kwargs.get("game_name")
        wanted = kwargs.get("wanted")

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
                return json.dumps({"error": f"'{game_name}' 게임을 찾을 수 없습니다."}, ensure_ascii=False)

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
                return json.dumps(filtered, ensure_ascii=False)

            logger.info(f"✅ 게임 정보 조회 완료 (전체)")
            return json.dumps(full_response, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ 게임 정보 조회 오류: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        
class GameReviewsTool(Tool):
    """게임 리뷰 요약 조회 도구"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @property
    def name(self) -> str:
        return "get_game_reviews"

    @property
    def description(self) -> str:
        return "게임의 리뷰 요약 및 주요 태그를 조회합니다."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "game_name": {
                    "type": "string",
                    "description": "게임 이름"
                }
            },
            "required": ["game_name"]
        }

    @property
    def tags(self) -> list[UserIntent]:
        return [UserIntent.SEARCH]

    async def execute(self, **kwargs: Any) -> str:
        game_name = kwargs.get("game_name")

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
                return json.dumps({"error": f"'{game_name}' 게임을 찾을 수 없습니다."}, ensure_ascii=False)

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
            return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ 리뷰 조회 오류: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)