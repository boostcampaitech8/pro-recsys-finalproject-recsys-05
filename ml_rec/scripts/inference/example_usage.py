"""
추천 서비스 사용 예시

실제 서비스에서 어떻게 사용하는지 보여주는 예시 코드입니다.
"""

from inference_service import GameRecommendationService
import pandas as pd


def example_1_new_user():
    """
    예시 1: 새로운 사용자에게 추천하기

    사용자가 플레이한 게임 목록을 입력받아 새로운 게임을 추천합니다.
    """
    print("="*60)
    print("예시 1: 새로운 사용자 추천")
    print("="*60)

    # 서비스 초기화
    service = GameRecommendationService('saved/item_similarity.pkl')

    # 사용자가 플레이한 게임 (실제로는 데이터베이스나 API에서 가져옴)
    user_played_games = ['10', '20', '30']  # 게임 ID 예시

    # 추천 생성
    recommendations = service.recommend_for_new_user(
        played_games=user_played_games,
        top_k=10,
        aggregation='weighted_sum'  # 'max' 또는 'mean'도 가능
    )

    # 결과 출력
    print(f"\n사용자가 플레이한 게임: {user_played_games}")
    print(f"\n추천 게임:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. 게임 ID: {rec['item_id']} (점수: {rec['score']:.4f})")

    return recommendations


def example_2_similar_games():
    """
    예시 2: 특정 게임과 유사한 게임 찾기

    "이 게임을 좋아한다면 이것도 좋아할 것입니다" 기능
    """
    print("\n" + "="*60)
    print("예시 2: 유사한 게임 추천")
    print("="*60)

    service = GameRecommendationService('saved/item_similarity.pkl')

    # 특정 게임 ID
    target_game = '10'  # 예시

    # 유사한 게임 추천
    similar_games = service.recommend_similar_games(
        game_id=target_game,
        top_k=10
    )

    print(f"\n'{target_game}' 게임과 유사한 게임:")
    for i, rec in enumerate(similar_games, 1):
        print(f"  {i}. 게임 ID: {rec['item_id']} (유사도: {rec['score']:.4f})")

    return similar_games


def example_3_batch_processing():
    """
    예시 3: 여러 사용자에 대해 한번에 추천하기

    배치 처리로 효율적으로 여러 사용자에게 추천을 생성합니다.
    """
    print("\n" + "="*60)
    print("예시 3: 배치 추천")
    print("="*60)

    service = GameRecommendationService('saved/item_similarity.pkl')

    # 여러 사용자의 데이터
    users_data = [
        {
            'user_id': 'user_001',
            'played_games': ['10', '20', '30']
        },
        {
            'user_id': 'user_002',
            'played_games': ['15', '25', '35', '45']
        },
        {
            'user_id': 'user_003',
            'played_games': ['5', '10']
        }
    ]

    # 일괄 추천 생성
    batch_results = service.batch_recommend(users_data, top_k=5)

    # 결과 출력
    for user_id, recommendations in batch_results.items():
        print(f"\n{user_id}의 추천:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. 게임 ID: {rec['item_id']} (점수: {rec['score']:.4f})")

    return batch_results


def example_4_api_simulation():
    """
    예시 4: REST API 형태로 사용하기

    실제 웹 서비스에서 사용하는 것처럼 JSON 형태로 입출력
    """
    print("\n" + "="*60)
    print("예시 4: API 스타일 사용")
    print("="*60)

    service = GameRecommendationService('saved/item_similarity.pkl')

    # API 요청 형태 (JSON)
    request = {
        "user_id": "new_user_12345",
        "played_games": ["10", "20", "30"],
        "top_k": 10,
        "aggregation": "weighted_sum"
    }

    print(f"\nAPI 요청:")
    print(f"  User ID: {request['user_id']}")
    print(f"  Played Games: {request['played_games']}")
    print(f"  Top K: {request['top_k']}")

    # 추천 생성
    recommendations = service.recommend_for_new_user(
        played_games=request['played_games'],
        top_k=request['top_k'],
        aggregation=request['aggregation']
    )

    # API 응답 형태 (JSON)
    response = {
        "user_id": request['user_id'],
        "recommendations": recommendations,
        "count": len(recommendations)
    }

    print(f"\nAPI 응답:")
    print(f"  추천 수: {response['count']}")
    print(f"  추천 게임:")
    for i, rec in enumerate(response['recommendations'][:5], 1):
        print(f"    {i}. {rec['item_id']} (점수: {rec['score']:.4f})")

    return response


def example_5_with_real_game_ids():
    """
    예시 5: 실제 게임 ID를 사용한 추천

    저장된 매핑 파일을 읽어서 실제 게임 ID로 추천을 생성합니다.
    """
    print("\n" + "="*60)
    print("예시 5: 실제 게임 ID 사용")
    print("="*60)

    service = GameRecommendationService('saved/item_similarity.pkl')

    # 아이템 매핑 파일 로드
    try:
        mapping_df = pd.read_csv('saved/item_mapping.csv')
        available_games = mapping_df['original_id'].astype(str).tolist()

        print(f"\n데이터셋의 총 게임 수: {len(available_games)}")
        print(f"샘플 게임 ID: {available_games[:10]}")

        # 실제 게임 ID로 추천 생성
        if len(available_games) >= 5:
            user_games = available_games[:5]

            print(f"\n사용자가 플레이한 게임: {user_games}")

            recommendations = service.recommend_for_new_user(
                played_games=user_games,
                top_k=10,
                aggregation='weighted_sum'
            )

            print(f"\n추천 게임:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. 게임 ID: {rec['item_id']} (점수: {rec['score']:.4f})")

            return recommendations
        else:
            print("게임 수가 부족합니다.")

    except FileNotFoundError:
        print("오류: saved/item_mapping.csv 파일을 찾을 수 없습니다.")
        print("먼저 extract_item_similarity.py를 실행하세요.")


def main():
    """
    모든 예시 실행

    실제 사용 시에는 필요한 예시만 선택해서 사용하세요.
    """
    print("\n" + "#"*60)
    print("# 게임 추천 서비스 - 사용 예시")
    print("#"*60)

    try:
        # 예시 1: 새 사용자 추천
        example_1_new_user()

        # 예시 2: 유사한 게임 찾기
        example_2_similar_games()

        # 예시 3: 배치 처리
        example_3_batch_processing()

        # 예시 4: API 스타일
        example_4_api_simulation()

        # 예시 5: 실제 게임 ID 사용
        example_5_with_real_game_ids()

        print("\n" + "="*60)
        print("✓ 모든 예시 실행 완료!")
        print("="*60)

    except FileNotFoundError as e:
        print(f"\n오류: 필요한 파일을 찾을 수 없습니다.")
        print(f"상세: {e}")
        print("\n다음 단계를 순서대로 실행하세요:")
        print("  1. python run_recbole_ease.py  (모델 학습)")
        print("  2. python extract_item_similarity.py  (유사도 추출)")
        print("  3. python example_usage.py  (추천 생성)")


if __name__ == "__main__":
    main()
