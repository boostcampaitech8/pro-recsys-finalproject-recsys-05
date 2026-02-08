"""
EASE와 LightGCN 후보 병합 로직
- 기존 사용자: 사전 계산된 후보 병합
- 새 사용자: 실시간 후보 생성
"""

import numpy as np
import logging
from typing import List, Dict, Set, Optional

logger = logging.getLogger(__name__)


class CandidateMerger:
    """후보 병합 클래스"""

    @staticmethod
    def merge_candidates(
        user_ease_candidates: List[Dict],
        user_lightgcn_candidates: List[Dict],
        user_interactions: Set[int],
        top_k: int = 200
    ) -> List[Dict]:
        """
        EASE와 LightGCN 후보를 병합 (역수 순위 가중치)

        Args:
            user_ease_candidates: [{"item_id": 1, "score": 0.8}, ...]
            user_lightgcn_candidates: [{"item_id": 2, "score": 0.75}, ...]
            user_interactions: 사용자가 이미 상호작용한 아이템 집합
            top_k: 반환할 후보 개수

        Returns:
            병합된 후보 리스트 (내림차순 정렬)
            [{"item_id": 1, "ease_rank": 1, "lightgcn_rank": 5, "merged_score": 0.9}, ...]
        """
        # 1. 각 모델의 랭크 정보 생성
        ease_rank_map = {}
        lightgcn_rank_map = {}

        for rank, candidate in enumerate(user_ease_candidates, 1):
            ease_rank_map[int(candidate['item_id'])] = {
                'rank': rank,
                'score': float(candidate['score'])
            }

        for rank, candidate in enumerate(user_lightgcn_candidates, 1):
            lightgcn_rank_map[int(candidate['item_id'])] = {
                'rank': rank,
                'score': float(candidate['score'])
            }

        # 2. 모든 후보 아이템 수집
        all_items = set(ease_rank_map.keys()) | set(lightgcn_rank_map.keys())

        # 3. 상호작용 이미 있는 아이템 제거
        all_items = all_items - user_interactions

        if not all_items:
            logger.warning(f"[WARN] 모든 후보가 이미 상호작용한 아이템")
            return []

        # 4. 역수 순위 가중치 계산
        merged_scores = {}

        for item_id in all_items:
            ease_info = ease_rank_map.get(item_id)
            lightgcn_info = lightgcn_rank_map.get(item_id)

            # 역수 순위: 1/rank (상위 순위가 높은 점수)
            ease_rank_score = 1.0 / ease_info['rank'] if ease_info else 0.0
            lightgcn_rank_score = 1.0 / lightgcn_info['rank'] if lightgcn_info else 0.0

            # 가중 합 (동일 가중)
            merged_score = (ease_rank_score + lightgcn_rank_score) / 2.0

            merged_scores[item_id] = {
                'item_id': item_id,
                'ease_rank': ease_info['rank'] if ease_info else 9999,
                'ease_score': ease_info['score'] if ease_info else 0.0,
                'lightgcn_rank': lightgcn_info['rank'] if lightgcn_info else 9999,
                'lightgcn_score': lightgcn_info['score'] if lightgcn_info else 0.0,
                'merged_score': merged_score
            }

        # 5. 정렬 및 상위 top_k 선택
        sorted_candidates = sorted(
            merged_scores.values(),
            key=lambda x: x['merged_score'],
            reverse=True
        )[:top_k]

        logger.info(f"[OK] 병합 완료: {len(sorted_candidates)} 후보 (상호작용 제거 후)")

        return sorted_candidates

    @staticmethod
    def generate_ease_candidates(
        ease_model: Optional[object],
        user_games: List[int],
        top_k: int = 200
    ) -> List[Dict]:
        """
        EASE 모델을 사용해 새로운 사용자를 위한 후보 생성

        Args:
            ease_model: 학습된 EASE 모델 (item_similarity.pkl)
            user_games: 사용자가 플레이한 게임 ID 리스트
            top_k: 반환할 후보 개수

        Returns:
            [{"item_id": 1, "score": 0.8}, ...] 형태의 후보 리스트
        """
        if not ease_model or not user_games:
            return []

        try:
            # EASE 모델은 보통 dict 형태: {item_id: {similar_item_id: score, ...}}
            candidate_scores = {}

            for user_item_id in user_games:
                user_item_id = int(user_item_id)
                if user_item_id not in ease_model:
                    continue

                # 사용자 게임과 유사한 게임들 추출
                similar_items = ease_model[user_item_id]

                # Dict 형태 {item_id: score} 처리
                if isinstance(similar_items, dict):
                    for item_id, score in similar_items.items():
                        item_id = int(item_id)
                        if item_id not in user_games:  # 이미 플레이한 게임 제외
                            candidate_scores[item_id] = candidate_scores.get(item_id, 0) + float(score)

            # 점수로 정렬하여 상위 top_k 선택
            sorted_items = sorted(
                candidate_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]

            candidates = [
                {"item_id": item_id, "score": score}
                for item_id, score in sorted_items
            ]

            logger.info(f"[OK] EASE 후보 생성: {len(candidates)} 개 (새 사용자)")
            return candidates

        except Exception as e:
            logger.warning(f"[WARN] EASE 후보 생성 실패: {e}")
            return []

    @staticmethod
    def generate_lightgcn_candidates(
        lightgcn_embeddings: np.ndarray,
        user_games: List[int],
        item_ids: np.ndarray,
        top_k: int = 200
    ) -> List[Dict]:
        """
        LightGCN 임베딩을 사용해 새로운 사용자를 위한 후보 생성

        Args:
            lightgcn_embeddings: Item 임베딩 (num_items x embedding_dim)
            user_games: 사용자가 플레이한 게임 ID 리스트 (external Steam IDs)
            item_ids: 임베딩 배열과 매칭되는 external item IDs (np.ndarray)
            top_k: 반환할 후보 개수

        Returns:
            [{"item_id": 1, "score": 0.8}, ...] 형태의 후보 리스트
        """
        if lightgcn_embeddings is None or item_ids is None or not user_games:
            return []

        try:
            user_games = set(int(g) for g in user_games)

            # External ID → internal index 매핑
            item_id_to_index = {int(item_id): idx for idx, item_id in enumerate(item_ids)}

            # 사용자 임베딩 = 플레이한 게임들의 임베딩 평균
            valid_indices = [
                item_id_to_index[game_id]
                for game_id in user_games
                if game_id in item_id_to_index
            ]
            if not valid_indices:
                return []

            user_embedding = lightgcn_embeddings[valid_indices].mean(axis=0)

            # 모든 아이템과의 코사인 유사도 계산
            item_scores = {}
            for idx, external_item_id in enumerate(item_ids):
                external_item_id = int(external_item_id)
                if external_item_id not in user_games:
                    # 코사인 유사도
                    item_emb = lightgcn_embeddings[idx]
                    similarity = np.dot(user_embedding, item_emb) / (
                        np.linalg.norm(user_embedding) * np.linalg.norm(item_emb) + 1e-8
                    )
                    item_scores[external_item_id] = float(similarity)

            # 상위 top_k 선택
            sorted_items = sorted(
                item_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]

            candidates = [
                {"item_id": item_id, "score": score}
                for item_id, score in sorted_items
            ]

            logger.info(f"[OK] LightGCN 후보 생성: {len(candidates)} 개 (새 사용자)")
            return candidates

        except Exception as e:
            logger.warning(f"[WARN] LightGCN 후보 생성 실패: {e}")
            return []

    @staticmethod
    def get_user_interactions(
        ease_candidates: dict,  # {user_id: [items], ...}
        user_id: str
    ) -> Set[int]:
        """
        사용자의 상호작용 아이템 추출

        Args:
            ease_candidates: 전체 EASE 후보 dict
            user_id: 사용자 ID (문자열)

        Returns:
            상호작용한 아이템 ID 집합
        """
        if user_id not in ease_candidates:
            return set()

        # EASE 후보에는 [item1, item2, ...] 형태로 저장됨
        user_items = ease_candidates[user_id]

        # 리스트의 경우
        if isinstance(user_items, list):
            if user_items and isinstance(user_items[0], dict):
                # [{"item_id": 1, "score": 0.8}, ...] 형태
                return set(int(item['item_id']) for item in user_items)
            else:
                # [1, 2, 3, ...] 형태
                return set(int(item) for item in user_items)

        return set()
