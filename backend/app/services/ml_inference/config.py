from pathlib import Path
import os


# 환경 변수로 ml_rec 루트 경로 설정 (Docker 환경과 로컬 환경 모두 대응)
ML_REC_ROOT = Path(os.getenv("ML_REC_ROOT", "/app/ml_rec"))
MODEL_PATH = ML_REC_ROOT / "scripts" / "inference" / "saved" / "item_similarity.pkl"


def get_model_path() -> str:
    """
    모델 파일 경로 반환 (Docker/로컬 환경 자동 감지)

    우선순위:
    1. 환경 변수 ML_REC_ROOT에서 찾기 (Docker 환경)
    2. 상대 경로로 찾기 (로컬 개발 환경)

    Returns:
        모델 파일 절대 경로

    Raises:
        FileNotFoundError: 모델 파일을 찾을 수 없을 때
    """
    if MODEL_PATH.exists():
        return str(MODEL_PATH)

    # Fallback: 상대 경로 (로컬 개발용)
    fallback = (
        Path(__file__).parent.parent.parent.parent.parent
        / "ml_rec" / "scripts" / "inference" / "saved" / "item_similarity.pkl"
    )
    if fallback.exists():
        return str(fallback)

    raise FileNotFoundError(
        f"Model file not found at {MODEL_PATH} or {fallback}. "
        "Please run extract_item_similarity.py first."
    )