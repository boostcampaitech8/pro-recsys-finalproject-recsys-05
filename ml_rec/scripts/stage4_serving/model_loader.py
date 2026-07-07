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
    SAVED_MODELS_DIR, CANDIDATES_DIR, DATASET_DIR,
    EASE_MODEL_FILE, EASE_MODEL_PATTERN, LIGHTGCN_MODEL_PATTERN,
    DCN_V2_MODEL_FILE, XGB_MODEL_FILE,
    EASE_CANDIDATES_FILE, LIGHTGCN_CANDIDATES_FILE,
    LIGHTGCN_EMBEDDINGS_FILE, ITEM_METADATA_FILE
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
    """EASE 모델 로드 (새로운 사용자 처리용)

    우선순위:
      1) saved_models/item_similarity_backend_format.pkl  (backend 서빙 dict — 신규-유저 EASE 후보 생성용)
      2) saved_models/item_similarity.pkl                 (구 파일; RecBole 체크포인트면 사용 불가)

    RecBole EASE 체크포인트(torch.save=ZIP)는 candidate_merger가 요구하는 포맷이 아니라
    pickle.load가 실패한다. 그 경우 조용히 None을 반환하지 않고 원인을 명확히 로깅한다.
    변환: backend/scripts/convert_ease_checkpoint.py → item_similarity_backend_format.pkl
    """
    backend_fmt = SAVED_MODELS_DIR / 'item_similarity_backend_format.pkl'
    model_path = backend_fmt if backend_fmt.exists() else (SAVED_MODELS_DIR / EASE_MODEL_FILE)
    if not model_path.exists():
        logger.warning(f"⚠️ EASE 모델 없음: {model_path} (새 사용자 처리 불가)")
        return None

    # torch.save(ZIP) 체크포인트 조기 감지 — pickle.load로는 읽을 수 없다
    try:
        with open(model_path, 'rb') as f:
            magic = f.read(2)
        if magic == b'PK':
            logger.error(
                f"❌ EASE 모델이 torch 체크포인트(ZIP)입니다: {model_path.name}. "
                f"backend/scripts/convert_ease_checkpoint.py로 변환한 "
                f"item_similarity_backend_format.pkl을 saved_models/에 두세요. (새 사용자 처리 불가)"
            )
            return None
    except Exception as e:
        logger.warning(f"⚠️ EASE 모델 매직바이트 확인 실패: {e}")

    try:
        with open(model_path, 'rb') as f:
            ease_model = pickle.load(f)
        logger.info(f"✓ EASE 모델 로드: {model_path.name}")
        return ease_model
    except Exception as e:
        logger.warning(f"⚠️ EASE 모델 로드 실패: {e}")
        return None


def load_ease_candidates():
    """EASE 후보 로드 (optional - 새 사용자는 실시간 생성)"""
    try:
        # Pickle 파일 시도 (더 빠름)
        pkl_path = CANDIDATES_DIR / 'ease_candidates.pkl'
        if pkl_path.exists():
            print("[DEBUG] EASE 후보 로드 중 (Pickle)...", flush=True)
            with open(pkl_path, 'rb') as f:
                candidates = pickle.load(f)
            logger.info(f"✓ EASE 후보 로드 (Pickle): {len(candidates)} 사용자")
            print(f"[DEBUG] EASE 후보 로드 완료: {len(candidates)} 사용자", flush=True)
            return candidates

        # Pickle이 없으면 JSON 시도
        if EASE_CANDIDATES_FILE.exists():
            print("[DEBUG] EASE 후보 로드 중 (JSON)...", flush=True)
            with open(EASE_CANDIDATES_FILE, 'r') as f:
                candidates = json.load(f)
            logger.info(f"✓ EASE 후보 로드 (JSON): {len(candidates)} 사용자")
            print(f"[DEBUG] EASE 후보 로드 완료: {len(candidates)} 사용자", flush=True)
            return candidates

        # 파일 없으면 빈 dict 반환 (새 사용자는 실시간 생성)
        logger.warning("⚠️ EASE 후보 파일 없음 - 새 사용자는 실시간 생성됨")
        print("[DEBUG] EASE 후보 파일 없음 - 새 사용자만 사용 가능", flush=True)
        return {}

    except Exception as e:
        logger.warning(f"⚠️ EASE 후보 로드 실패: {e} - 새 사용자만 사용 가능")
        print(f"[DEBUG] EASE 후보 로드 실패: {e} - 새 사용자만 사용 가능", flush=True)
        return {}


def load_lightgcn_candidates():
    """LightGCN 후보 로드 (optional - 새 사용자는 실시간 생성)"""
    try:
        # Pickle 파일 시도 (더 빠름)
        pkl_path = CANDIDATES_DIR / 'lightgcn_candidates.pkl'
        if pkl_path.exists():
            print("[DEBUG] LightGCN 후보 로드 중 (Pickle)...", flush=True)
            with open(pkl_path, 'rb') as f:
                candidates = pickle.load(f)
            logger.info(f"✓ LightGCN 후보 로드 (Pickle): {len(candidates)} 사용자")
            print(f"[DEBUG] LightGCN 후보 로드 완료: {len(candidates)} 사용자", flush=True)
            return candidates

        # Pickle이 없으면 JSON 시도
        if LIGHTGCN_CANDIDATES_FILE.exists():
            print("[DEBUG] LightGCN 후보 로드 중 (JSON)...", flush=True)
            with open(LIGHTGCN_CANDIDATES_FILE, 'r') as f:
                candidates = json.load(f)
            logger.info(f"✓ LightGCN 후보 로드 (JSON): {len(candidates)} 사용자")
            print(f"[DEBUG] LightGCN 후보 로드 완료: {len(candidates)} 사용자", flush=True)
            return candidates

        # 파일 없으면 빈 dict 반환 (새 사용자는 실시간 생성)
        logger.warning("⚠️ LightGCN 후보 파일 없음 - 새 사용자는 실시간 생성됨")
        print("[DEBUG] LightGCN 후보 파일 없음 - 새 사용자만 사용 가능", flush=True)
        return {}

    except Exception as e:
        logger.warning(f"⚠️ LightGCN 후보 로드 실패: {e} - 새 사용자만 사용 가능")
        print(f"[DEBUG] LightGCN 후보 로드 실패: {e} - 새 사용자만 사용 가능", flush=True)
        return {}


def load_lightgcn_embeddings():
    """LightGCN 임베딩 로드"""
    if not LIGHTGCN_EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(f"LightGCN 임베딩 파일 없음: {LIGHTGCN_EMBEDDINGS_FILE}")

    data = np.load(LIGHTGCN_EMBEDDINGS_FILE)
    embeddings = data['embeddings']
    item_ids = data['item_ids']  # External item IDs

    logger.info(f"✓ LightGCN 임베딩 로드: {embeddings.shape}")
    logger.info(f"✓ Item IDs 로드: {len(item_ids)} 아이템")
    return embeddings, item_ids


def load_item_metadata():
    """아이템 메타데이터 로드 (steam_optimal.item)"""
    if not ITEM_METADATA_FILE.exists():
        logger.warning(f"⚠️ 아이템 메타데이터 파일 없음: {ITEM_METADATA_FILE}")
        return {}

    try:
        item_metadata = {}
        with open(ITEM_METADATA_FILE, 'r') as f:
            # 헤더 스킵
            next(f)
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    item_id = int(parts[0])
                    popularity = float(parts[1])
                    avg_rating = float(parts[2]) if len(parts) > 2 else 0.0
                    
                    item_metadata[item_id] = {
                        'popularity': popularity,
                        'avg_rating': avg_rating
                    }
        
        logger.info(f"✓ 아이템 메타데이터 로드: {len(item_metadata)} 아이템")
        return item_metadata
        
    except Exception as e:
        logger.warning(f"⚠️ 아이템 메타데이터 로드 실패: {e}")
        return {}


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
                # CPU 환경 oneDNN 호환성: BatchNorm 제거
                # deep_modules.append(nn.BatchNorm1d(hidden_dim))
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
    import os

    # oneDNN 최적화 비활성화 (CPU matmul 호환성)
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    torch.backends.mkldnn.enabled = False

    model_path = SAVED_MODELS_DIR / DCN_V2_MODEL_FILE
    if not model_path.exists():
        raise FileNotFoundError(f"DCN v2 모델 없음: {model_path}")

    # 모델 아키텍처 정의
    DCNv2 = _build_dcn_v2_architecture()

    # 모델 생성 및 가중치 로드
    input_dim = 66  # Week 3에서 학습한 차원
    model = DCNv2(input_dim=input_dim, deep_layers=(256, 128, 64), cross_layers=3, dropout_rate=0.1)

    # GPU 사용 가능시 사용
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)

    # 모델 파일이 dict 형식인 경우 (model_state_dict 포함)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'], strict=False)
    else:
        # 직접 state_dict인 경우
        model.load_state_dict(checkpoint, strict=False)

    model = model.to(device)
    # CPU 환경 oneDNN 호환성: double precision 사용
    model = model.double()
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
    print("=" * 50, flush=True)
    print("[DEBUG] load_all_models() 시작됨!", flush=True)
    print("=" * 50, flush=True)
    logger.info("=" * 50)
    logger.info("모델 로드 시작...")
    logger.info("=" * 50)

    try:
        # EASE 모델 로드 (새 사용자 처리용)
        print("[DEBUG] EASE 모델 로드 중...", flush=True)
        ease_model = load_ease_model()

        # 후보 로드 (임시로 스킵 - 새 사용자는 실시간 생성 가능)
        print("[DEBUG] ⚠️ 후보 로드 스킵 (새 사용자는 실시간 생성됨)", flush=True)
        ease_candidates = {}
        lightgcn_candidates = {}
        
        # 아이템 메타데이터 로드
        print("[DEBUG] 아이템 메타데이터 로드 중...", flush=True)
        item_metadata = load_item_metadata()
        
        print("[DEBUG] LightGCN 임베딩 로드 중...", flush=True)
        lightgcn_embeddings, item_ids = load_lightgcn_embeddings()

        # 모델 로드
        print("[DEBUG] DCN v2 모델 로드 중...", flush=True)
        dcn_v2_model, device = load_dcn_v2_model()
        print("[DEBUG] XGBoost 모델 로드 중...", flush=True)
        xgb_model = load_xgboost_model()

        logger.info("=" * 50)
        logger.info("✅ 모든 모델 로드 완료!")
        logger.info("=" * 50)
        print("[DEBUG] ✅ 모든 모델 로드 완료!", flush=True)

        return {
            'ease_model': ease_model,
            'ease_candidates': ease_candidates,
            'lightgcn_candidates': lightgcn_candidates,
            'item_metadata': item_metadata,
            'lightgcn_embeddings': lightgcn_embeddings,
            'item_ids': item_ids,
            'dcn_v2_model': dcn_v2_model,
            'xgb_model': xgb_model,
            'device': device
        }

    except Exception as e:
        print(f"[DEBUG] ❌ 모델 로드 실패: {e}", flush=True)
        print(f"[DEBUG] Exception type: {type(e)}", flush=True)
        import traceback
        print(f"[DEBUG] Traceback:\n{traceback.format_exc()}", flush=True)
        logger.error(f"❌ 모델 로드 실패: {e}")
        raise
