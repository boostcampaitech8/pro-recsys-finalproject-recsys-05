"""
게임 추천 서비스

새로운 사용자의 게임 플레이 기록을 입력받아 추천을 생성하는 서비스입니다.
아이템 유사도 기반 방식으로 Cold Start 문제를 해결합니다.
"""

import numpy as np
import pandas as pd
import pickle
from typing import List, Dict, Tuple
import os


class GameRecommendationService:
    """
    게임 추천 서비스 클래스

    아이템 유사도 행렬을 사용하여 사용자의 게임 플레이 기록을 기반으로
    새로운 게임을 추천합니다.
    """

    def __init__(self, similarity_data_path='saved/item_similarity.pkl'):
        """
        서비스 초기화

        Args:
            similarity_data_path: 아이템 유사도 데이터 파일 경로
        """
        print("추천 서비스 초기화 중...")

        # 유사도 데이터 로드
        with open(similarity_data_path, 'rb') as f:
            data = pickle.load(f)

        self.similarity_matrix = data['similarity_matrix']
        self.item_num = data['item_num']
        self.id2token = data['id2token']
        self.token2id = data['token2id']

        print(f"✓ 서비스 준비 완료")
        print(f"  - 아이템 수: {self.item_num}")
        print(f"  - 유사도 행렬 크기: {self.similarity_matrix.shape}")

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
            print(f"경고: 알 수 없는 게임 ID {len(unknown_games)}개 (무시됨)")

        if not played_item_ids:
            print("오류: 유효한 게임 ID가 없습니다.")
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
            print(f"오류: 게임 ID '{game_id}'를 찾을 수 없습니다.")
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


def demo():
    """데모 실행"""
    print("="*60)
    print("게임 추천 서비스 데모")
    print("="*60)

    # 서비스 초기화
    service = GameRecommendationService('saved/item_similarity.pkl')

    # 아이템 매핑 정보 로드 (실제 게임 ID 확인용)
    mapping_df = pd.read_csv('saved/item_mapping.csv')
    available_games = mapping_df['original_id'].tolist()

    print(f"\n사용 가능한 게임 수: {len(available_games)}")
    print(f"샘플 게임 ID: {available_games[:10]}")

    # 예시 1: 새로운 사용자 추천
    print("\n" + "="*60)
    print("예시 1: 새로운 사용자에게 추천")
    print("="*60)

    # 무작위로 몇 개 게임 선택 (실제로는 사용자 입력)
    sample_games = np.random.choice(available_games, size=min(5, len(available_games)), replace=False).tolist()

    print(f"\n사용자가 플레이한 게임: {sample_games}")

    recommendations = service.recommend_for_new_user(
        played_games=sample_games,
        top_k=10,
        aggregation='weighted_sum'
    )

    print(f"\n추천 게임 Top-10:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. 게임 {rec['item_id']} (점수: {rec['score']:.4f})")

    # 예시 2: 특정 게임과 유사한 게임 추천
    if available_games:
        print("\n" + "="*60)
        print("예시 2: 특정 게임과 유사한 게임 추천")
        print("="*60)

        target_game = available_games[0]
        print(f"\n기준 게임: {target_game}")

        similar_games = service.recommend_similar_games(
            game_id=target_game,
            top_k=10
        )

        print(f"\n유사한 게임 Top-10:")
        for i, rec in enumerate(similar_games, 1):
            print(f"  {i}. 게임 {rec['item_id']} (유사도: {rec['score']:.4f})")

    # 예시 3: 배치 추천
    print("\n" + "="*60)
    print("예시 3: 여러 사용자 일괄 추천")
    print("="*60)

    users_data = [
        {
            'user_id': 'new_user_1',
            'played_games': sample_games[:3]
        },
        {
            'user_id': 'new_user_2',
            'played_games': sample_games[2:]
        }
    ]

    batch_results = service.batch_recommend(users_data, top_k=5)

    for user_id, recs in batch_results.items():
        print(f"\n{user_id}:")
        for i, rec in enumerate(recs[:3], 1):
            print(f"  {i}. 게임 {rec['item_id']} (점수: {rec['score']:.4f})")


def main():
    """메인 함수 - 실제 서비스 사용 예시"""

    # 서비스 초기화
    service = GameRecommendationService('saved/item_similarity.pkl')

    # 사용자 입력 (예시)
    print("\n" + "="*60)
    print("사용자 입력 기반 추천")
    print("="*60)

    # 실제로는 API 요청이나 사용자 입력에서 받아옴
    # 여기서는 예시로 하드코딩
    user_played_games = [
        # 사용자가 플레이한 게임 ID들을 여기에 입력
        # 예: ['10', '20', '30', '40', '50']
    ]

    # 매핑 파일에서 실제 게임 ID 가져오기
    mapping_df = pd.read_csv('saved/item_mapping.csv')
    available_games = mapping_df['original_id'].tolist()

    # 예시로 일부 게임 선택
    if not user_played_games:
        user_played_games = available_games[:5]

    print(f"\n입력된 게임 기록: {user_played_games}")

    # 추천 생성
    recommendations = service.recommend_for_new_user(
        played_games=user_played_games,
        top_k=20,
        aggregation='weighted_sum'
    )

    # 결과 출력
    print(f"\n추천 결과 (Top-20):")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i:2d}. 게임 ID: {rec['item_id']:10s} | 점수: {rec['score']:.4f}")

    # CSV로 저장
    output_df = pd.DataFrame(recommendations)
    output_file = 'saved/new_user_recommendations.csv'
    output_df.to_csv(output_file, index=False)
    print(f"\n✓ 결과 저장: {output_file}")


if __name__ == "__main__":
    # 데모 실행
    demo()

    # 또는 실제 서비스 사용
    # main()
