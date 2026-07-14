# 🌐 GCS 백업 가이드 (Week 4)

## 📊 백업 대상

```
대용량 파일들을 Google Cloud Storage(GCS)에 백업합니다.

├─ 모델 (1.4GB)
│  ├─ dcn_v2_steam.pth          (298KB)
│  └─ xgb_final_scorer.pkl      (27KB)
│
├─ 후보 데이터 (3.4GB)
│  ├─ ease_candidates.json      (1.8GB)
│  ├─ lightgcn_candidates.json  (1.8GB)
│  └─ lightgcn_embeddings.npz   (4.6MB)
│
└─ 데이터셋 (4.3GB)
   ├─ steam_optimal.inter       (9.47M)
   ├─ steam_optimal.item        (...)
   └─ steam_optimal.user        (...)

총합: 9.1GB
```

---

## ✅ 준비사항

### 1. GCS 인증 설정

**Option A: 로컬 개발 (gcloud CLI)**
```bash
gcloud auth login
gcloud auth application-default login
```

**Option B: GitHub Actions / CI/CD**
```bash
# GCS 서비스 계정 키를 Base64로 인코딩
cat gcs_key.json | base64 -w 0

# GitHub Secrets에 GCS_KEY_BASE64 설정
```

### 2. 필수 패키지 설치
```bash
pip install pyyaml google-cloud-storage
```

---

## 🚀 사용 방법

### **1️⃣ 모든 파일 백업 (첫 실행)**

```bash
# 프로젝트 루트에서 실행
python scripts/backup_ml_rec_to_gcs.py

# 예상 시간: 30-40분 (9GB)
```

**출력 예:**
```
============================================================
🚀 ML Rec → GCS 백업 시작
============================================================

📤 업로드: dcn_v2_steam.pth (0.3MB)
   로컬: /path/ml_rec/saved_models/dcn_v2_steam.pth
   GCS: gs://data-tailor-test/ml_rec/models/dcn_v2_steam.pth
✅ 업로드 완료: dcn_v2_steam.pth

📤 업로드: ease_candidates.json (1797.8MB)
   로컬: /path/ml_rec/candidates/ease_candidates.json
   GCS: gs://data-tailor-test/ml_rec/candidates/ease_candidates.json
✅ 업로드 완료: ease_candidates.json

============================================================
📊 백업 완료
   총: 8 파일
   성공: 8/8
   버킷: gs://data-tailor-test/ml_rec/
============================================================
```

---

### **2️⃣ 카테고리별 백업**

```bash
# 모델만 백업 (빠름)
python scripts/backup_ml_rec_to_gcs.py models

# 후보 데이터만 백업 (3.4GB)
python scripts/backup_ml_rec_to_gcs.py candidates

# 데이터셋만 백업 (4.3GB)
python scripts/backup_ml_rec_to_gcs.py dataset
```

---

### **3️⃣ 새 환경에서 다운로드**

```bash
# GCS 인증 설정
gcloud auth login

# 모든 파일 다운로드
python scripts/download_ml_rec_from_gcs.py

# 예상 시간: 20-30분 (9GB)
```

**출력 예:**
```
============================================================
🚀 GCS → ML Rec 다운로드 시작
============================================================

📥 다운로드: dcn_v2_steam.pth
   GCS: gs://data-tailor-test/ml_rec/models/dcn_v2_steam.pth
   로컬: /path/ml_rec/saved_models/dcn_v2_steam.pth
✅ 다운로드 완료: dcn_v2_steam.pth (0.3MB)

⏭️  이미 존재: lightgcn_candidates.json (1797.8MB)

============================================================
📊 다운로드 완료
   총: 7 파일
   성공: 7/7
   경로: /path/ml_rec/
============================================================
```

---

## 🔍 GCS 확인

### 업로드된 파일 확인

```bash
# 웹 브라우저
# https://console.cloud.google.com/storage/browser/data-tailor-test/ml_rec/

# 또는 CLI
gsutil ls -r gs://data-tailor-test/ml_rec/
```

---

## ⚙️ 설정 (configs/gcs_config.yaml)

```yaml
gcs:
  bucket_name: "data-tailor-test"
  project_id: "pro-recsys-finalproject-recsys-05"

ml_rec:
  data_root: "ml_rec"
  files:
    # 파일명: {local_path, upload_path}
    dcn_v2_steam.pth:
      local_path: "saved_models/dcn_v2_steam.pth"
      upload_path: "ml_rec/models/dcn_v2_steam.pth"
    # ... 더 많은 파일들
```

---

## 🔄 CI/CD 통합 (GitHub Actions)

```yaml
# .github/workflows/backup-ml-rec.yml

name: Backup ML Rec to GCS

on:
  schedule:
    - cron: '0 2 * * 0'  # 매주 일요일 새벽 2시

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Install dependencies
        run: |
          pip install pyyaml google-cloud-storage

      - name: Backup to GCS
        env:
          GCS_KEY_BASE64: ${{ secrets.GCS_KEY_BASE64 }}
        run: |
          python scripts/backup_ml_rec_to_gcs.py
```

---

## 📋 체크리스트

### 첫 실행
- [ ] GCS 인증 설정 (gcloud auth login)
- [ ] 필수 패키지 설치 (pyyaml, google-cloud-storage)
- [ ] 모든 파일 백업 (python scripts/backup_ml_rec_to_gcs.py)
- [ ] GCS 웹 콘솔에서 확인

### 새 환경 세팅
- [ ] 프로젝트 클론 (git clone)
- [ ] GCS 인증 설정 (gcloud auth login)
- [ ] 모든 파일 다운로드 (python scripts/download_ml_rec_from_gcs.py)
- [ ] 파일 확인 (ls -la ml_rec/saved_models/)

---

## 🐛 트러블슈팅

### Q: "Failed to create GCS client" 오류

**A:** GCS 인증 설정 확인
```bash
# 인증 상태 확인
gcloud auth list

# 다시 로그인
gcloud auth login
gcloud auth application-default login
```

### Q: 업로드 중단됨

**A:** 네트워크 연결 확인 후 다시 실행
```bash
# 이미 업로드된 파일은 자동으로 스킵됨
python scripts/backup_ml_rec_to_gcs.py
```

### Q: 다운로드가 너무 느림

**A:** 네트워크 속도 확인 또는 카테고리별로 분할 다운로드
```bash
# 모델만 먼저 다운로드
python scripts/download_ml_rec_from_gcs.py models

# 나중에 후보 데이터 다운로드
python scripts/download_ml_rec_from_gcs.py candidates
```

---

## 💾 비용 추정

| 항목 | 크기 | 월 비용 |
|------|------|--------|
| 저장소 | 9GB | ~$0.15 |
| 다운로드 | (1회) | 무료 |
| 업로드 | (1회) | 무료 |
| **합계** | | **~$0.15/월** |

---

## 📝 관련 문서

- [GCS 공식 문서](https://cloud.google.com/storage/docs)
- [Google Cloud Python 클라이언트](https://cloud.google.com/python/docs/reference/storage/latest)
- [프로젝트 README](../README.md)
- [Week 4 구현 문서](../ml_rec/docs/5WEEK_COMPLETE_IMPLEMENTATION_PLAN.md)

---

**Last Updated**: 2026-02-01
**By**: Claude Code
