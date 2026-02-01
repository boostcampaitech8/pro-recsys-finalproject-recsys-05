"""
BentoML 서비스 설정 파일
"""

from pathlib import Path

# 기본 경로
BASE_PATH = Path.cwd()

# 모델 경로
SAVED_MODELS_DIR = BASE_PATH / 'saved_models'
CANDIDATES_DIR = BASE_PATH / 'candidates'

# 모델 파일명
EASE_MODEL_FILE = 'item_similarity.pkl'
EASE_MODEL_PATTERN = 'EASE*.pth'
LIGHTGCN_MODEL_PATTERN = 'LightGCN*.pth'
DCN_V2_MODEL_FILE = 'dcn_v2_steam.pth'
XGB_MODEL_FILE = 'xgb_final_scorer.pkl'

# 후보 파일명
EASE_CANDIDATES_FILE = CANDIDATES_DIR / 'ease_candidates.json'
LIGHTGCN_CANDIDATES_FILE = CANDIDATES_DIR / 'lightgcn_candidates.json'
LIGHTGCN_EMBEDDINGS_FILE = CANDIDATES_DIR / 'lightgcn_embeddings.npz'
RANKING_TRAIN_FILE = CANDIDATES_DIR / 'ranking_train.pkl'

# 하이퍼파라미터
TOP_K_RETRIEVAL = 200
TOP_K_RANKING = 100
TOP_K_FINAL = 10

# 모델 설정
DCN_V2_CONFIG = {
    'feature_dim': 64 + 64 + 3,  # LightGCN(64) + EASE(64) + proxy_vars(3)
    'deep_layers': [256, 128, 64],
    'cross_layers': 3,
    'dropout': 0.1,
    'batch_norm': True
}

XGB_CONFIG = {
    'n_estimators': 100,
    'max_depth': 5,
    'learning_rate': 0.1,
    'device': 'cuda:0'
}

# 로깅
LOG_DIR = BASE_PATH / 'logs' / 'week4_serving'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# API 설정
API_PORT = 3000
API_HOST = '0.0.0.0'
