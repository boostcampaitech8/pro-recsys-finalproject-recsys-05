"""
간단한 방식: 저장된 체크포인트에서 직접 후보 및 임베딩 추출
"""

import json
import numpy as np
import torch
import pickle
import glob
import os
from pathlib import Path
import pandas as pd
from tqdm import tqdm

# 데이터셋 로드
def load_inter_data(inter_file):
    """interaction 파일 로드"""
    inter_df = pd.read_csv(inter_file, sep='\t', header=None)
    inter_df.columns = ['user_id', 'item_id', 'rating', 'timestamp']
    return inter_df

def load_model_checkpoint(model_path):
    """모델 체크포인트 로드"""
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    return checkpoint

def extract_embeddings_from_checkpoint(checkpoint, model_type='LightGCN'):
    """체크포인트에서 임베딩 추출"""
    if model_type == 'LightGCN':
        # LightGCN의 경우 state_dict에서 임베딩 추출
        state_dict = checkpoint['state_dict']

        # 아이템 임베딩 찾기
        item_emb_key = None
        for key in state_dict.keys():
            if 'item_embedding' in key and 'weight' in key:
                item_emb_key = key
                break

        if item_emb_key:
            item_embeddings = state_dict[item_emb_key].cpu().numpy()
            return item_embeddings

    return None

def load_id_mappings(inter_file):
    """ID 매핑 생성"""
    inter_df = pd.read_csv(inter_file, sep='\t', header=0)

    # 고유한 사용자와 아이템 추출 (문자열 정렬)
    users = sorted(inter_df['user_id:token'].unique().astype(str))
    items = sorted(inter_df['item_id:token'].unique().astype(int))

    # ID 매핑 (external -> internal)
    user_to_id = {u: i for i, u in enumerate(users)}
    item_to_id = {v: i for i, v in enumerate(items)}

    # 역매핑
    id_to_user = {i: u for u, i in user_to_id.items()}
    id_to_item = {i: v for v, i in item_to_id.items()}

    return users, items, user_to_id, item_to_id, id_to_user, id_to_item, inter_df

def get_user_interactions(inter_df, user_to_id, item_to_id):
    """사용자별 상호작용 추출"""
    user_interactions = {}
    for _, row in inter_df.iterrows():
        user_ext = str(row['user_id:token'])
        item_ext = int(row['item_id:token'])

        if user_ext in user_to_id and item_ext in item_to_id:
            user_id = user_to_id[user_ext]
            item_id = item_to_id[item_ext]

            if user_id not in user_interactions:
                user_interactions[user_id] = []
            user_interactions[user_id].append(item_id)

    return user_interactions

def extract_lightgcn_candidates(checkpoint, id_to_user, id_to_item, user_interactions, top_k=200):
    """LightGCN에서 후보 추출"""
    state_dict = checkpoint['state_dict']

    # 임베딩 추출
    user_emb_key = None
    item_emb_key = None

    for key in state_dict.keys():
        if 'user_embedding' in key and 'weight' in key:
            user_emb_key = key
        elif 'item_embedding' in key and 'weight' in key:
            item_emb_key = key

    if not user_emb_key or not item_emb_key:
        print("⚠ 임베딩 키를 찾을 수 없습니다")
        return {}, None

    user_embedding = state_dict[user_emb_key].cpu().numpy()
    item_embedding = state_dict[item_emb_key].cpu().numpy()

    candidates = {}
    n_users = user_embedding.shape[0]
    n_items = item_embedding.shape[0]

    print(f"  사용자: {n_users}, 아이템: {n_items}")

    for user_id in tqdm(range(n_users), desc="  추출 중"):
        user_vec = user_embedding[user_id]
        scores = np.dot(item_embedding, user_vec)

        top_indices = np.argsort(-scores)[:top_k]

        external_user_id = id_to_user.get(user_id, None)
        if external_user_id is None:
            continue

        candidates[str(external_user_id)] = []
        for rank, item_id in enumerate(top_indices):
            # item_id가 id_to_item 범위를 넘으면 원래 item id 사용
            external_item_id = id_to_item.get(item_id, item_id)
            score = float(scores[item_id])

            candidates[str(external_user_id)].append({
                'item_id': str(external_item_id),
                'score': score,
                'rank': rank + 1
            })

    return candidates, item_embedding

def extract_ease_candidates(checkpoint, id_to_user, id_to_item, user_interactions, top_k=200):
    """EASE에서 후보 추출"""

    # EASE의 item_similarity는 other_parameter에 저장됨
    if 'other_parameter' not in checkpoint:
        print("⚠ EASE other_parameter를 찾을 수 없습니다")
        return {}

    other_param = checkpoint['other_parameter']

    if 'item_similarity' not in other_param:
        print("⚠ EASE item_similarity를 찾을 수 없습니다")
        return {}

    # item_similarity는 numpy.matrix 형태
    item_similarity = np.asarray(other_param['item_similarity'])  # (n_items, n_items)
    n_items = item_similarity.shape[0]

    candidates = {}

    for user_id, interactions in tqdm(user_interactions.items(), desc="  추출 중"):
        if not interactions:
            continue

        # 점수 계산: sum(item_similarity[j, :] for j in interactions)
        scores = np.zeros(n_items)
        for j in interactions:
            if j < item_similarity.shape[0]:
                scores += np.asarray(item_similarity[j]).flatten()

        # 사용자가 이미 상호작용한 아이템은 제외
        for j in interactions:
            scores[j] = -np.inf

        top_indices = np.argsort(-scores)[:top_k]

        external_user_id = id_to_user[user_id]

        candidates[str(external_user_id)] = []
        for rank, item_id in enumerate(top_indices):
            if scores[item_id] == -np.inf:
                continue

            external_item_id = id_to_item.get(item_id, item_id)
            score = float(scores[item_id])

            candidates[str(external_user_id)].append({
                'item_id': str(external_item_id),
                'score': score,
                'rank': rank + 1
            })

    return candidates

def find_latest_model(model_name):
    """
    최신 모델 파일을 동적으로 찾기

    Args:
        model_name: 'EASE' or 'LightGCN'

    Returns:
        모델 파일 경로 (Path 객체)

    Example:
        >>> find_latest_model('EASE')
        Path('saved_models/EASE-steam_optimal-Jan-30-2026_06-49-29-ed8701.pth')
    """
    pattern = f'saved_models/{model_name}*.pth'
    model_files = glob.glob(pattern)

    if not model_files:
        raise FileNotFoundError(
            f"❌ No model files found for {model_name}\n"
            f"   Expected pattern: {pattern}\n"
            f"   Tip: Check if models have been trained in Week 2"
        )

    # 가장 최신 모델 파일 선택 (수정 시간 기준)
    latest_model = max(model_files, key=os.path.getmtime)
    print(f"✓ Found {model_name} model: {latest_model}")
    return Path(latest_model)

def main():
    print("\n" + "="*70)
    print("🚀 2주차 최종: 후보 및 임베딩 추출 (간단한 방식)")
    print("="*70 + "\n")

    # 경로 설정
    inter_file = Path('dataset/steam_optimal/steam_optimal.inter')
    ease_model_file = find_latest_model('EASE')
    lightgcn_model_file = find_latest_model('LightGCN')
    output_dir = Path('candidates')

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. ID 매핑 로드
    print("[1/4] ID 매핑 로드 중...")
    users, items, user_to_id, item_to_id, id_to_user, id_to_item, inter_df = load_id_mappings(inter_file)
    print(f"  ✓ 사용자: {len(users)}, 아이템: {len(items)}")

    # 2. 사용자별 상호작용 로드
    print("\n[2/4] 사용자 상호작용 로드 중...")
    user_interactions = get_user_interactions(inter_df, user_to_id, item_to_id)
    print(f"  ✓ {len(user_interactions)} 사용자의 상호작용 로드")

    # 3. EASE 모델에서 후보 추출
    print("\n[3/4] EASE 모델에서 후보 추출")
    try:
        ease_checkpoint = load_model_checkpoint(ease_model_file)
        ease_candidates = extract_ease_candidates(ease_checkpoint, id_to_user, id_to_item, user_interactions, 200)

        with open(output_dir / 'ease_candidates.json', 'w') as f:
            json.dump(ease_candidates, f, indent=2)
        print(f"✓ EASE 후보 저장: {output_dir / 'ease_candidates.json'}")
    except Exception as e:
        print(f"⚠ EASE 추출 중 오류: {e}")

    # 4. LightGCN 모델에서 후보 및 임베딩 추출
    print("\n[4/4] LightGCN 모델에서 후보 및 임베딩 추출")
    try:
        lightgcn_checkpoint = load_model_checkpoint(lightgcn_model_file)
        lightgcn_candidates, item_embeddings = extract_lightgcn_candidates(
            lightgcn_checkpoint, id_to_user, id_to_item, user_interactions, 200
        )

        with open(output_dir / 'lightgcn_candidates.json', 'w') as f:
            json.dump(lightgcn_candidates, f, indent=2)
        print(f"✓ LightGCN 후보 저장: {output_dir / 'lightgcn_candidates.json'}")

        # 임베딩 저장
        item_ids = np.array([id_to_item[i] for i in range(len(id_to_item))])
        np.savez(output_dir / 'lightgcn_embeddings.npz',
                 embeddings=item_embeddings,
                 item_ids=item_ids)
        print(f"✓ 임베딩 저장: {output_dir / 'lightgcn_embeddings.npz'} ({item_embeddings.shape})")

    except Exception as e:
        print(f"⚠ LightGCN 추출 중 오류: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("✅ 2주차 완료!")
    print("="*70)
    print(f"\n생성된 파일:")
    print(f"  - {output_dir / 'ease_candidates.json'}")
    print(f"  - {output_dir / 'lightgcn_candidates.json'}")
    print(f"  - {output_dir / 'lightgcn_embeddings.npz'}")
    print(f"\n다음 단계: 3주차 Ranking & Scoring")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
