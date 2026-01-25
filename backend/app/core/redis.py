import redis.asyncio as redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# TODO: redis.from_url을 사용하여 Async 클라이언트를 생성하세요.
# 참고: decode_responses=True 옵션을 쓰면 bytes가 아닌 str로 반환됩니다.
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def get_redis_client():
    return redis_client
