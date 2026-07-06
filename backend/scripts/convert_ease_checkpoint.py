"""
GCS 백업의 RecBole EASE 체크포인트(torch.save 포맷)를 백엔드 서빙용 pickle
포맷으로 변환하는 스크립트.

체크포인트(ml_rec/saved_models/item_similarity.pkl) 실물 구조:
    {
        'config': RecBole Config,
        'epoch': int, 'cur_step': int, 'best_valid_score': float,
        'state_dict': ...(EASE는 dummy),
        'other_parameter': {
            'item_similarity': np.matrix (17792, 17792) float32,
            'interaction_matrix': scipy.sparse.csr_matrix (97870, 17792) float32,
        },
        'optimizer': ...,
    }

백엔드(backend/app/services/ml_inference/inference_service.py)가 기대하는 포맷
(backend/app/data/item_similarity.pkl, 일반 pickle):
    {
        'similarity_matrix': np.ndarray (item_num, item_num) float32,
        'item_num': int,
        'id2token': np.ndarray (item_num,)   # 내부 index -> 원본 game id(문자열)
        'token2id': dict[str, int]           # 원본 game id -> 내부 index
    }

id2token/token2id는 체크포인트 안에 없으므로, 체크포인트 학습 당시와 동일한
설정(seed=2024, load_col={'inter': ['user_id', 'item_id']})으로 steam_optimal
RecBole 데이터셋을 재로드해 field2id_token / field2token_id 맵을 추출한다.
동일 seed·동일 필터링이면 아이템 개수/순서가 학습 시점과 일치해야 하며,
이 스크립트는 체크포인트 행렬 차원과 재로드한 dataset의 item_num이 일치하는지
검증한 뒤에만 저장한다.

사용법:
    backend/.venv/Scripts/python.exe backend/scripts/convert_ease_checkpoint.py
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_PATH = REPO_ROOT / "ml_rec" / "saved_models" / "item_similarity.pkl"
DATASET_DIR = REPO_ROOT / "ml_rec" / "dataset"
OUTPUT_PATH = REPO_ROOT / "backend" / "app" / "data" / "item_similarity.pkl"


def load_checkpoint():
    print(f"체크포인트 로드: {CHECKPOINT_PATH}")
    ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)

    other_param = ckpt["other_parameter"]
    item_similarity = other_param["item_similarity"]
    # np.matrix -> 일반 np.ndarray 로 변환 (백엔드는 ndarray 인덱싱을 기대)
    item_similarity = np.asarray(item_similarity, dtype=np.float32)

    return ckpt, item_similarity


def reload_dataset(ckpt):
    """체크포인트 학습 당시와 동일한 조건으로 steam_optimal 데이터셋을 재로드하여
    id2token / token2id 맵을 추출한다."""
    from recbole.config import Config
    from recbole.data import create_dataset

    ckpt_config = ckpt["config"].final_config_dict
    load_col = ckpt_config.get("load_col", {"inter": ["user_id", "item_id"]})
    seed = ckpt_config.get("seed", 2024)
    reproducibility = ckpt_config.get("reproducibility", True)

    config = Config(
        model="EASE",
        dataset="steam_optimal",
        config_dict={
            # RecBole은 내부적으로 os.path.join(data_path, dataset)을 최종 경로로 사용하므로
            # 여기서는 steam_optimal 폴더의 부모 디렉토리를 넘긴다.
            "data_path": str(DATASET_DIR),
            "load_col": load_col,
            "seed": seed,
            "reproducibility": reproducibility,
        },
    )
    print("RecBole dataset 재로드 중 (steam_optimal)...")
    dataset = create_dataset(config)
    return dataset


def main():
    if not CHECKPOINT_PATH.exists():
        print(f"오류: 체크포인트 파일이 없습니다: {CHECKPOINT_PATH}")
        sys.exit(1)

    if not DATASET_DIR.exists():
        print(f"오류: 데이터셋 디렉토리가 없습니다: {DATASET_DIR}")
        sys.exit(1)

    ckpt, item_similarity = load_checkpoint()
    ckpt_dim = item_similarity.shape[0]
    print(f"체크포인트 item_similarity 크기: {item_similarity.shape}")

    dataset = reload_dataset(ckpt)
    id2token = dataset.field2id_token["item_id"]
    token2id = dataset.field2token_id["item_id"]
    item_num = len(id2token)

    print(f"재로드한 dataset item_num: {item_num}")

    if item_num != ckpt_dim:
        print(
            f"오류: 체크포인트 행렬 차원({ckpt_dim})과 재로드한 dataset의 "
            f"item_num({item_num})이 일치하지 않습니다. 중단합니다 - "
            "RecBole 필터 설정/seed 불일치 가능성을 확인하세요."
        )
        sys.exit(1)

    print("차원 일치 확인 완료. 서빙 포맷으로 저장합니다...")

    output = {
        "similarity_matrix": item_similarity,
        "item_num": item_num,
        "id2token": np.asarray(id2token),
        "token2id": dict(token2id),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(output, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_mb = OUTPUT_PATH.stat().st_size / 1e6
    print(f"저장 완료: {OUTPUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
