# 🎮 TailorPlay: LLM 기반 오케스트레이션 게임 추천 시스템

> 🏫 **Naver Boostcamp AI Tech 8th Cohort**  
> 👥 **recsys-05 Team – Data Tailor**  
> 📅 Jan 2026 – Feb 2026

## "결정의 피로를 넘어, 당신만의 게임을 찾아드립니다."

> Steam의 폭발적 게임 증가(약 12.3만 개) 속에서 플레이어들의 선택 피로를 해결하기 위한 하이브리드 추천 시스템



## 🎯 핵심 아이디어

**협업 필터링 + LLM 오케스트레이션**

- 사용자의 플레이 데이터 기반 협업 필터링으로 **개인화된 후보 생성**
- LLM Agent가 사용자의 자연어 의도를 파악하고 **복합적인 요구를 처리**
- 3-Stage 파이프라인으로 **정확도와 속도를 동시에 확보**

---

## 🔧 주요 기술 스택

| 분야 | 기술 |
|------|------|
| **추천 모델** | EASE, LightGCN, DCN v2, XGBoost |
| **LLM & Agent** | Naver Clova + ReAct Agent |
| **Backend** | FastAPI, PostgreSQL, Redis |
| **Infra** | Docker Compose, GCP, GitHub Actions |
| **Frontend** | React, TypeScript, Tailwind CSS |
| **자동화** | Prefect (데이터 수집 및 모델 재학습) |

---

## 📂 프로젝트 구조

```
project/
├── backend/                    # FastAPI 서버 & 오케스트레이터
│   ├── alembic/                # DB 마이그레이션
│   ├── app/
│   │  ├── core/                # 인프라 (DB, Redis, 설정, 로깅)
│   │  ├── domains/
│   │  │   ├── chat/            # 챗봇 (LLM, Agent, Tools, Reranker)
│   │  │   ├── game/            # 게임 CRUD
│   │  │   ├── recommendation/  # 추천 (ML + 벡터검색)
│   │  │   ├── steam/           # Steam API 연동
│   │  │   └── user/            # 유저 CRUD
│   │  ├── routers/             # API 라우터
│   │  ├── services/            # ML 추론 (BentoML)
│   │  └── data/                # 게임 메타데이터 시드
│   ├── scripts/                # 데이터 로딩/벡터 관리 스크립트
│   ├── nginx/                  # Nginx 설정
│   └── Dockerfile
│
├── frontend/                  # React UI
│   ├── src/
│   │   ├── components/       # UI 컴포넌트
│   │   ├── pages/           # 페이지 (메인, 채팅)
│   │   └── hooks/           # 커스텀 훅
│   └── vite.config.ts
│
├── ml_rec/                    # 추천 모델 파이프라인
│   ├── scripts/
│   │   ├── stage1_ease.py      # EASE 모델
│   │   ├── stage1_lightgcn.py  # LightGCN 모델
│   │   ├── stage2_dcn.py       # DCN v2 모델
│   │   └── stage3_xgboost.py   # XGBoost 모델
│   ├── bentoml_service.py      # BentoML 서빙
│   └── Dockerfile.bentoml
│
├── ml_llm/                    # LLM & RAG 파이프라인
│   ├── raw_to_doc.py          # 데이터 문서화 v1
│   ├── doc_to_vector_local.py # 임베딩 v1
│   └── rag_embedding/         # 데이터 문서화 임베딩 v2
│
├── configs/                   # 설정 파일
│   ├── backend/              # Backend 환경변수
│   └── frontend/             # Frontend 환경변수
│
├── scripts/                   # 자동화 스크립트
│   ├── backup_ml_rec_to_gcs.py
│   └── download_ml_rec_from_gcs.py
│
├── docker-compose.yml         # 로컬 개발 환경
├── docker-compose.prod.yml    # 프로덕션 환경
└── PROJECT_REPORT.md          # 상세 프로젝트 보고서
```

---

## 🚀 빠른 시작 (Quick Start)

### 사전 요구사항
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 1️⃣ 환경 설정
```bash
# .env 파일 생성
cp .env.example .env

# 필요한 환경변수 설정
# - GCP 인증키
# - Steam API 키
# - LLM API 키 등
```

### 2️⃣ 로컬 개발 (Docker)
```bash
# 전체 서비스 시작
docker-compose up -d

# 확인: http://localhost:3000 (Frontend)
#      http://localhost:8000/docs (Backend API)
```

### 3️⃣ 수동 설정 (Python 환경)
```bash
# Backend 설치
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Frontend 설치
cd ../frontend
npm install
npm run dev
```

---

## 📊 3-Stage 추천 파이프라인

```
사용자 데이터
    ↓
[Stage 1] 후보 생성 (200개) - EASE + LightGCN (50:50 앙상블)
    ↓
[Stage 2] 품질 보정 (100개) - DCN v2 (메타데이터 활용)
    ↓
[Stage 3] 최종 선정 (10개) - XGBoost (트렌드 반영)
    ↓
최종 추천 결과
```

**성능 지표:**
- Hit@10: 63.3% (EASE 단일 모델)
- Recall@10: 55.0% (3-Stage 파이프라인)
- 추론 시간: ~100ms (신규), ~10ms (캐시)

---

## 🤖 LLM 오케스트레이션

ReAct Agent 패턴을 활용한 의도 파악 및 도구 실행:

1. **Intent Classification**: 사용자 의도를 `추천` / `검색` / `일반 대화`로 분류
2. **Tool Selection**: 적절한 도구 선택 (추천 엔진, RAG 검색, etc.)
3. **Reasoning**: 단계적 추론으로 복합 질의 처리
4. **Orchestration**: FastAPI가 전체 흐름 제어

**예시:**
> "젤다 같은데 좀 더 어두운 분위기의 게임 없어?"
> → 추천 + 검색 도구 동시 활용 → 최적 결과 제공

---

## 🗄️ ML 파이프라인 (Prefect 자동화)

> **Note**: ML 파이프라인 구현체는 [backend/ml_pipeline 브랜치의 ml_pipeline](https://github.com/boostcampaitech8/pro-recsys-finalproject-recsys-05/tree/backend/ml_pipeline/ml_pipeline) 디렉토리에서 확인하실 수 있습니다.

```yaml
매주 월요일 AM 2시:
  1. Steam Chart에서 메타데이터 수집
  2. 게임 리뷰 및 유저 상호작용 추가 수집
  3. EASE 모델 전체 재학습 (매주)
  4. LightGCN 증분 학습 (매주) / 전체 재학습 (월 1회)
  5. 벡터 임베딩 업데이트
```

---

## 👥 팀원 소개

| 이름 / 역할 | 담당 영역 | GitHub |
|------------|----------|--------|
| **최평화 (PM · AI Engineer · Frontend)** | Frontend (React), ML Training, BentoML 서빙 | [c-peace](https://github.com/c-peace) |
| **김병주 (Backend · Infra)** | GCP, Docker, FastAPI, CI/CD | [rlaqudwn1](https://github.com/rlaqudwn1) |
| **손병국 (LLM Agent)** | Chatbot 설계 및 구현 | [bson343](https://github.com/bson343) |
| **이지원 (RAG)** | RAG 검색 및 Agent Tool | [wonl1](https://github.com/wonl1) |
| **양성호 (Data Engineer)** | Steam Crawling, Prefect 자동화 | [she2psh](https://github.com/she2psh) |

---

## 📈 주요 성과

✅ **3-Stage 파이프라인**: 후보군 프로세스 구현

✅ **LLM 오케스트레이션**: 자연어 기반 복합 질의 처리

✅ **자동화 파이프라인**: 주간/월간 데이터 수집 및 모델 재학습

✅ **Docker 모듈화**: 배포 및 관리 용이한 컨테이너 환경

✅ **실시간 캐싱**: Redis를 활용한 응답 속도 최적화 (10ms)


---

## ⚠️ 주의사항 및 면책 조항 (Disclaimer)
이 프로젝트는 학습 및 연구 목적으로 제작되었습니다. 사용자는 아래 내용을 숙지해야 합니다.

1. **Steam Web API Usage**
   이 애플리케이션은 Steam Web API를 사용하지만, Valve Corporation에 의해 승인되거나 제휴되지 않았습니다.

2. **Web Scraping Warning**
   이 프로젝트에는 Steam 상점 페이지에 대한 크롤링(Scraping) 코드가 포함되어 있습니다.
   *   **과도한 요청 금지**: 짧은 시간 내에 과도한 요청(Request)을 보낼 경우 Steam 서버로부터 IP 차단(Ban)을 당할 수 있습니다.
   *   **책임 소재**: 제공된 코드를 사용하여 발생하는 계정 정지, IP 차단, 법적 문제에 대한 책임은 전적으로 사용자 본인에게 있습니다. 코드 내의 sleep 시간(딜레이)을 임의로 삭제하지 마십시오.

3. **Data Privacy**
   수집된 유저 데이터(Steam ID 등)는 개인정보 보호법 및 GDPR에 따라 보호받아야 합니다. 이 코드를 통해 수집한 데이터를 무단으로 배포하거나 상업적으로 이용하지 마십시오.

---

📌 **Project Completed**: Feb 2026  
🏫 **Naver Boostcamp AI Tech 8th | recsys-05 – Data Tailor**

---

<div align="center">
  <img src="https://steamcommunity.com/public/shared/images/header/globalheader_logo.png" alt="Steam Logo" width="150" />
  <p>This project uses the Steam Web API and is not endorsed or certified by Valve Corporation.</p>
</div>

