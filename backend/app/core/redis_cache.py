"""
Redis 캐싱 서비스
하이브리드 구조: 온라인 캐시 + 배치 캐시
"""

import json
import logging
from typing import Optional, Dict, Any, List
from .redis import redis_client

logger = logging.getLogger(__name__)


class RecommendationCache:
    """추천 캐시 관리 클래스"""

    # Redis 키 접두사
    ONLINE_CACHE_PREFIX = "rec:online"
    BATCH_CACHE_PREFIX = "rec:batch"

    # TTL 설정 (초)
    ONLINE_TTL = 3600  # 1시간
    BATCH_TTL = 86400  # 24시간 (배치 작업이 일일 1회이므로)

    @staticmethod
    def _get_online_key(steam_id: str, top_k: int = 10) -> str:
        """온라인 캐시 키 생성"""
        return f"{RecommendationCache.ONLINE_CACHE_PREFIX}:{steam_id}:{top_k}"

    @staticmethod
    def _get_batch_key(steam_id: str, top_k: int = 10) -> str:
        """배치 캐시 키 생성"""
        return f"{RecommendationCache.BATCH_CACHE_PREFIX}:{steam_id}:{top_k}"

    # =========================================================================
    # Week 4에서 사용할 메서드: 온라인 캐싱만
    # =========================================================================

    @staticmethod
    async def get_online(steam_id: str, top_k: int = 10) -> Optional[Dict[str, Any]]:
        """
        Redis에서 온라인 캐시 조회

        Args:
            steam_id: 사용자 Steam ID
            top_k: 추천 게임 개수

        Returns:
            캐시된 추천 결과 또는 None
        """
        try:
            key = RecommendationCache._get_online_key(steam_id, top_k)
            cached_data = await redis_client.get(key)

            if cached_data:
                logger.info(f"✓ Online cache hit: {steam_id}")
                return json.loads(cached_data)

            logger.info(f"⚠️ Online cache miss: {steam_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Redis 조회 실패: {e}")
            return None

    @staticmethod
    async def set_online(
        steam_id: str,
        top_k: int,
        data: Dict[str, Any],
        ttl: int = ONLINE_TTL
    ) -> bool:
        """
        Redis에 온라인 캐시 저장

        Args:
            steam_id: 사용자 Steam ID
            top_k: 추천 게임 개수
            data: 저장할 데이터
            ttl: Time To Live (초)

        Returns:
            저장 성공 여부
        """
        try:
            key = RecommendationCache._get_online_key(steam_id, top_k)
            await redis_client.setex(key, ttl, json.dumps(data))
            logger.info(f"✓ Online cache saved: {steam_id} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Redis 저장 실패: {e}")
            return False

    # =========================================================================
    # Week 5에서 사용할 메서드: 배치 캐싱 (이미 미리 작성)
    # =========================================================================

    @staticmethod
    async def get_batch(steam_id: str, top_k: int = 10) -> Optional[Dict[str, Any]]:
        """
        Redis에서 배치 캐시 조회 (Week 5)

        Args:
            steam_id: 사용자 Steam ID
            top_k: 추천 게임 개수

        Returns:
            배치 캐시된 추천 결과 또는 None
        """
        try:
            key = RecommendationCache._get_batch_key(steam_id, top_k)
            cached_data = await redis_client.get(key)

            if cached_data:
                logger.info(f"✓ Batch cache hit: {steam_id}")
                return json.loads(cached_data)

            logger.info(f"⚠️ Batch cache miss: {steam_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Redis 배치 조회 실패: {e}")
            return None

    @staticmethod
    async def set_batch(
        steam_id: str,
        top_k: int,
        data: Dict[str, Any],
        ttl: int = BATCH_TTL
    ) -> bool:
        """
        Redis에 배치 캐시 저장 (Week 5)

        Args:
            steam_id: 사용자 Steam ID
            top_k: 추천 게임 개수
            data: 저장할 데이터
            ttl: Time To Live (초)

        Returns:
            저장 성공 여부
        """
        try:
            key = RecommendationCache._get_batch_key(steam_id, top_k)
            await redis_client.setex(key, ttl, json.dumps(data))
            logger.info(f"✓ Batch cache saved: {steam_id} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Redis 배치 저장 실패: {e}")
            return False

    @staticmethod
    async def delete_online(steam_id: str, top_k: Optional[int] = None) -> bool:
        """
        Redis에서 온라인 캐시 삭제

        Args:
            steam_id: 사용자 Steam ID
            top_k: 추천 게임 개수 (None이면 모든 top_k에 대해 삭제)

        Returns:
            삭제 성공 여부
        """
        try:
            if top_k is None:
                # steam_id의 모든 캐시 삭제
                pattern = f"{RecommendationCache.ONLINE_CACHE_PREFIX}:{steam_id}:*"
                keys = await redis_client.keys(pattern)
                if keys:
                    await redis_client.delete(*keys)
                    logger.info(f"✓ Online cache deleted: {steam_id} ({len(keys)} keys)")
                return True
            else:
                # 특정 top_k만 삭제
                key = RecommendationCache._get_online_key(steam_id, top_k)
                await redis_client.delete(key)
                logger.info(f"✓ Online cache deleted: {steam_id}:{top_k}")
                return True

        except Exception as e:
            logger.error(f"❌ Redis 삭제 실패: {e}")
            return False

    @staticmethod
    async def delete_batch(steam_id: str, top_k: Optional[int] = None) -> bool:
        """
        Redis에서 배치 캐시 삭제

        Args:
            steam_id: 사용자 Steam ID
            top_k: 추천 게임 개수 (None이면 모든 top_k에 대해 삭제)

        Returns:
            삭제 성공 여부
        """
        try:
            if top_k is None:
                # steam_id의 모든 배치 캐시 삭제
                pattern = f"{RecommendationCache.BATCH_CACHE_PREFIX}:{steam_id}:*"
                keys = await redis_client.keys(pattern)
                if keys:
                    await redis_client.delete(*keys)
                    logger.info(f"✓ Batch cache deleted: {steam_id} ({len(keys)} keys)")
                return True
            else:
                # 특정 top_k만 삭제
                key = RecommendationCache._get_batch_key(steam_id, top_k)
                await redis_client.delete(key)
                logger.info(f"✓ Batch cache deleted: {steam_id}:{top_k}")
                return True

        except Exception as e:
            logger.error(f"❌ Redis 배치 삭제 실패: {e}")
            return False

    @staticmethod
    async def clear_all() -> bool:
        """모든 추천 관련 캐시 삭제 (개발/테스트용)"""
        try:
            online_keys = await redis_client.keys(f"{RecommendationCache.ONLINE_CACHE_PREFIX}:*")
            batch_keys = await redis_client.keys(f"{RecommendationCache.BATCH_CACHE_PREFIX}:*")

            all_keys = online_keys + batch_keys
            if all_keys:
                await redis_client.delete(*all_keys)
                logger.info(f"✓ All recommendation caches cleared ({len(all_keys)} keys)")
            return True

        except Exception as e:
            logger.error(f"❌ Redis 전체 삭제 실패: {e}")
            return False

    @staticmethod
    async def get_cache_stats() -> Dict[str, Any]:
        """캐시 통계 조회"""
        try:
            online_keys = await redis_client.keys(f"{RecommendationCache.ONLINE_CACHE_PREFIX}:*")
            batch_keys = await redis_client.keys(f"{RecommendationCache.BATCH_CACHE_PREFIX}:*")

            # 캐시 크기 계산 (바이트)
            online_size = 0
            for key in online_keys:
                online_size += len(await redis_client.get(key) or b'')

            batch_size = 0
            for key in batch_keys:
                batch_size += len(await redis_client.get(key) or b'')

            return {
                'online_cache_count': len(online_keys),
                'online_cache_size_mb': online_size / (1024 * 1024),
                'batch_cache_count': len(batch_keys),
                'batch_cache_size_mb': batch_size / (1024 * 1024),
                'total_cache_size_mb': (online_size + batch_size) / (1024 * 1024),
            }

        except Exception as e:
            logger.error(f"❌ 캐시 통계 조회 실패: {e}")
            return {}
