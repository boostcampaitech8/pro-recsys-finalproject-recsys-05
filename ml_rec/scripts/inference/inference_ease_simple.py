"""
EASE 모델 추론 스크립트 (간단 버전)

RecBole의 표준 방법을 사용하여 학습된 모델로 추천을 생성합니다.
"""

import torch
import pandas as pd
import numpy as np
from recbole.config import Config
from recbole.data import create_dataset, data_preparation
from recbole.utils import init_logger, get_model, init_seed


def load_trained_model(model_file, config_file_list):
    """학습된 모델을 로드합니다."""
    # Config 로드
    config = Config(model='EASE', config_file_list=config_file_list)
    init_seed(config['seed'], config['reproducibility'])
    init_logger(config)

    # 데이터셋 생성
    dataset = create_dataset(config)
    train_data, valid_data, test_data = data_preparation(config, dataset)

    # 모델 생성 및 로드
    model = get_model(config['model'])(config, train_data.dataset).to(config['device'])
    checkpoint = torch.load(model_file, map_location=config['device'])
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()

    print(f"✓ 모델 로드: {model_file}")
    print(f"✓ 데이터셋: {config['dataset']}")
    print(f"✓ 사용자 수: {dataset.user_num}, 아이템 수: {dataset.item_num}")
    print(f"✓ 학습 상호작용: {len(train_data.dataset)}")

    return model, dataset, train_data, config


def generate_topk_recommendations(model, dataset, train_data, config, k=20):
    """
    모든 사용자에 대해 Top-K 추천을 생성합니다.

    EASE 모델의 경우 전체 상호작용 행렬을 기반으로 추천을 계산합니다.
    """
    print(f"\n사용자별 Top-{k} 추천 생성 중...")

    # 데이터셋의 상호작용 정보
    inter_feat = dataset.inter_feat
    user_ids = inter_feat['user_id'].unique()

    recommendations = []

    with torch.no_grad():
        for idx, user_id in enumerate(user_ids):
            # padding user (0) 건너뛰기
            if user_id == 0:
                continue

            # 사용자가 이미 상호작용한 아이템 가져오기
            user_history = inter_feat[inter_feat['user_id'] == user_id]['item_id'].numpy()

            # EASE 모델로 전체 아이템에 대한 점수 계산
            # 사용자 ID를 텐서로 변환
            user_tensor = torch.tensor([user_id], dtype=torch.long).to(config['device'])

            # 모델의 full_sort_predict 메서드 사용 (RecBole 표준)
            scores = model.full_sort_predict(user_tensor)

            # 이미 상호작용한 아이템 제외
            scores = scores.cpu().numpy()[0]  # 첫 번째 사용자의 점수
            scores[user_history] = -np.inf

            # Top-K 아이템 선택
            top_k_items = np.argsort(scores)[::-1][:k]
            top_k_scores = scores[top_k_items]

            # 원본 ID로 변환하여 저장
            user_token = dataset.id2token('user_id', user_id)
            for item_id, score in zip(top_k_items, top_k_scores):
                if score == -np.inf:
                    continue
                item_token = dataset.id2token('item_id', item_id)
                recommendations.append({
                    'user_id': user_token,
                    'item_id': item_token,
                    'score': float(score)
                })

            # 진행 상황 출력
            if (idx + 1) % 500 == 0:
                print(f"  처리 완료: {idx + 1}/{len(user_ids)} 사용자")

    return recommendations


def save_to_csv(recommendations, output_file):
    """추천 결과를 CSV로 저장합니다."""
    df = pd.DataFrame(recommendations)
    df = df.sort_values(['user_id', 'score'], ascending=[True, False])
    df.to_csv(output_file, index=False)

    print(f"\n✓ 저장 완료: {output_file}")
    print(f"  - 총 추천 수: {len(df):,}")
    print(f"  - 사용자 수: {df['user_id'].nunique():,}")
    print(f"  - 평균 추천 수/사용자: {len(df) / df['user_id'].nunique():.1f}")

    return df


def print_sample_recommendations(df, n_users=3, n_items=5):
    """샘플 추천 결과를 출력합니다."""
    print(f"\n{'='*60}")
    print(f"샘플 추천 결과 (상위 {n_users}명 사용자)")
    print(f"{'='*60}")

    sample_users = df['user_id'].unique()[:n_users]
    for user_id in sample_users:
        user_recs = df[df['user_id'] == user_id].head(n_items)
        print(f"\n사용자 {user_id}:")
        for idx, row in enumerate(user_recs.itertuples(), 1):
            print(f"  {idx}. 아이템 {row.item_id} (점수: {row.score:.4f})")


def main():
    # ===== 설정 =====
    MODEL_FILE = 'saved/EASE-Jan-21-2026_05-18-10.pth'
    CONFIG_FILE = '../configs/recbole_config_ease.yaml'
    OUTPUT_FILE = 'saved/ease_recommendations.csv'
    TOP_K = 20  # 추천할 아이템 개수

    print("="*60)
    print("EASE 모델 추론")
    print("="*60)

    # 1. 모델 로드
    print("\n[1/3] 모델 및 데이터 로드...")
    model, dataset, train_data, config = load_trained_model(MODEL_FILE, [CONFIG_FILE])

    # 2. 추천 생성
    print(f"\n[2/3] Top-{TOP_K} 추천 생성...")
    recommendations = generate_topk_recommendations(model, dataset, train_data, config, k=TOP_K)

    # 3. 결과 저장
    print(f"\n[3/3] 결과 저장...")
    df = save_to_csv(recommendations, OUTPUT_FILE)

    # 샘플 출력
    print_sample_recommendations(df)

    print(f"\n{'='*60}")
    print("✓ 추론 완료!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
