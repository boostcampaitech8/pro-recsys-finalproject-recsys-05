from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[3] / "backend" / ".env"


def load_backend_env() -> Path:
    load_dotenv(dotenv_path=ENV_PATH)
    return ENV_PATH
