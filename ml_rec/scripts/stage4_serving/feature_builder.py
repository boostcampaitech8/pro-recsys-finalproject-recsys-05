"""
피처 엔지니어링: 사용자 및 아이템 피처 구성
"""

import numpy as np
import torch
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class FeatureBuilder:
    """피처 빌더 클래스"""

    def __init__(self, lightgcn_embeddings, item_ids=None):
        """
        Args:
            lightgcn_embeddings: shape (n_items, 64)
            item_ids: external item IDs (np.ndarray) - external ID → internal index 매핑용
        """
        self.lightgcn_embeddings = lightgcn_embeddings
        self.n_items = lightgcn_embeddings.shape[0]
        self.item_ids = item_ids

        # External ID → internal index 매핑 생성
        if item_ids is not None:
            self.item_id_to_index = {int(item_id): idx for idx, item_id in enumerate(item_ids)}
        else:
            self.item_id_to_index = {}

    def get_item_embedding(self, item_id: int) -> np.ndarray:
        """
        아이템의 LightGCN 임베딩 반환

        Args:
            item_id: 아이템 ID (external Steam ID)

        Returns:
            shape (64,) 임베딩
        """
        # External ID를 internal index로 변환
        if self.item_id_to_index:
            index = self.item_id_to_index.get(int(item_id), -1)
            if index < 0 or index >= self.n_items:
                return np.zeros(64, dtype=np.float32)
            return self.lightgcn_embeddings[index].astype(np.float32)
        else:
            # Fallback: item_ids가 없으면 item_id를 직접 인덱스로 사용 (호환성)
            if item_id < 0 or item_id >= self.n_items:
                return np.zeros(64, dtype=np.float32)
            return self.lightgcn_embeddings[item_id].astype(np.float32)

    def get_ease_embedding(self, candidate_score: float) -> np.ndarray:
        """
        EASE 스코어를 임베딩으로 변환 (간단한 방식: 스코어를 64차원으로 반복)

        Args:
            candidate_score: EASE 스코어 (0 ~ 1)

        Returns:
            shape (64,) 임베딩
        """
        # EASE는 이미 스코어 기반이므로, 간단하게 반복 확장
        ease_emb = np.full(64, candidate_score, dtype=np.float32)
        return ease_emb

    def build_ranking_features(
        self,
        user_ease_candidates: List[Dict],  # [{"item_id": 1, "score": 0.8}, ...]
        user_lightgcn_candidates: List[Dict],  # LightGCN 후보
        merged_candidates: List[Dict]  # 병합된 후보 (순서대로)
    ) -> np.ndarray:
        """
        Ranking 모델용 피처 구성

        각 후보에 대해:
        - LightGCN 임베딩 (64차원)
        - EASE/LightGCN 스코어 (2차원)

        Args:
            user_ease_candidates: EASE 후보 리스트
            user_lightgcn_candidates: LightGCN 후보 리스트
            merged_candidates: 병합된 후보 (top 200)

        Returns:
            shape (len(merged_candidates), 66) 피처 배열
                - 64: LightGCN 임베딩
                - 2: EASE/LightGCN 스코어
        """
        n_candidates = len(merged_candidates)

        # EASE/LightGCN 스코어 매핑
        ease_score_map = {int(c['item_id']): c['score'] for c in user_ease_candidates}
        lightgcn_score_map = {int(c['item_id']): c['score'] for c in user_lightgcn_candidates}

        features = []

        for rank, candidate in enumerate(merged_candidates):
            item_id = int(candidate['item_id'])

            # 1. LightGCN 임베딩
            lightgcn_emb = self.get_item_embedding(item_id)

            # 2. EASE/LightGCN 스코어 (간단한 피처)
            ease_score = ease_score_map.get(item_id, 0.0)
            lightgcn_score = lightgcn_score_map.get(item_id, 0.0)

            simple_features = np.array([ease_score, lightgcn_score], dtype=np.float32)

            # 피처 결합 (LightGCN 임베딩 + 스코어)
            feature_vec = np.concatenate([lightgcn_emb, simple_features])
            features.append(feature_vec)

        return np.array(features, dtype=np.float32)  # shape: (n_candidates, 66)

    def build_dcn_input(self, ranking_features: np.ndarray) -> torch.Tensor:
        """
        Ranking 피처를 DCN v2 입력으로 변환

        Args:
            ranking_features: shape (n_candidates, 66)

        Returns:
            torch.Tensor shape (n_candidates, 66)
        """
        return torch.from_numpy(ranking_features).float()
