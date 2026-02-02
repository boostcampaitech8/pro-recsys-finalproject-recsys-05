"""
모델 로드 유틸
"""

import glob
import os
import torch
import pickle
import json
import numpy as np
import logging
from pathlib import Path
from .config import (
    SAVED_MODELS_DIR, CANDIDATES_DIR,
    EASE_MODEL_FILE, EASE_MODEL_PATTERN, LIGHTGCN_MODEL_PATTERN,
    DCN_V2_MODEL_FILE, XGB_MODEL_FILE,
    EASE_CANDIDATES_FILE, LIGHTGCN_CANDIDATES_FILE,
    LIGHTGCN_EMBEDDINGS_FILE
)

logger = logging.getLogger(__name__)


def find_latest_model(model_pattern):
    """최신 모델 파일 찾기"""
    pattern = str(SAVED_MODELS_DIR / model_pattern)
    model_files = glob.glob(pattern)

    if not model_files:
        raise FileNotFoundError(f"모델을 찾을 수 없음: {pattern}")

    # 최신 파일 선택
    latest_model = max(model_files, key=os.path.getmtime)
    logger.info(f"✓ 모델 로드: {Path(latest_model).name}")
    return latest_model


def load_ease_model():
    """EASE 모델 로드 (새로운 사용자 처리용)"""
    model_path = SAVED_MODELS_DIR / EASE_MODEL_FILE
    if not model_path.exists():
        logger.warning(f"⚠️ EASE 모델 없음: {model_path} (새 사용자 처리 불가)")
        return None

    try:
        with open(model_path, 'rb') as f:
            ease_model = pickle.load(f)
        logger.info(f"✓ EASE 모델 로드")
        return ease_model
    except Exception as e:
        logger.warning(f"⚠️ EASE 모델 로드 실패: {e}")
        return None


def load_ease_candidates():
    """EASE 후보 로드"""
    if not EASE_CANDIDATES_FILE.exists():
        raise FileNotFoundError(f"EASE 후보 파일 없음: {EASE_CANDIDATES_FILE}")

    with open(EASE_CANDIDATES_FILE, 'r') as f:
        candidates = json.load(f)

    logger.info(f"✓ EASE 후보 로드: {len(candidates)} 사용자")
    return candidates


def load_lightgcn_candidates():
    """LightGCN 후보 로드"""
    if not LIGHTGCN_CANDIDATES_FILE.exists():
        raise FileNotFoundError(f"LightGCN 후보 파일 없음: {LIGHTGCN_CANDIDATES_FILE}")

    with open(LIGHTGCN_CANDIDATES_FILE, 'r') as f:
        candidates = json.load(f)

    logger.info(f"✓ LightGCN 후보 로드: {len(candidates)} 사용자")
    return candidates


def load_lightgcn_embeddings():
    """LightGCN 임베딩 로드"""
    if not LIGHTGCN_EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(f"LightGCN 임베딩 파일 없음: {LIGHTGCN_EMBEDDINGS_FILE}")

    data = np.load(LIGHTGCN_EMBEDDINGS_FILE)
    embeddings = data['item_embeddings']

    logger.info(f"✓ LightGCN 임베딩 로드: {embeddings.shape}")
    return embeddings


def _build_dcn_v2_architecture():
    """DCN v2 모델 아키텍처 정의"""
    import torch.nn as nn

    class DCNv2(nn.Module):
        """DCN v2 모델: Deep + Cross Network"""

        def __init__(self, input_dim, deep_layers=(256, 128, 64), cross_layers=3, dropout_rate=0.1):
            super(DCNv2, self).__init__()

            # Deep Network
            deep_modules = []
            prev_dim = input_dim
            for hidden_dim in deep_layers:
                deep_modules.append(nn.Linear(prev_dim, hidden_dim))
                deep_modules.append(nn.BatchNorm1d(hidden_dim))
                deep_modules.append(nn.ReLU())
                deep_modules.append(nn.Dropout(dropout_rate))
                prev_dim = hidden_dim

            self.deep_network = nn.Sequential(*deep_modules)

            # Cross Network
            self.cross_layers = nn.ModuleList()
            for _ in range(cross_layers):
                self.cross_layers.append(nn.Linear(input_dim, input_dim))

            # Final output layer
            self.output_layer = nn.Linear(prev_dim + input_dim, 1)
            self.sigmoid = nn.Sigmoid()

            self.input_dim = input_dim

        def forward(self, x):
            # Deep path
            deep_output = self.deep_network(x)

            # Cross path
            cross_x = x
            for cross_layer in self.cross_layers:
                cross_x = x * cross_layer(cross_x) + cross_x

            # Combine
            combined = torch.cat([deep_output, cross_x], dim=1)
            output = self.output_layer(combined)
            output = self.sigmoid(output)

            return output

    return DCNv2


def load_dcn_v2_model():
    """DCN v2 모델 로드"""
    model_path = SAVED_MODELS_DIR / DCN_V2_MODEL_FILE
    if not model_path.exists():
        raise FileNotFoundError(f"DCN v2 모델 없음: {model_path}")

    # 모델 아키텍처 정의
    DCNv2 = _build_dcn_v2_architecture()

    # 모델 생성 및 가중치 로드
    input_dim = 64 + 64 + 3  # LightGCN(64) + EASE(64) + proxy_vars(3)
    model = DCNv2(input_dim=input_dim, deep_layers=(256, 128, 64), cross_layers=3, dropout_rate=0.1)

    # GPU 사용 가능시 사용
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=False))
    model = model.to(device)
    model.eval()

    logger.info(f"✓ DCN v2 모델 로드 (device: {device})")
    return model, device


def load_xgboost_model():
    """XGBoost 모델 로드"""
    import xgboost as xgb

    model_path = SAVED_MODELS_DIR / XGB_MODEL_FILE
    if not model_path.exists():
        raise FileNotFoundError(f"XGBoost 모델 없음: {model_path}")

    try:
        # XGBoost 네이티브 형식 (UBJSON) 로드
        model = xgb.Booster()
        model.load_model(str(model_path))
        logger.info(f"✓ XGBoost 모델 로드 (UBJSON 형식)")
    except Exception as e:
        # Pickle 형식 시도 (호환성)
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"✓ XGBoost 모델 로드 (Pickle 형식)")
        except:
            logger.error(f"❌ XGBoost 모델 로드 실패: {e}")
            raise

    return model


def load_all_models():
    """모든 모델 로드"""
    logger.info("=" * 50)
    logger.info("모델 로드 시작...")
    logger.info("=" * 50)

    try:
        # EASE 모델 로드 (새 사용자 처리용)
        ease_model = load_ease_model()

        # 후보 로드
        ease_candidates = load_ease_candidates()
        lightgcn_candidates = load_lightgcn_candidates()
        lightgcn_embeddings = load_lightgcn_embeddings()

        # 모델 로드
        dcn_v2_model, device = load_dcn_v2_model()
        xgb_model = load_xgboost_model()

        logger.info("=" * 50)
        logger.info("✅ 모든 모델 로드 완료!")
        logger.info("=" * 50)

        return {
            'ease_model': ease_model,
            'ease_candidates': ease_candidates,
            'lightgcn_candidates': lightgcn_candidates,
            'lightgcn_embeddings': lightgcn_embeddings,
            'dcn_v2_model': dcn_v2_model,
            'xgb_model': xgb_model,
            'device': device
        }

    except Exception as e:
        logger.error(f"❌ 모델 로드 실패: {e}")
        raise
