# GPU 훈련 스크립트 가이드

## 개요

EASE 평가(CPU)가 진행 중일 때 BPR과 LightGCN을 GPU에서 병렬로 훈련합니다.

- **BPR**: 베이지안 개인화 순위(Bayesian Personalized Ranking) - 임베딩 기반 협업 필터링
- **LightGCN**: 라이트 그래프 컨볼루셔널 네트워크 - 그래프 신경망 기반 추천

## 빠른 시작

### 1. 포그라운드 실행 (권장)

```bash
cd /data/ephemeral/home/pro-recsys-finalproject-recsys-05/ml_rec/scripts
python train_gpu_models.py
```

**특징:**
- 실시간 훈련 로그 확인 가능
- 에러 발생 시 즉시 파악
- Ctrl+C로 중단 가능

### 2. 백그라운드 실행 (터미널 독립)

```bash
cd /data/ephemeral/home/pro-recsys-finalproject-recsys-05/ml_rec/scripts

# 훈련 시작
nohup python train_gpu_models.py > training.log 2>&1 &

# 로그 확인
tail -f training.log

# 진행 상황 모니터링
watch -n 1 nvidia-smi
```

**특징:**
- 터미널 닫아도 계속 실행
- SSH 연결이 끊겨도 안전
- 로그 파일에 모든 출력 저장

### 3. tmux 세션 사용 (고급)

```bash
# tmux 세션 생성
tmux new-session -d -s training -c /data/ephemeral/home/pro-recsys-finalproject-recsys-05/ml_rec/scripts

# 훈련 시작
tmux send-keys -t training "python train_gpu_models.py" Enter

# 세션 확인
tmux list-sessions

# 세션 연결
tmux attach -t training

# 세션 분리 (Ctrl+B, D)
```

## 모니터링

### GPU 사용률 실시간 확인

```bash
# 1초마다 업데이트 (Ctrl+C로 종료)
watch -n 1 nvidia-smi

# 한 번만 확인
nvidia-smi

# 더 상세한 정보
nvidia-smi -i 0 -q
```

### 시스템 리소스 모니터링

```bash
# CPU와 메모리 사용률
htop

# 프로세스별 GPU 메모리
nvidia-smi pmon -c 1

# PyTorch 프로세스만
ps aux | grep python
```

### 로그 파일 확인

```bash
# 실시간 로그 추적
tail -f training.log

# 마지막 100줄 확인
tail -100 training.log

# 전체 로그 확인
cat training.log

# 특정 패턴 검색
grep "NDCG" training.log
```

## 파일 구조

```
ml_rec/
├── scripts/
│   ├── train_gpu_models.py          # 훈련 스크립트
│   ├── TRAINING_GUIDE.md             # 이 문서
│   ├── training_results/             # 훈련 결과 저장 위치
│   │   └── training_results_*.json   # 각 실행의 결과
│   ├── saved/                        # 모델 저장 위치 (RecBole 기본)
│   │   └── BPR-*.pth
│   │   └── LightGCN-*.pth
│   └── inference/
│       ├── evaluate_model_full.py    # EASE 평가 (CPU)
│       └── ...
├── configs/
│   ├── recbole_config_bpr.yaml       # BPR 설정 (GPU 활성화)
│   ├── recbole_config_lightgcn.yaml  # LightGCN 설정 (GPU 활성화)
│   └── recbole_config_ease.yaml      # EASE 설정
└── dataset/
    └── steam_filtered_k30_activity/
```

## 병렬 실행 (권장 방식)

### 터미널 1: EASE 평가 (CPU)

```bash
cd /data/ephemeral/home/pro-recsys-finalproject-recsys-05/ml_rec/scripts/inference
python evaluate_model_full.py
```

### 터미널 2: BPR & LightGCN 훈련 (GPU)

```bash
cd /data/ephemeral/home/pro-recsys-finalproject-recsys-05/ml_rec/scripts
python train_gpu_models.py
```

### 터미널 3: 모니터링

```bash
# GPU 사용률 확인
watch -n 1 nvidia-smi

# 또는 시스템 리소스 전체 확인
htop
```

이 방식으로 실행하면:
- **CPU 100% 활용**: EASE 평가 진행
- **GPU 100% 활용**: BPR/LightGCN 훈련 진행
- 총 실행 시간 단축 가능

## 훈련 설정 커스터마이징

### BPR 설정 수정

`ml_rec/configs/recbole_config_bpr.yaml`에서:

```yaml
# 에포크 수 (기본: 50)
epochs: 50

# 배치 크기 (기본: 2048, GPU 메모리에 따라 조정)
train_batch_size: 2048
eval_batch_size: 2048

# 워커 수 (기본: 4)
worker: 4

# 평가 모드 (기본: full - 모든 아이템 고려)
eval_args:
  mode: full
```

### LightGCN 설정 수정

`ml_rec/configs/recbole_config_lightgcn.yaml`에서:

```yaml
# GCN 레이어 수 (기본: 3)
n_layers: 3

# 에포크 수 (기본: 50)
epochs: 50

# 배치 크기
train_batch_size: 2048
eval_batch_size: 2048
```

## 결과 확인

### 훈련 결과 JSON

`scripts/training_results/training_results_*.json` 파일에 저장됩니다.

구조:
```json
{
  "timestamp": "2026-01-22T...",
  "models": {
    "BPR": {
      "model": "BPR",
      "status": "completed",
      "start_time": "...",
      "end_time": "...",
      "duration": 1234.56,
      "config_file": "recbole_config_bpr.yaml"
    },
    "LightGCN": {
      "model": "LightGCN",
      "status": "completed",
      "duration": 2345.67,
      ...
    }
  }
}
```

### 저장된 모델 파일

RecBole이 자동으로 훈련된 모델을 저장합니다:

```bash
# 모델 파일 확인
ls -lh scripts/saved/BPR-*.pth
ls -lh scripts/saved/LightGCN-*.pth

# 파일 크기 확인 (모델이 제대로 저장되었는지 확인)
du -h scripts/saved/
```

## 트러블슈팅

### GPU 메모리 부족

**에러 메시지:**
```
RuntimeError: CUDA out of memory
```

**해결 방법:**
1. 배치 크기 감소:
   ```yaml
   train_batch_size: 1024  # 2048 → 1024
   eval_batch_size: 1024
   ```

2. 워커 수 감소:
   ```yaml
   worker: 2  # 4 → 2
   ```

### GPU 감지 안 됨

**에러 메시지:**
```
No CUDA devices available
```

**확인:**
```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

**해결 방법:**
1. GPU 드라이버 확인:
   ```bash
   nvidia-smi
   ```

2. Config 파일에서 GPU 설정 확인:
   ```yaml
   device: cuda
   gpu_id: '0'
   ```

### CPU 메모리 부족

**증상:** 훈련 중 갑자기 프로세스 종료

**해결 방법:**
1. 다른 프로세스 종료:
   ```bash
   ps aux | grep python
   kill <PID>
   ```

2. 시스템 재시작

### 훈련이 매우 느림

**확인:**
```bash
# GPU 사용률이 0%인지 확인
nvidia-smi

# CPU 사용률이 높지 않은지 확인
htop
```

**해결 방법:**
- 다른 프로세스 종료
- 배치 크기 증가 (메모리 허용 시)
- 워커 수 증가

## 종료 및 정리

### 훈련 중단

```bash
# 포그라운드 실행: Ctrl+C

# 백그라운드 실행: 프로세스 종료
kill <PID>
kill %1  # 백그라운드 작업 1 번호
```

### 백그라운드 프로세스 확인

```bash
jobs
ps aux | grep train_gpu_models.py
```

### 로그 정리

```bash
# 오래된 결과 파일 삭제
rm scripts/training_results/training_results_old.json

# 훈련 로그 압축
gzip training.log
```

## FAQ

**Q: EASE 평가와 동시에 훈련해도 안전한가?**
A: 예. EASE는 CPU, BPR/LightGCN은 GPU를 사용하므로 충돌 없음.

**Q: 훈련 중간에 중단해도 복구 가능한가?**
A: 아니오. 체크포인트 기능이 없으므로 처음부터 다시 시작해야 함. 중단 전에 충분한 시간 확보 필요.

**Q: 결과 비교는 어떻게?**
A: `scripts/training_results/*.json` 파일의 duration 필드로 훈련 시간 비교 가능. 성능 메트릭은 RecBole 로그 참고.

**Q: 다음에 더 빠르게 훈련하려면?**
A: 에포크 수 감소, 배치 크기 증가, 평가 빈도 감소 등을 통해 시간 단축 가능.

## 추가 자료

- [RecBole 공식 문서](https://recbole.io/)
- [PyTorch CUDA 가이드](https://pytorch.org/docs/stable/cuda.html)
- [NVIDIA GPU 최적화](https://developer.nvidia.com/blog/tag/gpu-optimization/)
