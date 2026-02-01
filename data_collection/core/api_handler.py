import time
import logging
import requests
from typing import Optional, Dict, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SteamAPIHandler:
    """Steam API 호출 및 Rate Limit 관리를 담당하는 클래스"""

    def __init__(self, delay_seconds: float = 1.5):
        self.delay_seconds = delay_seconds
        self.last_call_time = 0

    def _wait_for_rate_limit(self):
        """API 호출 간격 조절"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self.last_call_time = time.time()

    def fetch(
        self, url: str, params: Dict[str, Any], timeout: int = 10, retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """재시도 로직이 포함된 안전한 GET 요청 (JSON 전용)"""
        data = self.fetch_raw(url, params, timeout, retries)
        return data.json() if data and data.status_code == 200 else None

    def fetch_raw(
        self, url: str, params: Dict[str, Any], timeout: int = 10, retries: int = 3
    ) -> Optional[requests.Response]:
        """재시도 로직이 포함된 안전한 GET 요청 (Raw Response)"""
        for i in range(retries):
            self._wait_for_rate_limit()
            try:
                response = requests.get(url, params=params, timeout=timeout)
                if response.status_code == 200:
                    return response

                if response.status_code == 429:
                    wait_time = 60 * (i + 1)
                    logger.warning(
                        f"🚨 Rate Limit (429). {wait_time}초 대기... ({i+1}/{retries})"
                    )
                    time.sleep(wait_time)
                    continue

                logger.error(f"❌ API 실패 ({response.status_code}): {url}")
            except Exception as e:
                logger.error(f"❌ 네트워크 오류: {e}. 재시도... ({i+1}/{retries})")
                time.sleep(2)
        return None
