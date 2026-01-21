"""
EASE 모델을 사용한 추론 스크립트

학습된 EASE 모델을 로드하여 사용자별 Top-K 아이템 추천을 생성합니다.
"""

import torch
import pandas as pd
from recbole.config import Config
from recbole.data import create_dataset, data_preparation
from recbole.utils import init_logger, get_model, get_trainer, init_seed
import pickle
import os


def load_model_and_data(model_file, config_file_list):
    """
    학습된 모델과 데이터셋을 로드합니다.

    Args:
        model_file: 학습된 모델 파일 경로 (.pth)
        config_file_list: 설정 파일 리스트

    Returns:
        model: 로드된 모델
        dataset: 데이터셋
        config: 설정 객체
    """
    # 설정 로드
    config = Config(model='EASE', config_file_list=config_file_list)
    init_seed(config['seed'], config['reproducibility'])

    # 로거 초기화
    init_logger(config)

    # 데이터셋 로드
    dataset = create_dataset(config)

    # 모델 로드
    model = get_model(config['model'])(config, dataset).to(config['device'])

    # 학습된 파라미터 로드
    checkpoint = torch.load(model_file, map_location=config['device'])
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()

    print(f"✓ 모델 로드 완료: {model_file}")
    print(f"✓ 데이터셋: {config['dataset']}")
    print(f"✓ 사용자 수: {dataset.user_num}")
    print(f"✓ 아이템 수: {dataset.item_num}")

    return model, dataset, config


def predict_for_user(model, dataset, config, user_id, k=10):
    """
    특정 사용자에 대한 Top-K 추천을 생성합니다.

    Args:
        model: 학습된 모델
        dataset: 데이터셋
        config: 설정 객체
        user_id: 추천을 생성할 사용자 ID (내부 ID)
        k: 추천할 아이템 개수

    Returns:
        top_k_items: Top-K 아이템 리스트 (내부 ID)
        top_k_scores: Top-K 아이템 점수 리스트
    """
    with torch.no_grad():
        # 모든 아이템에 대한 점수 계산
        # EASE는 일반적으로 user-item interaction history를 기반으로 예측
        user_tensor = torch.LongTensor([user_id]).to(config['device'])

        # 모델의 predict 메서드 사용 (모델에 따라 다를 수 있음)
        # EASE의 경우 전체 아이템에 대한 점수를 계산
        scores = model.predict(user_tensor)

        # 이미 상호작용한 아이템은 제외
        train_items = dataset.inter_feat[dataset.inter_feat['user_id'] == user_id]['item_id'].tolist()
        scores[train_items] = -float('inf')

        # Top-K 추출
        top_k_scores, top_k_items = torch.topk(scores, k)

    return top_k_items.cpu().numpy(), top_k_scores.cpu().numpy()


def predict_for_all_users(model, dataset, config, k=10, batch_size=256):
    """
    모든 사용자에 대한 Top-K 추천을 생성합니다.

    Args:
        model: 학습된 모델
        dataset: 데이터셋
        config: 설정 객체
        k: 추천할 아이템 개수
        batch_size: 배치 크기

    Returns:
        recommendations: {user_id: [(item_id, score), ...]} 형태의 딕셔너리
    """
    recommendations = {}

    with torch.no_grad():
        # 사용자별로 추천 생성
        for user_id in range(dataset.user_num):
            if user_id == 0:  # padding ID 스킵
                continue

            try:
                # 해당 사용자가 학습 데이터에 있는지 확인
                user_history = dataset.inter_feat[dataset.inter_feat['user_id'] == user_id]
                if len(user_history) == 0:
                    continue

                # Top-K 추천 생성
                top_k_items, top_k_scores = predict_for_user(
                    model, dataset, config, user_id, k
                )

                # 결과 저장
                recommendations[user_id] = list(zip(top_k_items, top_k_scores))

                # 진행 상황 표시
                if (user_id + 1) % 1000 == 0:
                    print(f"처리 완료: {user_id + 1}/{dataset.user_num} 사용자")

            except Exception as e:
                print(f"사용자 {user_id} 처리 중 오류: {e}")
                continue

    return recommendations


def save_recommendations(recommendations, dataset, output_file):
    """
    추천 결과를 CSV 파일로 저장합니다.

    Args:
        recommendations: 추천 결과 딕셔너리
        dataset: 데이터셋 (ID 매핑 정보)
        output_file: 출력 파일 경로
    """
    results = []

    for user_id, items in recommendations.items():
        # 내부 ID를 원본 ID로 변환
        user_token = dataset.id2token('user_id', user_id)

        for item_id, score in items:
            item_token = dataset.id2token('item_id', item_id)
            results.append({
                'user_id': user_token,
                'item_id': item_token,
                'score': float(score)
            })

    # DataFrame으로 변환 후 저장
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"✓ 추천 결과 저장 완료: {output_file}")
    print(f"  - 총 추천 수: {len(df)}")
    print(f"  - 사용자 수: {df['user_id'].nunique()}")


def main():
    # 설정
    MODEL_FILE = 'saved/EASE-Jan-21-2026_05-18-10.pth'
    CONFIG_FILE = '../configs/recbole_config_ease.yaml'
    OUTPUT_FILE = 'saved/ease_recommendations.csv'
    TOP_K = 20  # 사용자당 추천할 아이템 개수

    print("="*60)
    print("EASE 모델 추론 시작")
    print("="*60)

    # 1. 모델 및 데이터 로드
    print("\n[1/3] 모델 및 데이터 로드 중...")
    model, dataset, config = load_model_and_data(
        MODEL_FILE,
        config_file_list=[CONFIG_FILE]
    )

    # 2. 추천 생성
    print(f"\n[2/3] 모든 사용자에 대한 Top-{TOP_K} 추천 생성 중...")
    recommendations = predict_for_all_users(model, dataset, config, k=TOP_K)

    print(f"\n✓ 추천 생성 완료: {len(recommendations)} 명의 사용자")

    # 3. 결과 저장
    print(f"\n[3/3] 결과 저장 중...")
    save_recommendations(recommendations, dataset, OUTPUT_FILE)

    # 샘플 출력
    print("\n" + "="*60)
    print("샘플 추천 결과 (첫 번째 사용자)")
    print("="*60)
    first_user = list(recommendations.keys())[0]
    print(f"사용자 ID: {dataset.id2token('user_id', first_user)}")
    print(f"추천 아이템:")
    for i, (item_id, score) in enumerate(recommendations[first_user][:5], 1):
        item_token = dataset.id2token('item_id', item_id)
        print(f"  {i}. 아이템 {item_token} (점수: {score:.4f})")

    print("\n✓ 모든 작업 완료!")


if __name__ == "__main__":
    main()
