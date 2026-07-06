"""F11: 추천 점수가 메타데이터 병합 단계에서 0으로 뭉개지지 않는지 검증.

BentoML 응답과 EASE 폴백 모두 "score" 키로 점수를 반환하는데,
병합이 "combined_score"만 읽으면 모든 점수가 기본값 0이 된다.
"""
import pytest

from app.domains.recommendation import integrated_service as integrated_module
from app.domains.recommendation.integrated_service import (
    IntegratedRecommendationService,
)


class FakeGame:
    def __init__(self, app_id, name):
        self.app_id = app_id
        self.name = name
        self.header_image = "img.jpg"
        self.short_description_kr = "설명"
        self.genres_kr = ["액션"]
        self.price = 10000
        self.release_date = "1 Jan, 2024"


class FakeSteamService:
    async def get_user_data(self, steam_id, save_to_file=False):
        return {"games": [{"appid": 10}, {"appid": 20}], "is_playtime_public": True}


class FakeGameRepository:
    def __init__(self, games):
        self._games = games

    async def get_games_by_app_ids(self, app_ids):
        return [g for g in self._games if g.app_id in app_ids]


class FakeCache:
    async def get_online(self, steam_id, top_k):
        return None

    async def set_online(self, steam_id, top_k, result):
        return None


def _make_service(games):
    service = IntegratedRecommendationService(
        steam_service=FakeSteamService(),
        game_repository=FakeGameRepository(games),
        recommendation_repository=None,  # save_history=False라 사용되지 않는다
        user_repository=None,
    )
    service.rec_cache = FakeCache()
    return service


def _install_fake_bentoml(monkeypatch, recommendations):
    payload = {"status": "success", "recommendations": recommendations}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            return FakeResponse()

    monkeypatch.setattr(integrated_module.httpx, "AsyncClient", FakeAsyncClient)


@pytest.mark.asyncio
async def test_bentoml_score_key_is_merged(monkeypatch):
    """BentoML이 "score" 키로만 점수를 줘도 0이 아닌 실제 점수가 병합된다."""
    _install_fake_bentoml(
        monkeypatch, [{"rank": 1, "item_id": 999, "score": 0.8731}]
    )
    service = _make_service([FakeGame(999, "Hades")])

    result = await service.recommend_from_steam(
        "76561198000000000", top_k=1, save_history=False
    )

    game = result["recommended_games"][0]
    assert game["name"] == "Hades"
    assert game["score"] == pytest.approx(0.8731)


@pytest.mark.asyncio
async def test_combined_score_takes_priority(monkeypatch):
    """3-stage 결합 점수(combined_score)가 있으면 그것을 우선 사용한다."""
    _install_fake_bentoml(
        monkeypatch,
        [{"rank": 1, "item_id": 999, "combined_score": 0.5, "score": 0.9}],
    )
    service = _make_service([FakeGame(999, "Hades")])

    result = await service.recommend_from_steam(
        "76561198000000000", top_k=1, save_history=False
    )

    assert result["recommended_games"][0]["score"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_ease_fallback_score_is_merged(monkeypatch):
    """BentoML 불가 시 EASE 폴백 결과의 score도 그대로 병합된다."""

    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            raise integrated_module.httpx.ConnectError("bentoml down")

    monkeypatch.setattr(integrated_module.httpx, "AsyncClient", FailingAsyncClient)

    class FakeModelService:
        def recommend_for_new_user(self, played_games, top_k, aggregation):
            return [{"item_id": "999", "score": 0.4242}]

    service = _make_service([FakeGame(999, "Hades")])
    service._model_service = FakeModelService()

    result = await service.recommend_from_steam(
        "76561198000000000", top_k=1, save_history=False
    )

    game = result["recommended_games"][0]
    assert game["name"] == "Hades"
    assert game["score"] == pytest.approx(0.4242)


@pytest.mark.asyncio
async def test_metadata_missing_game_still_carries_score(monkeypatch):
    """DB에 메타데이터가 없는 게임도 점수는 유지된다."""
    _install_fake_bentoml(
        monkeypatch, [{"rank": 1, "item_id": 12345, "score": 0.61}]
    )
    service = _make_service([])

    result = await service.recommend_from_steam(
        "76561198000000000", top_k=1, save_history=False
    )

    game = result["recommended_games"][0]
    assert game["name"] == "Unknown Game"
    assert game["score"] == pytest.approx(0.61)
