from pathlib import Path
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, urlunparse

ROOT_PATH = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_PATH / ".env"
CONFIG_ENV_PATH = ROOT_PATH / "configs" / "backend" / ".env"
LEGACY_ENV_PATH = ROOT_PATH / "backend" / ".env"

def _env_has_key(path: Path, key: str) -> bool:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(f"{key}="):
                return True
    except FileNotFoundError:
        return False
    return False


def _is_running_in_docker() -> bool:
    if os.path.exists("/.dockerenv"):
        return True
    cgroup_path = "/proc/1/cgroup"
    if os.path.exists(cgroup_path):
        try:
            content = Path(cgroup_path).read_text(encoding="utf-8")
            return "docker" in content or "kubepods" in content
        except Exception:
            return False
    return False


def _swap_host(url: str, new_host: str) -> str:
    parsed = urlparse(url)
    if not parsed.hostname:
        return url
    netloc = parsed.netloc.replace(parsed.hostname, new_host)
    return urlunparse(parsed._replace(netloc=netloc))


def _patch_service_urls_for_docker() -> None:
    if not _is_running_in_docker():
        return

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        if parsed.hostname in ("localhost", "127.0.0.1"):
            os.environ["DATABASE_URL"] = _swap_host(db_url, "db")

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        parsed = urlparse(redis_url)
        if parsed.hostname in ("localhost", "127.0.0.1"):
            os.environ["REDIS_URL"] = _swap_host(redis_url, "redis")


def resolve_env_path(required_key: str | None = "DATABASE_URL") -> Path:
    candidates = [ENV_PATH, CONFIG_ENV_PATH, LEGACY_ENV_PATH]
    for path in candidates:
        if path.exists():
            if required_key is None or _env_has_key(path, required_key) or os.getenv(required_key):
                return path
    for path in candidates:
        if path.exists():
            return path
    return CONFIG_ENV_PATH


def load_backend_env() -> Path:
    env_path = resolve_env_path()
    load_dotenv(dotenv_path=env_path)
    _patch_service_urls_for_docker()
    return env_path
