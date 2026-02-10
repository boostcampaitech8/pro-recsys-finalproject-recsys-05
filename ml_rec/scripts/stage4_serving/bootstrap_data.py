from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Tuple

import yaml
from google.api_core.exceptions import NotFound
from google.cloud import storage


DEFAULT_OBJECTS: Dict[str, Tuple[str, str]] = {
    "item_similarity.pkl": (
        "saved_models/item_similarity.pkl",
        "ml_rec/models/item_similarity.pkl",
    ),
    "dcn_v2_steam.pth": (
        "saved_models/dcn_v2_steam.pth",
        "ml_rec/models/dcn_v2_steam.pth",
    ),
    "xgb_final_scorer.pkl": (
        "saved_models/xgb_final_scorer.pkl",
        "ml_rec/models/xgb_final_scorer.pkl",
    ),
    "ease_candidates.json": (
        "candidates/ease_candidates.json",
        "ml_rec/candidates/ease_candidates.json",
    ),
    "lightgcn_candidates.json": (
        "candidates/lightgcn_candidates.json",
        "ml_rec/candidates/lightgcn_candidates.json",
    ),
    "lightgcn_embeddings.npz": (
        "candidates/lightgcn_embeddings.npz",
        "ml_rec/candidates/lightgcn_embeddings.npz",
    ),
    "steam_optimal.item": (
        "dataset/steam_optimal/steam_optimal.item",
        "ml_rec/dataset/steam_optimal.item",
    ),
}

REQUIRED_KEYS = (
    "item_similarity.pkl",
    "dcn_v2_steam.pth",
    "xgb_final_scorer.pkl",
    "ease_candidates.json",
    "lightgcn_candidates.json",
    "lightgcn_embeddings.npz",
    "steam_optimal.item",
)


def _load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"GCS config not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    if not isinstance(config, dict):
        raise ValueError(f"Invalid GCS config format: {path}")
    return config


def _resolve_paths(config: dict, ml_root: Path) -> Dict[str, Tuple[str, Path]]:
    files = config.get("ml_rec", {}).get("files", {})
    mapping: Dict[str, Tuple[str, Path]] = {}
    for key in REQUIRED_KEYS:
        default_local, default_blob = DEFAULT_OBJECTS[key]
        entry = files.get(key, {})
        if isinstance(entry, dict):
            local_rel = entry.get("local_path") or default_local
            blob_path = entry.get("download_path") or entry.get("upload_path") or default_blob
        else:
            local_rel = default_local
            blob_path = default_blob
        mapping[key] = (str(blob_path), ml_root / str(local_rel))
    return mapping


def _ensure_blob(client: storage.Client, bucket_name: str, blob_path: str, local_path: Path) -> None:
    if local_path.exists() and local_path.stat().st_size > 0:
        print(f"[bootstrap] OK: {local_path}")
        return

    local_path.parent.mkdir(parents=True, exist_ok=True)
    blob = client.bucket(bucket_name).blob(blob_path)
    try:
        blob.download_to_filename(str(local_path))
    except NotFound as exc:
        raise FileNotFoundError(f"Missing GCS object: gs://{bucket_name}/{blob_path}") from exc

    if local_path.stat().st_size <= 0:
        raise RuntimeError(f"Downloaded file is empty: {local_path}")
    print(f"[bootstrap] Downloaded: gs://{bucket_name}/{blob_path} -> {local_path}")


def main() -> None:
    skip = os.getenv("BENTOML_SKIP_GCS_BOOTSTRAP", "false").lower()
    if skip in {"1", "true", "yes"}:
        print("[bootstrap] Skipped by BENTOML_SKIP_GCS_BOOTSTRAP")
        return

    ml_root = Path(os.getenv("ML_REC_ROOT", "/app/ml_rec"))
    config_path = Path(os.getenv("GCS_CONFIG_PATH", "/app/configs/gcs_config.yaml"))
    config = _load_config(config_path)

    bucket_name = os.getenv("GCS_BUCKET_NAME") or config.get("gcs", {}).get("bucket_name")
    if not bucket_name:
        raise RuntimeError("GCS bucket name is missing. Set GCS_BUCKET_NAME or gcs.bucket_name in config.")

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if credentials_path and not Path(credentials_path).exists():
        raise FileNotFoundError(f"GOOGLE_APPLICATION_CREDENTIALS not found: {credentials_path}")

    mapping = _resolve_paths(config, ml_root)
    client = storage.Client()

    print(f"[bootstrap] Bucket: {bucket_name}")
    for key in REQUIRED_KEYS:
        blob_path, local_path = mapping[key]
        _ensure_blob(client, bucket_name, blob_path, local_path)

    print("[bootstrap] BentoML assets are ready.")


if __name__ == "__main__":
    main()
