"""
EASE 모델에서 아이템 유사도 행렬을 추출하는 스크립트

학습된 EASE 모델의 가중치를 사용하여 아이템 간 유사도를 계산하고 저장합니다.
이를 통해 새로운 사용자에 대해서도 아이템 기반 추천이 가능합니다.
"""

import torch
import numpy as np
import pandas as pd
import pickle
from recbole.config import Config
from recbole.data import create_dataset, data_preparation
from recbole.utils import init_logger, get_model, init_seed
from sklearn.preprocessing import normalize
import os


def load_model(model_file, config_file_list):
    """학습된 EASE 모델을 로드합니다."""
    config = Config(model='EASE', config_file_list=config_file_list)
    init_seed(config['seed'], config['reproducibility'])
    init_logger(config)

    dataset = create_dataset(config)
    train_data, _, _ = data_preparation(config, dataset)

    model = get_model(config['model'])(config, train_data.dataset).to(config['device'])
    checkpoint = torch.load(model_file, map_location=config['device'], weights_only=False)
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()

    print(f"✓ 모델 로드: {model_file}")
    print(f"✓ 아이템 수: {dataset.item_num}")

    return model, dataset, config


def extract_item_similarity_matrix(model, dataset):
    """
    EASE 모델에서 아이템 유사도 행렬을 추출합니다.

    EASE 모델은 내부적으로 item-item 가중치 행렬을 학습하므로,
    이를 사용하여 아이템 간 유사도를 계산할 수 있습니다.
    """
    print("\n아이템 유사도 행렬 추출 중...")

    with torch.no_grad():
        # EASE 모델의 가중치 행렬 가져오기
        # RecBole의 EASE 구현에서는 item_similarity 또는 weight 등의 이름으로 저장됨

        # 모델 파라미터 확인
        print("\n모델 파라미터:")
        for name, param in model.named_parameters():
            print(f"  - {name}: {param.shape}")

        # EASE 모델의 경우, 일반적으로 'item_similarity' 또는 'weight' 행렬이 있음
        # RecBole EASE 구현 확인 필요
        if hasattr(model, 'item_similarity'):
            item_sim = model.item_similarity
            # torch tensor인 경우 numpy로 변환, 이미 numpy면 그대로 사용
            if hasattr(item_sim, 'cpu'):
                similarity_matrix = item_sim.cpu().numpy()
            else:
                similarity_matrix = np.asarray(item_sim)
        elif hasattr(model, 'weight'):
            weight = model.weight
            if hasattr(weight, 'cpu'):
                similarity_matrix = weight.cpu().numpy()
            else:
                similarity_matrix = np.asarray(weight)
        else:
            # 대안: interaction matrix로부터 직접 계산
            print("\n직접 계산 방식 사용...")
            # EASE는 closed-form solution: B = I - P^{-1}
            # 여기서는 학습된 interaction matrix를 사용
            interaction_matrix = model.interaction_matrix
            if hasattr(interaction_matrix, 'cpu'):
                interaction_matrix = interaction_matrix.cpu().numpy()
            else:
                interaction_matrix = np.asarray(interaction_matrix)

            # 아이템 간 코사인 유사도 계산
            # normalize rows (각 아이템을 정규화)
            normalized = normalize(interaction_matrix, norm='l2', axis=0)
            similarity_matrix = np.dot(normalized.T, normalized)

            # 대각선을 0으로 (자기 자신과의 유사도 제거)
            np.fill_diagonal(similarity_matrix, 0)

    print(f"✓ 유사도 행렬 shape: {similarity_matrix.shape}")
    print(f"✓ 유사도 범위: [{similarity_matrix.min():.4f}, {similarity_matrix.max():.4f}]")

    return similarity_matrix


def save_item_similarity(similarity_matrix, dataset, output_dir='saved'):
    """
    아이템 유사도 행렬과 메타데이터를 저장합니다.

    저장 파일:
    1. item_similarity_matrix.npy: numpy 배열로 전체 유사도 행렬
    2. item_similarity.pkl: 메타데이터 포함 (item ID 매핑 등)
    3. item_mapping.csv: item_id와 원본 ID 매핑 테이블
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Numpy 배열로 저장
    matrix_file = os.path.join(output_dir, 'item_similarity_matrix.npy')
    np.save(matrix_file, similarity_matrix)
    print(f"✓ 유사도 행렬 저장: {matrix_file}")

    # 2. 아이템 ID 매핑 정보 저장
    item_ids = []
    item_tokens = []

    for item_id in range(dataset.item_num):
        if item_id == 0:  # padding ID 스킵
            continue
        item_token = dataset.id2token('item_id', item_id)
        item_ids.append(item_id)
        item_tokens.append(item_token)

    mapping_df = pd.DataFrame({
        'internal_id': item_ids,
        'original_id': item_tokens
    })
    mapping_file = os.path.join(output_dir, 'item_mapping.csv')
    mapping_df.to_csv(mapping_file, index=False)
    print(f"✓ 아이템 매핑 저장: {mapping_file}")

    # 3. 전체 데이터를 pickle로 저장 (빠른 로딩용)
    data = {
        'similarity_matrix': similarity_matrix,
        'item_num': dataset.item_num,
        'id2token': {i: dataset.id2token('item_id', i) for i in range(dataset.item_num)},
        'token2id': {dataset.id2token('item_id', i): i for i in range(dataset.item_num) if i != 0}
    }

    pkl_file = os.path.join(output_dir, 'item_similarity.pkl')
    with open(pkl_file, 'wb') as f:
        pickle.dump(data, f)
    print(f"✓ 메타데이터 저장: {pkl_file}")

    return mapping_df


def analyze_similarity(similarity_matrix, dataset, n_samples=5):
    """유사도 행렬을 분석하고 샘플을 출력합니다."""
    print(f"\n{'='*60}")
    print("아이템 유사도 분석")
    print(f"{'='*60}")

    # 무작위로 몇 개 아이템 선택하여 가장 유사한 아이템 출력
    sample_items = np.random.choice(range(1, dataset.item_num), size=min(n_samples, dataset.item_num-1), replace=False)

    for item_id in sample_items:
        item_token = dataset.id2token('item_id', item_id)
        similarities = similarity_matrix[item_id]

        # 가장 유사한 5개 아이템
        top_indices = np.argsort(similarities)[::-1][:5]

        print(f"\n아이템 {item_token}와 가장 유사한 게임:")
        for rank, similar_id in enumerate(top_indices, 1):
            if similar_id == 0 or similar_id == item_id:
                continue
            similar_token = dataset.id2token('item_id', similar_id)
            score = similarities[similar_id]
            print(f"  {rank}. 아이템 {similar_token} (유사도: {score:.4f})")


def main():
    # 설정
    MODEL_FILE = '../saved/EASE-Jan-21-2026_05-18-10.pth'
    CONFIG_FILE = '../../configs/recbole_config_ease.yaml'
    OUTPUT_DIR = 'saved'

    print("="*60)
    print("아이템 유사도 행렬 추출")
    print("="*60)

    # 1. 모델 로드
    print("\n[1/4] 모델 로드...")
    model, dataset, config = load_model(MODEL_FILE, [CONFIG_FILE])

    # 2. 유사도 행렬 추출
    print("\n[2/4] 유사도 행렬 추출...")
    similarity_matrix = extract_item_similarity_matrix(model, dataset)

    # 3. 저장
    print("\n[3/4] 저장...")
    mapping_df = save_item_similarity(similarity_matrix, dataset, OUTPUT_DIR)

    # 4. 분석
    print("\n[4/4] 분석...")
    analyze_similarity(similarity_matrix, dataset, n_samples=3)

    print(f"\n{'='*60}")
    print("✓ 완료!")
    print(f"{'='*60}")
    print(f"\n다음 파일들이 생성되었습니다:")
    print(f"  - {OUTPUT_DIR}/item_similarity_matrix.npy")
    print(f"  - {OUTPUT_DIR}/item_similarity.pkl")
    print(f"  - {OUTPUT_DIR}/item_mapping.csv")
    print(f"\n이제 inference_service.py를 사용하여 새로운 사용자에게 추천할 수 있습니다.")


if __name__ == "__main__":
    main()
