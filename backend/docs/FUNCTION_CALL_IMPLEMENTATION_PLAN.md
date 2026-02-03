# Function Call Tools 구현 계획서

**작성일**: 2026-02-03
**담당**: Backend PM / Tools 개발자
**상태**: 최종 아키텍처 확정, Phase 1 (tools.py) 진행 중

---

## 📋 목차

1. [최종 아키텍처 결정사항](#최종-아키텍처-결정사항)
2. [데이터 흐름](#데이터-흐름)
3. [Tools 함수 정의](#tools-함수-정의)
4. [필터링 필드 상세](#필터링-필드-상세)
5. [구현 일정](#구현-일정)
6. [파일 변경 계획](#파일-변경-계획)
7. [개발 옵션](#개발-옵션)

---

## 🎯 최종 아키텍처 결정사항

### RAG도 Function Call로 통합

**이전 구조**: RAG는 chatbot.py에서 자동 실행, Function Call은 별도
```
chatbot.py (RAG 자동)  |  tools.py (Function Call)
                       ↓
                    중복 조회 문제 ❌
```

**새로운 구조**: 모든 데이터 조회를 Function Call로 통일
```
LLM이 필요한 정보를 선택해서 Function Call 사용
          ↓
모든 데이터 조회가 일관된 방식
          ↓
투명성, 로깅, 제어 가능 ✅
```

### LLM이 사용 가능한 Tools (5개)

```
GameTools Class
├─ search_by_embedding(query, top_k=3)
│   └─ 의미 유사도 기반 검색 (RAG)
│
├─ search_games_by_filter(...)
│   └─ 필터링 기반 검색 (12개 필터)
│
├─ get_personalized_recommendations(top_k=5, steam_id=None)
│   └─ 개인화 추천 (협필터링 + DCN)
│
├─ get_game_info(game_name, wanted=None)
│   └─ 게임 상세 정보 조회
│
└─ get_game_reviews(game_name)
    └─ 게임 평점/리뷰 요약
```

---

## 📊 데이터 흐름

```
┌─────────────────────────────────────────┐
│ 1. 사용자 입력                           │
│ "1만원 이하 RPG 추천해줘"                │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ 2. LLM (Clova X) 분석                   │
│   - 질문 이해                            │
│   - 필요한 정보 파악                      │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ 3. LLM이 Function Call 선택              │
│ search_games_by_filter(                 │
│   max_price=10000,                      │
│   genres=["RPG"]                        │
│ )                                       │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ 4. tools.py 함수 실행                    │
│   ↓ PostgreSQL 쿼리                      │
│   ↓ 데이터 처리                          │
│   ↓ 결과 반환                            │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ 5. LLM에 결과 반환                        │
│ [                                       │
│   {"name": "게임1", "price": 5000},     │
│   {"name": "게임2", "price": 8000},     │
│   ...                                   │
│ ]                                       │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ 6. LLM이 최종 답변 생성                   │
│ "1만원 이하 RPG 게임으로 다음을          │
│  추천드립니다..."                        │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ 7. 사용자에게 응답                        │
└─────────────────────────────────────────┘
```

---

## 🔧 Tools 함수 정의

### 1. search_by_embedding(query, top_k=3)

**목적**: 의미 유사도 기반 게임 검색 (RAG)

**사용 상황**:
- "위처3 같은 게임 추천해"
- "로그라이크 게임 뭐가 있어?"
- "오픈 월드 RPG 찾아줘"

**입력**:
```python
query: str          # 검색어 (예: "로그라이크")
top_k: int = 3      # 상위 결과 개수
```

**출력**:
```python
List[Dict]:
  - game_id: int
  - name: str
  - similarity_score: float (0.0~1.0)
  - short_description_kr: str
  - genres_kr: List[str]
  - header_image: str
  - price: int
```

**데이터 소스**: PostgreSQL pgvector (embedding 벡터 유사도 검색)

**구현**:
1. 입력 query를 embedding으로 변환
2. pgvector 코사인 유사도 검색
3. 상위 k개 게임 반환

---

### 2. search_games_by_filter(...)

**목적**: 조건 기반 게임 검색

**사용 상황**:
- "1만원 이하 RPG 찾아줘"
- "할인 중인 인디 게임"
- "Windows에서 할 수 있는 게임"

**입력** (모두 Optional):
```python
query: Optional[str] = None            # 게임명 검색
max_price: Optional[int] = None        # 최대 가격 (KRW)
min_price: Optional[int] = None        # 최소 가격
genres: Optional[List[str]] = None     # 장르 (genres_kr)
tags: Optional[List[str]] = None       # 태그 (tags_en)
platforms: Optional[List[str]] = None  # Windows, Mac, Linux
is_free: Optional[bool] = None         # 무료 게임만
is_korean_supported: Optional[bool] = None  # 한국어 지원
min_metacritic: Optional[int] = None   # 최소 메타크리틱 점수
developers: Optional[List[str]] = None # 개발사 필터
release_year: Optional[int] = None     # 출시 연도
dlc_available: Optional[bool] = None   # DLC 있는 게임
```

**출력**:
```python
List[Dict] (최대 10개):
  - game_id: int
  - name: str
  - price: int
  - genres_kr: List[str]
  - platforms: Dict[str, bool]
  - is_korean_supported: bool
  - metacritic: int
  - dlc_count: int
  - header_image: str
```

**데이터 소스**: PostgreSQL games 테이블 (동적 WHERE 조건)

**구현**:
1. 동적 WHERE 조건 빌더
2. SELECT 쿼리 실행
3. 최대 10개 결과 반환

---

### 3. get_personalized_recommendations(top_k=5, steam_id=None)

**목적**: 사용자의 플레이 이력 기반 개인화 추천

**사용 상황**:
- "내 취향에 맞는 게임 추천해"
- "내가 좋아할 만한 게임"
- "최근 추천 게임"

**입력**:
```python
top_k: int = 5              # 상위 추천 개수 (최대 20)
steam_id: Optional[str] = None  # Steam 사용자 ID
```

**출력**:
```python
List[Dict]:
  - game_id: int
  - name: str
  - score: float (0.0~1.0)   # 추천 점수
  - reason: str              # 추천 이유
  - genres: List[str]
  - header_image: str
```

**데이터 소스**: BentoML API (협필터링 + DCN 모델)

**Steam ID 관리**:
1. steam_id가 None이면:
   - LLM이 "Steam ID를 입력해주세요" 요청
   - 사용자 입력 받음
2. steam_id 저장:
   - Redis 또는 Session에 저장 (TTL: 30분)
3. 재사용:
   - 이후 요청에서 자동 추출

**구현**:
1. steam_id 확인 (없으면 저장된 값 사용)
2. BentoML API에 요청
3. 게임 정보 보강 (이름, 장르, 이미지 등)
4. 결과 반환

---

### 4. get_game_info(game_name, wanted=None)

**목적**: 특정 게임의 상세 정보 조회

**사용 상황**:
- "엘든링 가격이 얼마야?"
- "위처3의 개발사가 뭐야?"
- "이 게임 시스템 요구사항 알려줘"

**입력**:
```python
game_name: str                  # 게임 이름
wanted: Optional[List[str]] = None  # 원하는 정보 필드
  # 가능한 값: ["price", "details", "requirements", "reviews", "media", "dev_info"]
  # None이면 전체 정보 반환
```

**출력**:
```python
Dict:
  - title: str
  - game_id: int
  - price: Dict
      - current: int (KRW)
      - original: int
  - details: Dict
      - genres: List[str]
      - developer: str
      - release_date: str
      - description: str
  - requirements: Dict
      - os: str
      - min_cpu: str
      - min_ram: str
      - min_gpu: str
  - reviews: Dict
      - metacritic_score: int
      - recommendations_total: int
  - media: Dict
      - header_image: str
      - screenshots: List[str]
  - dev_info: Dict
      - developers: List[str]
      - publishers: List[str]
      - dlc_count: int
```

**데이터 소스**: PostgreSQL games 테이블 (ILIKE 검색)

**구현**:
1. 게임명으로 ILIKE 검색
2. 전체 정보 구성
3. wanted 필터링 적용 (있으면)
4. 결과 반환

---

### 5. get_game_reviews(game_name)

**목적**: 게임의 평점과 리뷰 요약 조회

**사용 상황**:
- "엘든링 평점이 어떻게 돼?"
- "사람들이 이 게임을 어떻게 평가해?"

**입력**:
```python
game_name: str  # 게임 이름
```

**출력**:
```python
Dict:
  - title: str
  - score: int (0~100)
  - sentiment: str
      # "매우 긍정적" (85-100)
      # "긍정적" (70-84)
      # "혼합" (50-69)
      # "부정적" (30-49)
      # "매우 부정적" (0-29)
  - summary: str (리뷰 요약)
  - keywords: List[str] (주요 키워드 top 5)
  - review_count: int (리뷰 총 개수)
```

**데이터 소스**: PostgreSQL games 테이블 (metacritic, recommendations_total)

**구현**:
1. 게임명으로 검색
2. metacritic, recommendations_total 조회
3. 감정 분류 (score 기반)
4. 결과 반환

---

## 📌 필터링 필드 상세

### search_games_by_filter의 12개 필터

| # | 필터명 | 타입 | 설명 | DB 필드 | 예시 |
|----|--------|------|------|---------|------|
| 1 | query | str | 게임명 검색 (ILIKE) | name | "Elden" |
| 2 | max_price | int | 최대 가격 (KRW) | price | 50000 |
| 3 | min_price | int | 최소 가격 (KRW) | price | 10000 |
| 4 | genres | List[str] | 장르 필터 (AND 조건) | genres_kr | ["RPG", "Action"] |
| 5 | tags | List[str] | 태그 필터 (OR 조건) | tags_en | ["Open World"] |
| 6 | platforms | List[str] | 플랫폼 필터 | platforms | ["Windows", "Linux"] |
| 7 | is_free | bool | 무료 게임만 | is_free | true |
| 8 | is_korean_supported | bool | 한국어 지원 | is_korean_supported | true |
| 9 | min_metacritic | int | 최소 메타크리틱 점수 | metacritic | 80 |
| 10 | developers | List[str] | 개발사 필터 | developers | ["FromSoftware"] |
| 11 | release_year | int | 출시 연도 | release_date | 2022 |
| 12 | dlc_available | bool | DLC 있는 게임 | dlc_count > 0 | true |

### 쿼리 예시

**예시 1**: "1만원 이하 RPG"
```python
search_games_by_filter(
    max_price=10000,
    genres=["RPG"]
)
```

**예시 2**: "무료 한국어 지원 게임"
```python
search_games_by_filter(
    is_free=True,
    is_korean_supported=True
)
```

**예시 3**: "FromSoftware 메타크리틱 80점 이상"
```python
search_games_by_filter(
    developers=["FromSoftware"],
    min_metacritic=80
)
```

**예시 4**: "2022년 이후 Linux 게임"
```python
search_games_by_filter(
    release_year=2022,
    platforms=["Linux"]
)
```

---

## 📅 구현 일정

### Phase 1: tools.py 구현 (옵션 A)

**예상 시간**: 2-3시간

```
1. tools.py 파일 생성
   ├─ GameTools 클래스 정의
   ├─ __init__ 메서드
   └─ 의존성 주입 함수

2. 5개 함수 구현
   ├─ search_by_embedding()
   ├─ search_games_by_filter()
   ├─ get_personalized_recommendations()
   ├─ get_game_info()
   └─ get_game_reviews()

3. 헬퍼 함수 구현
   ├─ _call_bentoml_api()
   ├─ _get_steam_id_from_session()
   ├─ _save_steam_id_to_redis()
   └─ 에러 처리

4. Docstring 작성
   └─ 각 함수의 완전한 문서화
```

**결과**: tools.py 파일 완성 + 문서
**다음 담당자**: 오케스트레이터 (chatbot.py 통합)

---

### Phase 2: chatbot.py & router.py 통합 (옵션 B)

**예상 시간**: 1-2시간

```
1. chatbot.py 수정
   ├─ GameTools 인스턴스 초기화
   ├─ RAG 자동 실행 제거
   ├─ LangChain function calling 설정
   └─ 시스템 프롬프트 업데이트

2. router.py 수정
   ├─ steam_id 세션 관리 추가
   └─ 응답 포맷 수정

3. schemas.py 수정
   ├─ FunctionCall 모델 추가 (선택)
   └─ ChatResponse 수정 (선택)
```

**결과**: 실제 동작하는 function call 시스템

---

### Phase 3: 테스트 & 검증 (옵션 C)

**예상 시간**: 1-2시간

```
1. 단위 테스트 작성 (test_tools.py)
   ├─ 각 함수별 테스트
   ├─ Mock 데이터 사용
   └─ DB 연결 테스트

2. E2E 테스트
   ├─ LLM + Function Calling 전체 흐름
   └─ 실제 DB/BentoML 연동
```

**결과**: 테스트 완료 + 검증된 시스템

---

## 📂 파일 변경 계획

### 신규 생성

**`backend/app/domains/chat/tools.py`**
```python
"""
게임 추천 시스템용 Function Call Tools
- 의미 검색 (RAG)
- 필터링 검색
- 개인화 추천
- 게임 정보 조회
- 리뷰 조회
"""

import json
import httpx
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.logger import logger
from app.core.config import settings

class GameTools:
    def __init__(
        self,
        db_session: AsyncSession,
        redis_client=None,
        embeddings_model=None
    ):
        self.db = db_session
        self.redis = redis_client
        self.embeddings = embeddings_model
        self.bentoml_url = settings.BENTOML_SERVICE_URL

    # 5개 함수 구현...

def get_game_tools(
    db_session: AsyncSession,
    redis_client=None,
    embeddings_model=None
) -> GameTools:
    """의존성 주입용 헬퍼 함수"""
    return GameTools(db_session, redis_client, embeddings_model)
```

### 수정 필요

**`backend/app/domains/chat/chatbot.py`** (Phase 2)
```python
# 추가
from app.domains.chat.tools import GameTools

# __init__ 수정
self.tools = None

# initialize 메서드에 추가
self.tools = GameTools(engine, redis_client, embeddings_model)

# RAG 자동 실행 제거
# 기존 self.retriever 로직 제거

# function calling 통합
# LangChain의 bind_tools() 사용
```

**`backend/app/domains/chat/router.py`** (Phase 2)
```python
# steam_id 세션 관리 추가
# function call 결과 처리 추가
```

**`backend/app/domains/chat/schemas.py`** (Phase 2, 선택)
```python
# FunctionCall 모델 추가 (선택)
class FunctionCall(BaseModel):
    tool_name: str
    arguments: Dict
    result: Any

# ChatResponse에 tool_calls 필드 추가 (선택)
```

---

## 🎯 개발 옵션

### Option A: tools.py만 구현 ⭐ (현재 선택)

**범위**: tools.py 파일만 완성

**시간**: 2-3시간

**결과**:
- ✅ 완성된 tools.py
- ✅ 함수 정의 명확
- ✅ 상세 문서

**다음 담당**: 오케스트레이터

**장점**:
- 빠른 구현
- 명확한 인터페이스
- 다른 팀원이 쉽게 통합 가능

**단점**:
- 실제 동작 미검증
- 통합 로직 직접 하지 않음

---

### Option B: tools.py + chatbot.py 통합

**범위**: tools.py + chatbot.py + router.py 수정

**시간**: 4-6시간

**결과**:
- ✅ 완전 동작하는 function call 시스템
- ✅ 실제 LLM과 연동 가능
- ✅ 테스트 가능한 상태

**장점**:
- 완전 동작
- 바로 테스트 가능
- 통합 로직 확인 가능

**단점**:
- 시간 소요
- 테스트 미완

---

### Option C: 전체 + 테스트

**범위**: A + B + 테스트

**시간**: 5-7시간

**결과**:
- ✅ 완벽한 시스템
- ✅ 테스트 완료
- ✅ 문서 완성

**장점**:
- 완벽함
- 모든 버그 사전 발견
- 프로덕션 준비 완료

**단점**:
- 가장 오래 걸림

---

## ✅ 체크리스트 (Phase 1 - Option A)

### tools.py 작성

- [ ] GameTools 클래스 정의
- [ ] __init__ 메서드 구현
- [ ] search_by_embedding() 구현
- [ ] search_games_by_filter() 구현
- [ ] get_personalized_recommendations() 구현
- [ ] get_game_info() 구현
- [ ] get_game_reviews() 구현
- [ ] _call_bentoml_api() 헬퍼 함수
- [ ] _get_steam_id_from_session() 헬퍼 함수
- [ ] _save_steam_id_to_redis() 헬퍼 함수
- [ ] 에러 처리 (try-except)
- [ ] 로깅 추가 (logger.info, logger.error)
- [ ] Docstring 작성 (모든 함수)
- [ ] Type hints 적용 (100%)
- [ ] get_game_tools() 의존성 주입 함수

---

## 📚 참고 자료

### Database

- **Games 테이블**: `backend/app/domains/game/models.py`
- **메타데이터**: `backend/app/data/games_metadata.jsonl`

### 기존 코드

- **Chatbot**: `backend/app/domains/chat/chatbot.py`
- **Schemas**: `backend/app/domains/chat/schemas.py`
- **Models**: `backend/app/domains/chat/models.py`

### 설정

- **BentoML URL**: `settings.BENTOML_SERVICE_URL` (http://bentoml:3000)
- **Database**: `settings.DATABASE_URL`

---

## 🚀 다음 단계

**1. Option A (tools.py) 구현 시작**
```bash
cd backend
# tools.py 작성
```

**2. 구현 완료 후**
- [ ] 코드 리뷰
- [ ] 상황 보고
- [ ] Option B/C 진행 여부 결정

---

**최종 승인**: 2026-02-03
**개발 상태**: Phase 1 준비 완료 ✅
