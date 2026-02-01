"""
BentoML 기반 3-Stage 추천 서비스
Stage 1: Retrieval (EASE + LightGCN) → 200 candidates
Stage 2: Ranking (DCN v2) → 100 candidates
Stage 3: Scoring (XGBoost) → 10 final recommendations
"""

import bentoml
import numpy as np
import torch
import logging
import json
from typing import List, Dict

from .model_loader import load_all_models
from .feature_builder import FeatureBuilder
from .candidate_merger import CandidateMerger
from .config import TOP_K_RETRIEVAL, TOP_K_RANKING, TOP_K_FINAL, LOG_DIR

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'recommendation_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@bentoml.service(
    name="game-recommendation-service",
    traffic={"timeout": 30},
)
class GameRecommendationService:
    """
    게임 추천 서비스

    3-Stage 파이프라인:
    1. Retrieval: EASE + LightGCN으로 200개 후보 추출
    2. Ranking: DCN v2로 100개로 축소
    3. Scoring: XGBoost로 최종 10개 선택
    """

    def __init__(self):
        """모델 및 데이터 로드"""
        logger.info("=" * 60)
        logger.info("GameRecommendationService 초기화 시작...")
        logger.info("=" * 60)

        try:
            # 모든 모델 로드
            models = load_all_models()

            self.ease_model = models['ease_model']  # 새 사용자 처리용
            self.ease_candidates = models['ease_candidates']
            self.lightgcn_candidates = models['lightgcn_candidates']
            self.lightgcn_embeddings = models['lightgcn_embeddings']
            self.dcn_v2_model = models['dcn_v2_model']
            self.xgb_model = models['xgb_model']
            self.device = models['device']

            # Helper 초기화
            self.feature_builder = FeatureBuilder(self.lightgcn_embeddings)
            self.candidate_merger = CandidateMerger()

            logger.info("✅ GameRecommendationService 초기화 완료!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            raise

    @bentoml.api
    def recommend(
        self,
        user_id: str,
        user_games: List[int],
        top_k: int = 10
    ) -> Dict:
        """
        사용자에게 게임 추천

        Args:
            user_id: 사용자 ID (Steam ID)
            user_games: 사용자가 이미 플레이한 게임 ID 리스트
            top_k: 반환할 추천 게임 개수 (기본 10)

        Returns:
            {
                "status": "success",
                "user_id": "76561198...",
                "recommendations": [
                    {
                        "rank": 1,
                        "item_id": 123,
                        "game_id": 123,
                        "score": 0.95,
                        "source": "dcn_v2+xgb"
                    },
                    ...
                ],
                "metadata": {
                    "retrieval_candidates": 200,
                    "ranking_candidates": 100,
                    "final_candidates": 10,
                    "processing_time_ms": 450
                }
            }
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"추천 요청: user_id={user_id}, top_k={top_k}")
            logger.info(f"{'='*60}")

            # 사용자 상호작용 아이템 집합
            user_interactions = set(user_games)

            # =========================================================================
            # Stage 1: Retrieval (EASE + LightGCN) → 200 candidates
            # =========================================================================
            logger.info("\n[Stage 1] Retrieval 시작...")

            # 사용자의 EASE 및 LightGCN 후보 추출
            user_ease_candidates = self.ease_candidates.get(user_id, [])
            user_lightgcn_candidates = self.lightgcn_candidates.get(user_id, [])

            # 새로운 사용자 처리 (사전 계산된 후보가 없는 경우)
            is_new_user = False
            if not user_ease_candidates:
                logger.info(f"ℹ️ 새 사용자 감지 ({user_id}): EASE 후보 실시간 생성")
                user_ease_candidates = self.candidate_merger.generate_ease_candidates(
                    self.ease_model,
                    user_games,
                    top_k=TOP_K_RETRIEVAL
                )
                is_new_user = True

            if not user_lightgcn_candidates:
                logger.info(f"ℹ️ 새 사용자 감지 ({user_id}): LightGCN 후보 실시간 생성")
                user_lightgcn_candidates = self.candidate_merger.generate_lightgcn_candidates(
                    self.lightgcn_embeddings,
                    user_games,
                    top_k=TOP_K_RETRIEVAL
                )
                is_new_user = True

            if not user_ease_candidates or not user_lightgcn_candidates:
                logger.warning(f"⚠️ 사용자 {user_id}에 대한 후보 생성 실패")
                return {
                    "status": "error",
                    "error": f"후보 생성 실패: user_id={user_id}",
                    "user_id": user_id
                }

            # 후보 병합
            retrieval_candidates = self.candidate_merger.merge_candidates(
                user_ease_candidates=user_ease_candidates,
                user_lightgcn_candidates=user_lightgcn_candidates,
                user_interactions=user_interactions,
                top_k=TOP_K_RETRIEVAL
            )

            logger.info(f"✓ Retrieval 완료: {len(retrieval_candidates)} 후보")

            if len(retrieval_candidates) == 0:
                logger.warning(f"⚠️ 추가할 수 있는 게임이 없음 (모두 플레이함)")
                return {
                    "status": "error",
                    "error": "추가할 수 있는 게임이 없음",
                    "user_id": user_id
                }

            # =========================================================================
            # Stage 2: Ranking (DCN v2) → 100 candidates
            # =========================================================================
            logger.info("\n[Stage 2] Ranking 시작...")

            # 랭킹 피처 구성
            ranking_features = self.feature_builder.build_ranking_features(
                user_ease_candidates=user_ease_candidates,
                user_lightgcn_candidates=user_lightgcn_candidates,
                merged_candidates=retrieval_candidates
            )
            logger.info(f"✓ 피처 구성 완료: {ranking_features.shape}")

            # DCN v2 점수 계산
            with torch.no_grad():
                dcn_input = self.feature_builder.build_dcn_input(ranking_features)
                dcn_input = dcn_input.to(self.device)
                dcn_scores = self.dcn_v2_model(dcn_input).cpu().numpy().flatten()
            logger.info(f"✓ DCN v2 스코어 계산 완료: {dcn_scores.shape}")

            # 상위 TOP_K_RANKING 선택
            ranking_indices = np.argsort(-dcn_scores)[:TOP_K_RANKING]
            ranking_candidates = [
                {
                    **retrieval_candidates[i],
                    'dcn_score': float(dcn_scores[i])
                }
                for i in ranking_indices
            ]
            logger.info(f"✓ Ranking 완료: {len(ranking_candidates)} 후보")

            # =========================================================================
            # Stage 3: Scoring (XGBoost) → 10 final recommendations
            # =========================================================================
            logger.info("\n[Stage 3] Scoring 시작...")

            # XGBoost 입력 피처 구성
            xgb_features = np.array([
                [
                    c['dcn_score'],  # DCN 점수
                    c['ease_score'],  # EASE 점수
                    c['lightgcn_score'],  # LightGCN 점수
                    np.exp(-ranking_indices.tolist().index(idx) / len(ranking_candidates)),  # 순위 가중
                    (c['ease_score'] + c['lightgcn_score']) / 2.0  # 평균 점수
                ]
                for idx, c in enumerate(ranking_candidates)
            ], dtype=np.float32)

            # XGBoost 점수
            xgb_scores = self.xgb_model.predict_proba(xgb_features)[:, 1]
            logger.info(f"✓ XGBoost 점수 계산 완료: {xgb_scores.shape}")

            # 상위 top_k 선택
            final_k = min(top_k, len(ranking_candidates))
            final_indices = np.argsort(-xgb_scores)[:final_k]

            final_recommendations = []
            for rank, idx in enumerate(final_indices, 1):
                candidate = ranking_candidates[idx]
                final_recommendations.append({
                    'rank': rank,
                    'item_id': int(candidate['item_id']),
                    'game_id': int(candidate['item_id']),  # 호환성
                    'dcn_score': float(candidate['dcn_score']),
                    'xgb_score': float(xgb_scores[idx]),
                    'combined_score': float((candidate['dcn_score'] + xgb_scores[idx]) / 2.0),
                    'source': 'dcn_v2+xgb'
                })

            logger.info(f"✓ Scoring 완료: {len(final_recommendations)} 최종 추천")

            # =========================================================================
            # 응답 생성
            # =========================================================================
            processing_time = (time.time() - start_time) * 1000  # ms

            logger.info(f"\n{'='*60}")
            logger.info(f"✅ 추천 완료 ({processing_time:.1f}ms)")
            logger.info(f"{'='*60}\n")

            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': final_recommendations,
                'metadata': {
                    'retrieval_candidates': len(retrieval_candidates),
                    'ranking_candidates': len(ranking_candidates),
                    'final_candidates': len(final_recommendations),
                    'is_new_user': is_new_user,
                    'processing_time_ms': round(processing_time, 1)
                }
            }

        except Exception as e:
            logger.error(f"❌ 추천 실패: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'user_id': user_id
            }

    @bentoml.api
    def health_check(self) -> Dict:
        """헬스 체크"""
        return {
            'status': 'healthy',
            'service': 'game-recommendation-service',
            'models_loaded': True
        }
