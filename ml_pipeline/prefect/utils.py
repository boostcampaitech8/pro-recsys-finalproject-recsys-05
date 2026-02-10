import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# ml_pipeline 루트 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .env 로드 (API Key 등 환경변수 설정)
# ml_pipeline의 상위 폴더(프로젝트 루트)에 있는 .env 로드
LOADED_ENV = load_dotenv(Path(BASE_DIR).parent / ".env")

def setup_gcs_auth():
    """환경변수(env)에 있는 경로만 사용하며, 상대 경로일 경우 절대 경로로 변환합니다."""
    env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not env_path:
        return

    path = Path(env_path)
    if not path.is_absolute():
        project_root = Path(BASE_DIR).parent
        abs_path = (project_root / path).resolve()
    else:
        abs_path = path

    if abs_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(abs_path)
        print(f"🔑 GCS 인증 키 설정됨: {abs_path}")
    else:
        print(f"⚠️ [Warning] GCS 키 파일을 찾을 수 없습니다: {abs_path}")

def load_config(config_path: str = "configs/gcs_config.yaml") -> Dict[str, Any]:
    """설정 파일을 로드합니다."""
    project_root = Path(BASE_DIR).parent
    abs_path = project_root / config_path

    if not abs_path.exists():
        abs_path = Path(BASE_DIR) / config_path

    if abs_path.exists():
        with open(abs_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

def get_ml_python_executable(override_path: str = None):
    """
    ML/LLM 작업을 위한 Python 인터프리터 경로를 반환합니다.
    우선순위: override_path > 환경변수(ML_PYTHON_PATH) > sys.executable
    """
    # 0. 명시적 오버라이드 경로
    if override_path and os.path.exists(override_path):
        return override_path

    # 1. 시스템 환경 변수 확인 (개발자/운영자 설정)
    env_path = os.getenv("ML_PYTHON_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    return sys.executable
