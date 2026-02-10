# 📁 프로젝트 폴더 구조 (정리 완료)

**정리 완료 일시**: 2026-01-31
**상태**: ✅ 4주차 배포 준비 완료

---

## 🏗️ 현재 폴더 구조

```
ml_rec/
├── 📄 README.md                           # 메인 프로젝트 문서
├── 📄 requirements.txt                    # Python 의존성
├── 📄 .gitignore
│
├── 📁 docs/                               # ✨ 모든 문서 통합 (정리 완료)
│   ├── WEEK1_COMPLETION_REPORT.md        # 데이터 전처리 완료 보고서
│   ├── WEEK2_COMPLETION_REPORT.md        # Retrieval 모델 학습 완료 보고서
│   ├── WEEK3_COMPLETION_REPORT.md        # Ranking & Scoring 완료 보고서
│   ├── 4WEEK_IMPLEMENTATION_PLAN.md      # 4주차 배포 계획
│   ├── DATASET_README.md                 # 데이터셋 상세 설명
│   ├── model_guide.md                    # 모델 가이드
│   └── PROJECT_STRUCTURE.md              # 이 파일 (폴더 구조 설명)
│
├── 📁 dataset/
│   └── steam_optimal/                    # ✅ 최종 데이터셋 (RecBole 포맷)
│       ├── steam_optimal.inter           # 9.47M 상호작용 (317MB)
│       ├── steam_optimal.item            # 17.5K 게임 (258KB)
│       └── steam_optimal.user            # 96K 사용자 (2.4MB)
│
├── 📁 candidates/                        # Week 2 Retrieval 결과
│   ├── ease_candidates.json              # EASE Top-200 후보
│   ├── lightgcn_candidates.json          # LightGCN Top-200 후보
│   ├── ranking_train.pkl                 # Week 3 학습 데이터
│   ├── ranking_val.pkl                   # Week 3 검증 데이터
│   ├── ranking_test.pkl                  # Week 3 테스트 데이터
│   └── lightgcn_embeddings.npz           # LightGCN 64-dim 임베딩
│
├── 📁 saved_models/                      # 학습된 모델들
│   ├── EASE-steam_optimal-*.pth          # Week 2: EASE 모델 (1.3GB)
│   ├── LightGCN-steam_optimal-*.pth      # Week 2: LightGCN 모델 (111MB)
│   ├── dcn_v2_steam.pth                  # Week 3: DCN v2 모델 (298KB)
│   └── xgb_final_scorer.pkl              # Week 3: XGBoost 모델 (27KB)
│
├── 📁 configs/                           # RecBole 설정 (필수)
│   ├── recbole_ease_optimal.yaml         # EASE 학습 설정
│   └── recbole_lightgcn_optimal.yaml     # LightGCN 학습 설정
│
├── 📁 logs/                              # ✨ 통합 로그 디렉토리
│   ├── week2_retrieval/                  # Week 2 학습 로그
│   └── week3_ranking/                    # Week 3 학습 로그
│
└── 📁 scripts/                           # ✨ 단계별 정렬된 스크립트
    ├── 📁 preprocessing/                 # Week 1: 데이터 전처리 (참고용)
    │   ├── smart_filter.py               # 필터링 조합 자동 테스트
    │   ├── create_optimal_dataset.py      # 최적 데이터셋 생성
    │   ├── to_recbole_format.py           # RecBole 포맷 변환
    │   └── validate_dataset.py            # 데이터 검증
    │
    ├── 📁 stage1_retrieval/              # Week 2: Retrieval 모델 (참고용)
    │   ├── run_recbole_ease.py
    │   ├── run_recbole_lightgcn.py
    │   ├── train_retrieval_models.py
    │   ├── extract_candidates.py          # 후보 추출 메인 스크립트
    │   └── extract_candidates_simple.py   # 단순 후보 추출
    │
    ├── 📁 stage2_ranking/                # Week 3: Ranking 데이터셋 생성 (참고용)
    │   └── ranking_dataset_builder.py     # 데이터셋 빌더
    │
    ├── 📁 stage3_scoring/                # Week 3: 최종 스코어링 (참고용)
    │   ├── dcn_v2_trainer.py              # DCN v2 모델 학습
    │   └── xgboost_stacker.py             # XGBoost 스태킹
    │
    ├── 📁 stage4_serving/                # Week 4: 배포 서비스 (생성 예정)
    │   ├── bentoml_service.py             # BentoML 서비스 메인
    │   ├── fastapi_api.py                 # FastAPI 엔드포인트
    │   ├── clova_integration.py           # Clova X LLM 연동
    │   ├── docker-compose.yml             # Docker 배포 설정
    │   └── Dockerfile
    │
    └── 📁 utils/                         # 공통 유틸리티 (생성 예정)
        ├── data_loader.py
        ├── feature_engineering.py
        └── model_utils.py
```

---

## 📊 정리 결과 비교

### Step 4-5 완료 현황

| 항목 | 상태 | 설명 |
|------|------|------|
| **docs 폴더 통합** | ✅ 완료 | 6개 문서 파일 통합 |
| **스크립트 단계별 정렬** | ✅ 완료 | stage1~4 폴더 구조 |
| **불필요한 README 삭제** | ✅ 완료 | scripts 하위 문서 정리 |
| **Week 4 필수 스크립트** | ✅ 보존 | 모든 재현 필요 스크립트 유지 |

### 아직 대기 중 (Step 1-3)

| 항목 | 용량 | 상태 | 우선순위 |
|------|------|------|---------|
| `dataset/steam_filtered_k30_activity/` | ~2.5GB | 대기 | 🔴 높음 |
| `dataset/steam_filtered_kcore20/` | ~2.5GB | 대기 | 🔴 높음 |
| `dataset/steam/` (원본) | ~3.8GB | 대기 | 🔴 높음 |

**총 절감 가능**: ~8.8GB (Step 1-3 실행 시)

---

## 🔄 Week 4 재현 필수 요소

### 현재 보유 중인 파일

```
✅ 데이터: dataset/steam_optimal/ (필수)
✅ 모델: saved_models/* (필수)
✅ 후보 & 임베딩: candidates/* (필수)
✅ 설정: configs/*.yaml (필수)
✅ 스크립트: scripts/preprocessing/* (Week 1 재현용)
✅ 스크립트: scripts/stage1_retrieval/* (Week 2 재현용)
✅ 스크립트: scripts/stage2_ranking/* (Week 3 재현용)
✅ 스크립트: scripts/stage3_scoring/* (Week 3 재현용)
```

### Week 4 새로 생성할 파일

```
📄 scripts/stage4_serving/bentoml_service.py
📄 scripts/stage4_serving/fastapi_api.py
📄 scripts/stage4_serving/clova_integration.py
📄 scripts/stage4_serving/docker-compose.yml
📄 scripts/stage4_serving/Dockerfile
📁 scripts/utils/* (공통 유틸리티)
```

---

## 🚀 4주차 진행 전 체크리스트

- [x] **Step 4**: docs 폴더 문서 통합 완료
- [x] **Step 5**: scripts 단계별 정렬 완료
- [ ] **Step 1-3** (선택사항): 중간 데이터셋 삭제로 8.8GB 추가 절감
- [ ] Week 4 배포 스크립트 작성 시작

---

## 💡 노트

### 폴더 이름 컨벤션
- `stage1_retrieval/`, `stage2_ranking/`, `stage3_scoring/`, `stage4_serving/`
  - 각 주차별 작업 단계를 명확하게 표현
  - Week 3-4 진행 중에도 이전 스크립트 참고 용이

### 데이터 폴더
- **RecBole 요구사항**: `dataset/steam_optimal/` 경로는 변경 불가
- **임베딩 저장**: `candidates/lightgcn_embeddings.npz` 필수
- **후보 저장**: `candidates/{ease,lightgcn}_candidates.json` 필수

### 로그 관리
- `logs/week2_retrieval/`: EASE, LightGCN 학습 로그
- `logs/week3_ranking/`: Ranking, DCN v2, XGBoost 학습 로그
- `logs/week4_serving/`: (Week 4에서 생성) BentoML, FastAPI 로그

---

**By Claude Code** | 2026-01-31
