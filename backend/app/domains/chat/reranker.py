"""
CLOVA Studio Reranker API Client
"""
import os
import httpx
from typing import List, Dict, Any, Optional
from app.core.logger import logger


class ClovaReranker:
    """CLOVA Studio Reranker API를 사용하여 문서를 재순위화합니다."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        reranker_url: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Args:
            api_key: CLOVA Studio API 키 (없으면 환경변수에서 로드)
            reranker_url: CLOVA Studio Reranker API 전체 URL (없으면 환경변수에서 로드)
            timeout: HTTP 요청 타임아웃 (초)
        """
        # CLOVA_API_KEY는 기존과 동일, Reranker 전용 URL 사용
        self.api_key = api_key or os.getenv("CLOVA_API_KEY")
        self.reranker_url = (reranker_url or os.getenv("CLOVA_RERANKER_URL", "")).rstrip("/")
        self.timeout = timeout

        if not self.api_key:
            logger.warning("⚠️ CLOVA_API_KEY가 설정되지 않았습니다. Reranker를 사용할 수 없습니다.")

        if not self.reranker_url:
            logger.warning("⚠️ CLOVA_RERANKER_URL이 설정되지 않았습니다. Reranker를 사용할 수 없습니다.")

    def is_available(self) -> bool:
        """Reranker가 사용 가능한지 확인합니다."""
        return bool(self.api_key and self.reranker_url)

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        CLOVA Studio Reranker API를 사용하여 문서를 재순위화합니다.

        Args:
            query: 검색 쿼리
            documents: 재순위화할 문서 목록 (각 문서는 텍스트 문자열)
            top_k: 반환할 상위 K개 문서 (없으면 전체 반환)

        Returns:
            재순위화된 문서 리스트. 각 항목은 다음 형식:
            [
                {"index": 원본_인덱스, "score": 점수, "document": 문서_텍스트},
                ...
            ]

        Raises:
            ValueError: API 키 또는 URL이 설정되지 않은 경우
            httpx.HTTPError: API 요청 실패 시
        """
        if not self.is_available():
            raise ValueError(
                "CLOVA Reranker API가 설정되지 않았습니다. "
                "CLOVA_API_KEY와 CLOVA_RERANKER_URL을 확인하세요."
            )

        if not documents:
            logger.warning("⚠️ 재순위화할 문서가 없습니다.")
            return []

        try:
            # API 요청 - reranker_url은 이미 전체 엔드포인트 경로를 포함
            url = self.reranker_url
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            # 문서를 CLOVA Studio 형식으로 변환: [{"id": "0", "doc": "..."}]
            payload = {
                "query": query,
                "documents": [
                    {"id": str(i), "doc": doc}
                    for i, doc in enumerate(documents)
                ]
            }

            logger.info(f"🔄 CLOVA Reranker 요청: query='{query}', docs={len(documents)}개")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()

            # 응답 파싱: citedDocuments에서 인용된 문서 추출
            cited_docs = result.get("result", {}).get("citedDocuments", [])

            # 원본 형식으로 변환: [{"index": 0, "score": 1.0, "document": "..."}]
            reranked_docs = [
                {
                    "index": int(doc.get("id", 0)),
                    "score": 1.0 - (idx * 0.01),  # 순서에 따라 점수 부여 (임시)
                    "document": doc.get("doc", "")
                }
                for idx, doc in enumerate(cited_docs)
            ]

            # top_k 적용
            if top_k is not None and top_k > 0:
                reranked_docs = reranked_docs[:top_k]

            logger.info(f"✅ CLOVA Reranker 완료: {len(reranked_docs)}개 문서 반환")
            return reranked_docs

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ CLOVA Reranker HTTP 오류: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ CLOVA Reranker 요청 실패: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ CLOVA Reranker 예외: {e}")
            raise
