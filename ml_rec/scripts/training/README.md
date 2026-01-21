# Training Scripts

RecBole 기반 추천 모델 학습 스크립트

## 파일 목록

- `run_recbole_ease.py` - EASE 모델 학습 ⭐ 추천
- `run_recbole_bpr.py` - BPR 모델 학습
- `run_recbole_lightgcn.py` - LightGCN 모델 학습
- `run_recbole_neumf.py` - NeuMF 모델 학습

## 사용 방법

```bash
# EASE 모델 학습 (추천)
python run_recbole_ease.py
```

## 설정 파일

설정 파일은 `../../configs/` 폴더에 있습니다:
- `recbole_config_ease.yaml`
- `recbole_config_bpr.yaml`
- `recbole_config_lightgcn.yaml`

## 결과

학습된 모델은 `../saved/` 폴더에 저장됩니다.

자세한 내용은 [상위 README](../README.md)를 참고하세요.
