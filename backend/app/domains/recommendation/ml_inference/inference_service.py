"""
게임 추천 서비스

새로운 사용자의 게임 플레이 기록을 입력받아 추천을 생성하는 서비스입니다.
아이템 유사도 기반 방식으로 Cold Start 문제를 해결합니다.
"""

import numpy as np
import pickle
from typing import List, Dict, Tuple
import os
from app.core.logger import logger
from .config import get_model_path


class GameRecommendationService:
    """
    게임 추천 서비스 클래스

    아이템 유사도 행렬을 사용하여 사용자의 게임 플레이 기록을 기반으로
    새로운 게임을 추천합니다.
    """

    def __init__(self, similarity_data_path=None):
        """
        서비스 초기화

        Args:
            similarity_data_path: 아이템 유사도 데이터 파일 경로 (None이면 자동 감지)
        """
        logger.info("추천 서비스 초기화 중...")

        # 경로가 지정되지 않으면 자동 감지
        if similarity_data_path is None:
            similarity_data_path = get_model_path()

        # 유사도 데이터 로드
        with open(similarity_data_path, 'rb') as f:
            data = pickle.load(f)

        self.similarity_matrix = data['similarity_matrix']
        self.item_num = data['item_num']
        self.id2token = data['id2token']
        self.token2id = data['token2id']

        logger.info("✓ 서비스 준비 완료")
        logger.info(f"  - 아이템 수: {self.item_num}")
        logger.info(f"  - 유사도 행렬 크기: {self.similarity_matrix.shape}")

    def recommend_for_new_user(
        self,
        played_games: List[str],
        top_k: int = 10,
        aggregation: str = 'weighted_sum'
    ) -> List[Dict[str, float]]:
        """
        새로운 사용자에게 게임을 추천합니다.

        Args:
            played_games: 사용자가 플레이한 게임 ID 리스트 (원본 ID)
            top_k: 추천할 게임 개수
            aggregation: 점수 집계 방식
                - 'weighted_sum': 유사도의 가중 합
                - 'max': 최대 유사도
                - 'mean': 평균 유사도

        Returns:
            추천 게임 리스트 [{'item_id': str, 'score': float}, ...]
        """
        # 1. 원본 ID를 내부 ID로 변환
        played_item_ids = []
        unknown_games = []

        for game_id in played_games:
            if game_id in self.token2id:
                played_item_ids.append(self.token2id[game_id])
            else:
                unknown_games.append(game_id)

        if unknown_games:
            logger.warning(f"경고: 알 수 없는 게임 ID {len(unknown_games)}개 (무시됨)")

        if not played_item_ids:
            logger.error("오류: 유효한 게임 ID가 없습니다.")
            return []

        # 2. 각 플레이한 게임에 대해 유사한 게임 점수 계산
        candidate_scores = np.zeros(self.item_num)

        for played_id in played_item_ids:
            similarities = self.similarity_matrix[played_id]

            if aggregation == 'weighted_sum':
                # 가중 합: 모든 플레이한 게임과의 유사도를 합산
                candidate_scores += similarities
            elif aggregation == 'max':
                # 최대값: 각 후보에 대해 가장 높은 유사도만 사용
                candidate_scores = np.maximum(candidate_scores, similarities)
            elif aggregation == 'mean':
                # 평균 (나중에 게임 수로 나눔)
                candidate_scores += similarities

        # 평균 방식인 경우 게임 수로 나눔
        if aggregation == 'mean':
            candidate_scores /= len(played_item_ids)

        # 3. 이미 플레이한 게임 제외
        candidate_scores[played_item_ids] = -np.inf
        candidate_scores[0] = -np.inf  # padding ID 제외

        # 4. Top-K 추출
        top_k_indices = np.argsort(candidate_scores)[::-1][:top_k]

        # 5. 결과 생성
        recommendations = []
        for idx in top_k_indices:
            if candidate_scores[idx] == -np.inf:
                continue

            recommendations.append({
                'item_id': self.id2token[idx],
                'score': float(candidate_scores[idx])
            })

        return recommendations

    def recommend_similar_games(
        self,
        game_id: str,
        top_k: int = 10
    ) -> List[Dict[str, float]]:
        """
        특정 게임과 유사한 게임을 추천합니다.

        Args:
            game_id: 기준 게임 ID (원본 ID)
            top_k: 추천할 게임 개수

        Returns:
            유사한 게임 리스트 [{'item_id': str, 'score': float}, ...]
        """
        if game_id not in self.token2id:
            logger.error(f"오류: 게임 ID '{game_id}'를 찾을 수 없습니다.")
            return []

        item_id = self.token2id[game_id]
        similarities = self.similarity_matrix[item_id]

        # 자기 자신 제외
        similarities[item_id] = -np.inf
        similarities[0] = -np.inf  # padding ID 제외

        # Top-K 추출
        top_k_indices = np.argsort(similarities)[::-1][:top_k]

        recommendations = []
        for idx in top_k_indices:
            if similarities[idx] == -np.inf:
                continue

            recommendations.append({
                'item_id': self.id2token[idx],
                'score': float(similarities[idx])
            })

        return recommendations

    def batch_recommend(
        self,
        users_data: List[Dict[str, List[str]]],
        top_k: int = 10
    ) -> Dict[str, List[Dict[str, float]]]:
        """
        여러 사용자에 대해 일괄 추천합니다.

        Args:
            users_data: [{'user_id': 'user1', 'played_games': ['game1', 'game2']}, ...]
            top_k: 추천할 게임 개수

        Returns:
            {user_id: [추천 리스트], ...}
        """
        results = {}

        for user_data in users_data:
            user_id = user_data['user_id']
            played_games = user_data['played_games']

            recommendations = self.recommend_for_new_user(played_games, top_k)
            results[user_id] = recommendations

        return results
