# Function Call Tools 개발 메뉴얼

**작성일:** 2025-02-03
**대상:** Backend PM / 함수 개발자
**목표:** Clova X (LLM) 에이전트가 사용할 Function Call Tools를 명확한 인터페이스로 개발하기

---

## 📌 목차

1. [개요](#개요)
2. [함수 규격 정의](#함수-규격-정의)
3. [tools.py 구현 가이드](#toolspy-구현-가이드)
4. [각 함수별 상세 스펙](#각-함수별-상세-스펙)
5. [매개변수 최적화 팁](#매개변수-최적화-팁)
6. [개발 일정 및 체크리스트](#개발-일정-및-체크리스트)

---

## 개요

### 핵심 개념

이 문서의 목표는 **"Clova X가 헷갈리지 않게 명확한 인자를 주고받는 것"**입니다.

### 컨텍스트

- **현재 상태:** `chatbot.py`는 RAG 기반으로만 동작 (임베딩 검색 + LLM 응답)
- **목표:** Function Calling을 통해 LLM이 게임 정보, 추천, 필터링을 동적으로 요청 가능하게
- **역할 분담:**
  - **Chatbot (오케스트레이터):** LLM 요청 분석 → 적절한 도구 함수 선택 → 결과 LLM 전달
  - **Tools (함수 모음):** 정확한 데이터 반환 (DB 쿼리, 추천 모델 호출, 필터링)

---

## 함수 규격 정의

### 전체 함수 List

| 함수명 | 매개변수 | 반환값 | 용도 | 우선순위 |
|--------|---------|--------|------|----------|
| `get_game_info` | `game_name: str`<br>`wanted: list[str] (Optional)` | `Dict` (게임 상세 정보) | 특정 게임의 상세 정보 조회 | **필수** |
| `get_personalized_recommendations` | `top_k: int (Default: 5)` | `List[Dict]` (추천 게임 목록) | 개인화된 게임 추천 | **필수** |
| `search_games_by_filter` | `query: str (Optional)`<br>`max_price: int (Optional)`<br>`tags: list[str] (Optional)`<br>`platforms: list[str] (Optional)`<br>`on_sale: bool (Optional)` | `List[Dict]` (필터링된 게임) | 복합 조건으로 게임 검색 | **필수** |
| `get_game_reviews` | `game_name: str` | `Dict` (리뷰 요약) | 게임 평판/리뷰 요약 조회 | 선택 |
| `get_trending_games` | `period: str (default: "week")` | `List[Dict]` (인기 게임) | 현재 인기 게임 조회 | 선택 |

---

## tools.py 구현 가이드

### 파일 위치

```
backend/
├── app/
│   └── domains/
│       └── chat/
│           ├── tools.py          ← 새로 생성할 파일
│           ├── chatbot.py
│           └── router.py
```

### 기본 구조 템플릿

```python
"""
게임 추천 시스템용 Function Call Tools
- 데이터베이스 쿼리
- 추천 모델 호출
- 필터링 로직
"""

import json
import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logger import logger

logger = logging.getLogger(__name__)


class GameTools:
    """Clova X가 호출할 게임 관련 함수들의 모음"""

    def __init__(self, db_session: AsyncSession, redis_client=None):
        """
        초기화

        Args:
            db_session: SQLAlchemy AsyncSession (PostgreSQL 연결)
            redis_client: Redis 클라이언트 (캐싱용, 선택사항)
        """
        self.db = db_session
        self.redis = redis_client

    # ============================================
    # Function 1: get_game_info
    # ============================================

    async def get_game_info(
        self,
        game_name: str,
        wanted: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        특정 게임의 상세 정보를 조회합니다.

        Parameters:
            game_name (str): 게임 이름 (예: "The Witcher 3")
            wanted (List[str], optional): 원하는 필드만 반환
                - Possible values: ["price", "details", "requirements", "reviews"]
                - None이면 전체 정보 반환

        Returns:
            Dict with keys:
                - title (str): 게임 제목
                - game_id (int): 게임 ID (내부 DB에서 사용)
                - price (Dict):
                    - current (int): 현재 가격 (단위: KRW)
                    - original (int): 정가
                    - discount_rate (int): 할인율 (0-100)
                - details (Dict):
                    - genres (List[str]): 장르
                    - developer (str): 개발사
                    - release_date (str): 출시일 (YYYY-MM-DD)
                    - description (str): 게임 설명 (짧게, ~200자)
                - requirements (Dict):
                    - os (str): 지원 OS
                    - min_cpu (str): 최소 CPU
                    - min_ram (str): 최소 RAM (GB)
                    - min_gpu (str): 최소 GPU
                - steam_url (str): Steam 상점 URL

        Example:
            >>> await tools.get_game_info("Elden Ring", wanted=["price", "details"])
            {
                "title": "ELDEN RING",
                "price": {"current": 59800, "discount_rate": 0},
                "details": {
                    "genres": ["Action", "RPG"],
                    "developer": "FromSoftware"
                }
            }
        """
        logger.info(f"🎮 Fetching game info: {game_name}")

        try:
            # 1. 유사 검색 (ILIKE를 사용하여 대소문자 무시)
            query = """
            SELECT id, name, genres_kr, price, developer, release_date,
                   min_cpu, min_ram, min_gpu, os_requirement, description
            FROM games
            WHERE name ILIKE :game_name
            LIMIT 1
            """

            result = await self.db.execute(
                text(query),
                {"game_name": f"%{game_name}%"}
            )
            game_row = result.fetchone()

            if not game_row:
                logger.warning(f"❌ Game not found: {game_name}")
                return {"error": f"'{game_name}' 게임을 찾을 수 없습니다."}

            # 2. 전체 정보 구성
            full_response = {
                "title": game_row.name,
                "game_id": game_row.id,
                "price": {
                    "current": int(game_row.price) if game_row.price else 0,
                    "original": int(game_row.original_price) if hasattr(game_row, 'original_price') else 0,
                    "discount_rate": 0  # 필요시 계산 로직 추가
                },
                "details": {
                    "genres": json.loads(game_row.genres_kr) if game_row.genres_kr else [],
                    "developer": game_row.developer or "Unknown",
                    "release_date": str(game_row.release_date) if game_row.release_date else "Unknown",
                    "description": game_row.description or ""
                },
                "requirements": {
                    "os": game_row.os_requirement or "Unknown",
                    "min_cpu": game_row.min_cpu or "Unknown",
                    "min_ram": game_row.min_ram or "Unknown",
                    "min_gpu": game_row.min_gpu or "Unknown"
                },
                "steam_url": f"https://store.steampowered.com/search/?term={game_row.name}"
            }

            # 3. wanted 필터링 적용
            if wanted:
                filtered_response = {"title": full_response["title"], "game_id": full_response["game_id"]}
                if "price" in wanted:
                    filtered_response["price"] = full_response["price"]
                if "details" in wanted:
                    filtered_response["details"] = full_response["details"]
                if "requirements" in wanted:
                    filtered_response["requirements"] = full_response["requirements"]
                if "url" in wanted:
                    filtered_response["steam_url"] = full_response["steam_url"]
                return filtered_response

            return full_response

        except Exception as e:
            logger.error(f"❌ Error fetching game info: {e}")
            return {"error": str(e)}

    # ============================================
    # Function 2: get_personalized_recommendations
    # ============================================

    async def get_personalized_recommendations(
        self,
        top_k: int = 5,
        steam_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        사용자의 플레이 이력과 선호도를 바탕으로 개인화된 게임을 추천합니다.

        Parameters:
            top_k (int): 상위 추천 게임 개수 (Default: 5, Max: 20)
            steam_id (str, optional): Steam 사용자 ID
                - None이면 세션/현재 로그인 사용자에서 자동 추출

        Returns:
            List[Dict] with keys:
                - game_id (int): 게임 ID
                - title (str): 게임 제목
                - score (float): 추천 점수 (0.0 ~ 1.0)
                - reason (str): 추천 이유 (LLM 응답용 짧은 설명)
                - genres (List[str]): 게임 장르
                - thumbnail_url (str): 게임 썸네일 이미지 URL

        Example:
            >>> await tools.get_personalized_recommendations(top_k=5, steam_id="76561198...")
            [
                {
                    "game_id": 105600,
                    "title": "Terraria",
                    "score": 0.95,
                    "reason": "샌드박스 장르 선호 반영, 유사 게임들의 높은 평가",
                    "genres": ["Sandbox", "Indie"],
                    "thumbnail_url": "https://..."
                },
                ...
            ]
        """
        logger.info(f"🎯 Generating recommendations for user: {steam_id or 'current_session'}")

        try:
            # 1. steam_id 확인 (세션에서 추출)
            user_id = steam_id  # 실제로는 Request context에서 추출해야 함
            if not user_id:
                logger.warning("⚠️ steam_id not provided, using session user")
                return []

            # 2. 추천 모델 호출 (BentoML)
            # 실제 구현: requests.post(f"{BENTOML_SERVER}/predict", json={"user_id": user_id, "top_k": top_k})
            recommendations = await self._call_recommendation_model(user_id, top_k)

            if not recommendations:
                logger.warning(f"⚠️ No recommendations for user: {user_id}")
                return []

            # 3. 게임 정보 보강 (제목, 장르 등)
            enriched = []
            for rec in recommendations[:top_k]:
                game_info = await self._get_game_by_id(rec["game_id"])
                if game_info:
                    enriched.append({
                        "game_id": rec["game_id"],
                        "title": game_info.get("name", "Unknown"),
                        "score": float(rec.get("score", 0.0)),
                        "reason": rec.get("reason", "맞춤 추천"),
                        "genres": game_info.get("genres", []),
                        "thumbnail_url": game_info.get("header_image", "")
                    })

            logger.info(f"✅ Generated {len(enriched)} recommendations")
            return enriched

        except Exception as e:
            logger.error(f"❌ Error in recommendations: {e}")
            return []

    # ============================================
    # Function 3: search_games_by_filter
    # ============================================

    async def search_games_by_filter(
        self,
        query: Optional[str] = None,
        max_price: Optional[int] = None,
        tags: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
        on_sale: bool = False
    ) -> List[Dict[str, Any]]:
        """
        여러 조건으로 게임을 검색합니다 (동적 쿼리).

        Parameters:
            query (str, optional): 게임 이름 또는 키워드 검색
            max_price (int, optional): 최대 가격 (KRW)
            tags (List[str], optional): 장르 필터
                - 가능한 값: ["Action", "RPG", "Indie", "Casual", "Simulation", "Strategy", etc.]
            platforms (List[str], optional): 플랫폼 필터
                - 가능한 값: ["Windows", "Mac", "Linux"]
            on_sale (bool): True면 현재 할인 중인 게임만 필터링

        Returns:
            List[Dict] with keys:
                - game_id (int): 게임 ID
                - title (str): 게임 제목
                - price (int): 현재 가격 (KRW)
                - discount_rate (int): 할인율 (0-100)
                - tags (List[str]): 장르
                - on_sale (bool): 현재 할인 여부
                - thumbnail_url (str): 썸네일

        Notes:
            - 최대 10개 결과만 반환 (LLM이 처리하기 쉽게)
            - query와 tags를 조합하면 AND 조건으로 검색

        Example:
            >>> await tools.search_games_by_filter(
            ...     query="RPG",
            ...     max_price=50000,
            ...     tags=["RPG"],
            ...     on_sale=True
            ... )
            [
                {
                    "game_id": 105600,
                    "title": "Monster Hunter: World",
                    "price": 39800,
                    "discount_rate": 20,
                    "tags": ["Action", "RPG"],
                    "on_sale": True,
                    "thumbnail_url": "https://..."
                },
                ...
            ]
        """
        logger.info(f"🔍 Searching games: query={query}, max_price={max_price}, tags={tags}")

        try:
            # 1. 동적 SQL 쿼리 구성
            where_clauses = ["name ILIKE :query" if query else "1=1"]
            params = {}

            if query:
                params["query"] = f"%{query}%"
            if max_price:
                where_clauses.append("price <= :max_price")
                params["max_price"] = max_price
            if on_sale:
                where_clauses.append("discount_rate > 0")
            if platforms:
                # platforms를 쉼표로 구분된 문자열로 저장한다고 가정
                platform_condition = " OR ".join([f"platforms ILIKE :platform_{i}" for i in range(len(platforms))])
                where_clauses.append(f"({platform_condition})")
                for i, platform in enumerate(platforms):
                    params[f"platform_{i}"] = f"%{platform}%"

            where_sql = " AND ".join(where_clauses)

            # 2. 장르 필터링 (tags)
            # PostgreSQL JSONB 배열 포함 검사 사용
            tag_sql = ""
            if tags:
                tag_conditions = []
                for i, tag in enumerate(tags):
                    tag_conditions.append(f"genres_kr @> :tag_{i}")
                    params[f"tag_{i}"] = json.dumps([tag], ensure_ascii=False)
                tag_sql = f"AND ({' OR '.join(tag_conditions)})"

            query_sql = f"""
            SELECT id, name, price, discount_rate, genres_kr, platforms, header_image
            FROM games
            WHERE {where_sql}
            {tag_sql}
            ORDER BY price ASC
            LIMIT 10
            """

            result = await self.db.execute(text(query_sql), params)
            games = result.fetchall()

            # 3. 결과 구성
            response = []
            for game in games:
                response.append({
                    "game_id": game.id,
                    "title": game.name,
                    "price": int(game.price) if game.price else 0,
                    "discount_rate": int(game.discount_rate) if game.discount_rate else 0,
                    "tags": json.loads(game.genres_kr) if game.genres_kr else [],
                    "on_sale": bool(game.discount_rate and game.discount_rate > 0),
                    "thumbnail_url": game.header_image or ""
                })

            logger.info(f"✅ Found {len(response)} games")
            return response

        except Exception as e:
            logger.error(f"❌ Error searching games: {e}")
            return []

    # ============================================
    # Function 4: get_game_reviews (Optional)
    # ============================================

    async def get_game_reviews(self, game_name: str) -> Dict[str, Any]:
        """
        게임의 평판과 리뷰 요약을 조회합니다.

        Parameters:
            game_name (str): 게임 이름

        Returns:
            Dict with keys:
                - score (int): 평가 점수 (0-100)
                - sentiment (str): 감정 분류
                    - "매우 긍정적" (85-100)
                    - "긍정적" (70-84)
                    - "혼합" (50-69)
                    - "부정적" (30-49)
                    - "매우 부정적" (0-29)
                - summary (str): 리뷰 요약 (1-2문장)
                - keywords (List[str]): 주요 키워드 (top 5)
                - review_count (int): 리뷰 총 개수

        Example:
            >>> await tools.get_game_reviews("Elden Ring")
            {
                "score": 92,
                "sentiment": "매우 긍정적",
                "summary": "뛰어난 게임성과 도전적인 난이도가 호평받으며...",
                "keywords": ["challenging", "beautiful", "story", "replayability"],
                "review_count": 125000
            }
        """
        logger.info(f"📝 Fetching reviews for: {game_name}")

        try:
            # DB에서 리뷰 요약 테이블 조회
            query = """
            SELECT game_id, avg_score, sentiment_label, summary, top_keywords, review_count
            FROM game_reviews_summary
            WHERE game_id = (SELECT id FROM games WHERE name ILIKE :game_name LIMIT 1)
            """

            result = await self.db.execute(text(query), {"game_name": f"%{game_name}%"})
            review_row = result.fetchone()

            if not review_row:
                return {"error": f"'{game_name}'의 리뷰 정보를 찾을 수 없습니다."}

            return {
                "score": int(review_row.avg_score),
                "sentiment": review_row.sentiment_label,
                "summary": review_row.summary,
                "keywords": json.loads(review_row.top_keywords) if review_row.top_keywords else [],
                "review_count": review_row.review_count
            }

        except Exception as e:
            logger.error(f"❌ Error fetching reviews: {e}")
            return {"error": str(e)}

    # ============================================
    # Helper Methods
    # ============================================

    async def _call_recommendation_model(self, user_id: str, top_k: int) -> List[Dict]:
        """BentoML 추천 모델 API 호출"""
        # 실제 구현: HTTP 요청을 통해 추천 서버에 쿼리
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{BENTOML_SERVER}/predict",
        #         json={"user_id": user_id, "top_k": top_k}
        #     )
        #     return response.json()
        pass

    async def _get_game_by_id(self, game_id: int) -> Optional[Dict]:
        """ID로 게임 정보 조회"""
        query = "SELECT id, name, genres_kr, header_image FROM games WHERE id = :id"
        result = await self.db.execute(text(query), {"id": game_id})
        row = result.fetchone()

        if row:
            return {
                "id": row.id,
                "name": row.name,
                "genres": json.loads(row.genres_kr) if row.genres_kr else [],
                "header_image": row.header_image
            }
        return None


# ============================================
# Dependency Injection Helper
# ============================================

def get_game_tools(db_session: AsyncSession, redis_client=None) -> GameTools:
    """FastAPI 의존성 주입용 헬퍼 함수"""
    return GameTools(db_session, redis_client)
```

---

## 각 함수별 상세 스펙

### 1️⃣ get_game_info

**목적:** 특정 게임의 상세 정보를 한 번에 조회

**LLM이 호출하는 상황:**
- "엘든링 가격이 얼마예요?"
- "위처3의 시스템 요구사항 알려줘"
- "이 게임 개발사가 뭐예요?"

**매개변수 설정 팁:**
- `wanted` 매개변수로 필요한 정보만 받으면 LLM이 더 간결하게 답변 가능
- 가격만 묻는 경우: `wanted=["price"]`
- 장르와 개발사를 묻는 경우: `wanted=["details"]`

---

### 2️⃣ get_personalized_recommendations

**목적:** 사용자의 게임 플레이 이력을 바탕으로 맞춤 추천

**LLM이 호출하는 상황:**
- "내 취향에 맞는 게임 추천해줘"
- "최근에 인기 있는 게임 중 내가 좋아할 만한 거 추천"
- "액션 게임을 좋아하는데, 뭐 해볼만한 게 있어?"

**주의사항:**
- `steam_id`는 Request context에서 추출하므로 오케스트레이터가 전달
- 반드시 `reason` 필드를 포함해야 LLM이 설득력 있는 답변 생성

---

### 3️⃣ search_games_by_filter

**목적:** 복합 조건으로 게임 검색 (검색어 + 가격 + 장르 + 플랫폼)

**LLM이 호출하는 상황:**
- "1만원 이하 RPG 게임 찾아줘"
- "인디 게임 중에 할인 중인 거 있어?"
- "리눅스에서 할 수 있는 게임 뭐가 있을까?"

**복합 쿼리 예시:**
```python
# Case 1: 가격 필터만
search_games_by_filter(max_price=30000)

# Case 2: 장르 + 가격
search_games_by_filter(
    tags=["Indie", "Casual"],
    max_price=20000
)

# Case 3: 모든 조건
search_games_by_filter(
    query="adventure",
    max_price=50000,
    tags=["Adventure"],
    platforms=["Windows"],
    on_sale=True
)
```

---

### 4️⃣ get_game_reviews (Optional)

**목적:** 게임의 평판과 리뷰 요약 조회

**LLM이 호출하는 상황:**
- "엘든링 리뷰 평가가 어떤가요?"
- "사람들이 이 게임을 어떻게 생각해요?"

---

## 매개변수 최적화 팁

### 1. 반환값에 "이유(reason)" 포함

추천 함수의 반환값에 `reason` 필드를 넣으면 LLM이 훨씬 설득력 있는 답변을 생성합니다.

**❌ 나쁜 예:**
```json
{
    "game_id": 105600,
    "title": "Terraria",
    "score": 0.95
}
```

**✅ 좋은 예:**
```json
{
    "game_id": 105600,
    "title": "Terraria",
    "score": 0.95,
    "reason": "최근 플레이한 '스타듀밸리'와 유사한 샌드박스 장르, 사용자 선호도 기반"
}
```

### 2. 단위 명시 및 통일

**데이터 일관성:**
- 가격은 반드시 **정수형(KRW)**으로 통일
- 사용자에게 보여줄 때 "₩39,800" 형식으로 포맷

**Example:**
```json
{
    "price": 59800,  // KRW, 정수
    "currency": "KRW",
    "display_price": "₩59,800"  // 옵션: 디스플레이용
}
```

### 3. 리스트 길이 제한

검색 결과가 너무 많으면 LLM이 처리하기 힘듭니다.

**권장사항:**
- 검색 결과: **최대 10개**로 슬라이싱
- 추천 결과: **기본 5개, 최대 20개**
- 트렌딩: **최대 5개**

```python
# ✅ Good
return results[:10]  # 최대 10개만 반환

# ❌ Bad
return all_results  # 수백 개 반환 → LLM이 혼란스러움
```

### 4. 오류 처리 일관성

반환값에 오류 정보를 명확하게 포함

**✅ 일관된 오류 응답:**
```json
{
    "error": "게임을 찾을 수 없습니다.",
    "status": 404
}
```

---

## 개발 일정 및 체크리스트

### 📅 Day 1: Interface 정의 및 Mock 버전

**목표:** 오케스트레이터 개발자가 LLM 연동 테스트를 시작할 수 있도록

**체크리스트:**

- [ ] **Interface Freeze** (1시간)
  - 위의 함수명, 매개변수, 반환값을 팀과 최종 확정
  - 각 함수의 예상 호출 빈도 및 응답 시간 합의
  - Discord/Slack에 핀 메모: "Function Call 규격 확정됨 ✅"

- [ ] **tools.py Mock 버전 완성** (2-3시간)
  - 위 코드 템플릿을 기반으로 가짜 데이터 반환하는 버전 작성
  - 실제 DB 연결 X, hardcoded sample data 사용
  - 예시:
    ```python
    async def get_game_info(self, game_name: str, wanted=None):
        # DB 없이 바로 반환
        return {
            "title": "Mock Game",
            "price": {"current": 29800, "discount_rate": 0},
            "details": {"genres": ["Action", "Indie"]}
        }
    ```

- [ ] **router.py에 tools 통합** (1-2시간)
  - ChatRequest에 function call 결과를 담기 위한 필드 추가
  - tools 인스턴스 의존성 주입 설정

- [ ] **오케스트레이터 개발자 Delivery**
  - "이 tools.py를 chatbot과 연결해서 먼저 테스트해봐. LLM이 실제 function call을 해보자!"

---

### 📅 Day 2: 실제 로직 연결 및 최적화

**목표:** 프로덕션 수준의 안정적인 데이터 반환

**체크리스트:**

- [ ] **PostgreSQL 쿼리 작성** (2-3시간)
  - `get_game_info`: WHERE ILIKE 유사 검색
  - `search_games_by_filter`: 동적 쿼리 빌더 (WHERE 조건 동적 조립)
  - 인덱스 확인: games(name), games(genres_kr), games(price)

- [ ] **BentoML 추천 모델 연동** (2시간)
  - `_call_recommendation_model()` 구현
  - 추천 서버 URL 환경변수 설정
  - Timeout 및 Fallback 로직

- [ ] **캐싱 추가** (1시간, 선택사항)
  - Redis에서 인기 게임/트렌딩 캐싱
  - TTL 설정 (예: 1시간)

- [ ] **오류 처리 강화** (1시간)
  - 데이터 없을 때 정확한 에러 메시지
  - DB 연결 실패 시 재시도 로직

- [ ] **성능 테스트** (1시간)
  - 느린 쿼리 확인 및 최적화
  - Average latency 목표: < 500ms

- [ ] **테스트 코드 작성** (1-2시간)
  ```python
  # test/test_tools.py
  async def test_get_game_info():
      tools = GameTools(mock_db_session)
      result = await tools.get_game_info("Elden Ring")
      assert result["title"] == "ELDEN RING"
      assert "price" in result
  ```

---

## 📝 개발 완료 후 확인사항

### 1. 함수 서명 확인

```python
# ✅ 올바른 async 함수
async def get_game_info(self, game_name: str, wanted: Optional[List[str]] = None) -> Dict[str, Any]:
    pass

# ❌ 동기 함수는 chatbot과 호환 불가
def get_game_info(self, game_name: str, wanted: Optional[List[str]] = None) -> Dict[str, Any]:
    pass
```

### 2. 반환값 검증

각 함수가 **항상 정확한 타입**으로 반환하는지 확인:

- `get_game_info()` → `Dict`
- `get_personalized_recommendations()` → `List[Dict]`
- `search_games_by_filter()` → `List[Dict]`
- `get_game_reviews()` → `Dict`

### 3. 예외 처리

```python
try:
    # 쿼리 실행
except Exception as e:
    logger.error(f"❌ Error: {e}")
    return {"error": "친절한 에러 메시지"}  # 또는 빈 리스트
```

### 4. 로깅

각 함수 시작과 종료에 로그 출력:
```python
logger.info(f"🎮 Fetching game info: {game_name}")
# ... 처리 ...
logger.info(f"✅ Found game: {result['title']}")
```

---

## 💡 FAQ

### Q: tools.py와 router.py의 차이는?

**A:**
- **router.py**: FastAPI의 HTTP 엔드포인트 (사용자 → 서버)
- **tools.py**: LLM이 호출하는 내부 함수 모음 (LLM → chatbot → tools)

### Q: tools.py를 여러 파일로 나누면 안 되나요?

**A:** 가능합니다. 복잡도가 높아지면:
```
chat/
├── tools/
│   ├── __init__.py
│   ├── game_tools.py
│   ├── recommendation_tools.py
│   └── review_tools.py
```

하지만 현재는 하나의 파일로 시작하는 것을 권장합니다.

### Q: 데이터가 없을 때는 어떻게 처리하나요?

**A:** 항상 일관된 형태로 반환:

```python
# ✅ 가능한 경우
return {"error": "게임을 찾을 수 없습니다."}

# 또는
return []  # 리스트 반환 함수의 경우
```

LLM이 "오류" 필드를 인식하고 사용자에게 친절한 메시지를 전달합니다.

---

## 🎯 최종 체크리스트

**PM님이 tools.py를 완성하기 전에:**

- [ ] 위 함수 4개의 정확한 매개변수/반환값 정의 완료
- [ ] Mock 데이터로 먼저 테스트 (실제 DB 연결 전)
- [ ] 오케스트레이터와 데이터 형식 확정
- [ ] 성능 목표 설정 (평균 응답 시간 < 500ms)
- [ ] 에러 처리 방식 정의

**완성 후:**

- [ ] 모든 함수의 docstring 작성 완료
- [ ] 타입 힌팅 100% 적용
- [ ] 유닛 테스트 작성 및 패스
- [ ] 성능 테스트 완료
- [ ] 팀에 문서 공유 및 리뷰

---

## 📚 참고 자료

- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SQLAlchemy AsyncSession](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [LangChain Tool Definition](https://python.langchain.com/docs/modules/tools/)

---

**마지막 응원 한마디:**

지금 담당하신 tools.py는 서비스의 **'팩트 체크' 센터**입니다.
Clova X가 아무리 말을 잘해도 여기서 전달해주는 데이터가 틀리면 엉터리 서비스가 됩니다.
데이터의 **정확도**와 **예외 처리**에 집중하신다면, 이번 프로젝트는 반드시 성공합니다! 🚀
