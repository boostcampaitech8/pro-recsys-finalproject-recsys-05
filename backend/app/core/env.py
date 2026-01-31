from pathlib import Path
from dotenv import load_dotenv

ROOT_PATH = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_PATH / ".env"
LEGACY_ENV_PATH = ROOT_PATH / "backend" / ".env"


def load_backend_env() -> Path:
    env_path = ENV_PATH if ENV_PATH.exists() else LEGACY_ENV_PATH
    load_dotenv(dotenv_path=env_path)
    return env_path
