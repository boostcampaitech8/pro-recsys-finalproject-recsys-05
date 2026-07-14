"""T39 G3: seam 기계 핀 — 산문으로만 존재하던 seam 불변식을 테스트로 동결.

- S6: 임베딩 1024차원(bge-m3) — 모델 컬럼·설정 기본값 (불변식 3)
- S2: model_loader 후보 JSON 로드 스킵 유지 — 12GB OOM 방지 (불변식 2)
- stage3 계약: DCN input_dim=66 — 변경은 T36 execplan 경유

ml_rec은 backend 의존성이 아니므로(torch 등 미설치) import 대신 텍스트 핀을 쓴다.
핀이 깨졌다면 seam 문서(docs/SPEC.md §1, docs/MAINTENANCE.md §2)를 먼저 확인할 것.
"""
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_LOADER = REPO_ROOT / "ml_rec" / "scripts" / "stage4_serving" / "model_loader.py"


def _model_loader_src() -> str:
    assert MODEL_LOADER.exists(), f"S2/stage3 핀 대상 파일 이동됨: {MODEL_LOADER}"
    return MODEL_LOADER.read_text(encoding="utf-8")


def test_s6_embedding_column_is_1024():
    """S6: games.embedding pgvector 컬럼은 1024차원 (bge-m3 교체 금지)."""
    from app.domains.game.models import Game

    assert Game.__table__.c.embedding.type.dim == 1024


def test_s6_settings_embedding_dimension_default_is_1024():
    """S6: Settings 기본값도 1024 — env 오버라이드와 무관하게 클래스 계약을 동결."""
    from app.core.config import Settings

    assert Settings.model_fields["EMBEDDING_DIMENSION"].default == 1024
    assert Settings.model_fields["EMBEDDING_MODEL_NAME"].default == "BAAI/bge-m3"


def test_s2_candidate_load_skip_is_preserved():
    """S2: 후보 JSON 로드 스킵 되돌리기 금지 — 로드 시 12GB OOM (불변식 2)."""
    src = _model_loader_src()
    assert "후보 로드 스킵" in src
    assert "ease_candidates = {}" in src
    assert "lightgcn_candidates = {}" in src


def test_stage3_dcn_input_dim_is_66():
    """stage3 서빙 계약: DCN input_dim=66 — 레이아웃 변경은 T36 execplan 경유 필수."""
    src = _model_loader_src()
    assert "input_dim = 66" in src
