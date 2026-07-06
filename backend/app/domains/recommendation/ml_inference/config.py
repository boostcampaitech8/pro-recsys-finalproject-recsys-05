from pathlib import Path
import os


# 모델 파일 경로 설정 (Docker 및 로컬 환경 모두 대응)
# 우선순위: 1. backend/app/data (새로운 경로) -> 2. ml_rec (기존 경로)
# parents[3] == app/ (ml_inference -> recommendation -> domains -> app)
APP_DATA_DIR = Path(__file__).parents[3] / "data"
MODEL_PATH = APP_DATA_DIR / "item_similarity.pkl"

# 기존 경로 (호환성)
ML_REC_ROOT = Path(os.getenv("ML_REC_ROOT", "/app/ml_rec"))
LEGACY_MODEL_PATH = ML_REC_ROOT / "scripts" / "inference" / "saved" / "item_similarity.pkl"


def get_model_path() -> str:
    """
    모델 파일 경로 반환 (Docker/로컬 환경 자동 감지)

    우선순위:
    1. backend/app/data/item_similarity.pkl (새로운 경로)
    2. ml_rec/scripts/inference/saved/item_similarity.pkl (기존 경로, 호환성)

    Returns:
        모델 파일 절대 경로

    Raises:
        FileNotFoundError: 모델 파일을 찾을 수 없을 때
    """
    # 우선순위 1: 새로운 경로 (backend/app/data)
    if MODEL_PATH.exists():
        return str(MODEL_PATH)

    # 우선순위 2: 기존 경로 (ml_rec) - 호환성
    if LEGACY_MODEL_PATH.exists():
        return str(LEGACY_MODEL_PATH)

    raise FileNotFoundError(
        f"Model file not found at {MODEL_PATH} or {LEGACY_MODEL_PATH}. "
        "Please download item_similarity.pkl first."
    )