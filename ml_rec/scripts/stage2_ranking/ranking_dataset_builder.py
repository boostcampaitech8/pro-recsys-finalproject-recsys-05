"""
Task 1: Ranking Dataset Builder
EASE/LightGCN 후보를 받아서 DCN v2 학습용 데이터셋 생성

절차:
1. EASE/LightGCN 후보 로드
2. 후보 합병 (300개)
3. 특성 엔지니어링 (사용자/게임/임베딩)
4. Positive/Negative 샘플 생성 (1:4 비율)
5. 8:1:1 분할
6. pickle 저장
"""

import json
import numpy as np
import pandas as pd
import pickle
import logging
from pathlib import Path
from collections import defaultdict
import random

# 랜덤 시드 고정 (재현성)
random.seed(42)
np.random.seed(42)

# 로깅 설정
log_dir = Path('logs/week3_ranking')
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_dir / 'ranking_dataset_builder.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RankingDatasetBuilder:
    def __init__(self, is_test=False):
        self.base_path = Path.cwd()
        self.candidates_path = self.base_path / 'candidates'
        self.dataset_path = self.base_path / 'dataset' / 'steam_optimal'
        self.is_test = is_test

        logger.info("=" * 80)
        logger.info(f"Task 1: Ranking Dataset Builder 시작 (Test Mode: {is_test})")
        logger.info("=" * 80)

    def load_candidates(self):
        """EASE/LightGCN 후보 로드"""
        logger.info("\n[Step 1] EASE/LightGCN 후보 로드 중...")

        # EASE 후보 로드
        with open(self.candidates_path / 'ease_candidates.json', 'r') as f:
            ease_candidates = json.load(f)
        logger.info(f"✅ EASE 후보 로드: {len(ease_candidates)}명 사용자")

        # LightGCN 후보 로드
        with open(self.candidates_path / 'lightgcn_candidates.json', 'r') as f:
            lightgcn_candidates = json.load(f)
        logger.info(f"✅ LightGCN 후보 로드: {len(lightgcn_candidates)}명 사용자")

        if self.is_test:
            logger.info("ℹ️ Test Mode: 사용자 수를 상위 500명으로 제한합니다.")
            test_users = list(ease_candidates.keys())[:500]
            ease_candidates = {u: ease_candidates[u] for u in test_users if u in ease_candidates}
            lightgcn_candidates = {u: lightgcn_candidates[u] for u in test_users if u in lightgcn_candidates}

        # LightGCN 임베딩 로드
        embeddings_data = np.load(self.candidates_path / 'lightgcn_embeddings.npz')
        embeddings = embeddings_data['embeddings']  # (17532, 64)
        item_ids = embeddings_data['item_ids']  # (17532,)

        self.item_embedding_dict = {str(item_id): embeddings[i] for i, item_id in enumerate(item_ids)}
        logger.info(f"✅ LightGCN 임베딩 로드: {len(self.item_embedding_dict)}개 아이템, 64차원")

        return ease_candidates, lightgcn_candidates

    def merge_candidates(self, ease_candidates, lightgcn_candidates):
        """EASE와 LightGCN 후보 합병 (1:1 가중치, 중복 제거)"""
        logger.info("\n[Step 2] 후보 합병 중 (1:1 가중치)...")

        merged_candidates = {}

        for user_id in ease_candidates.keys():
            if user_id not in lightgcn_candidates:
                continue

            # EASE 후보
            raw_ease = ease_candidates[user_id]
            if isinstance(raw_ease[0], dict):
                ease_items = {str(item['item_id']): float(item['score']) for item in raw_ease}
            else:
                ease_items = {str(item): 1.0 for item in raw_ease}

            # LightGCN 후보
            raw_lightgcn = lightgcn_candidates[user_id]
            if isinstance(raw_lightgcn[0], dict):
                lightgcn_items = {str(item['item_id']): float(item['score']) for item in raw_lightgcn}
            else:
                lightgcn_items = {str(item): 1.0 for item in raw_lightgcn}

            # 합병: 1:1 가중치
            merged_score = {}
            for item_id, score in ease_items.items():
                merged_score[item_id] = merged_score.get(item_id, 0) + score
            for item_id, score in lightgcn_items.items():
                merged_score[item_id] = merged_score.get(item_id, 0) + score

            # 상위 300개 선택
            top_300 = sorted(merged_score.items(), key=lambda x: x[1], reverse=True)[:300]
            merged_candidates[user_id] = [{'item_id': item_id, 'score': score} for item_id, score in top_300]

        logger.info(f"✅ 합병 완료: {len(merged_candidates)}명 사용자, 평균 {sum(len(v) for v in merged_candidates.values()) / len(merged_candidates):.1f}개 후보")

        return merged_candidates

    def load_dataset(self):
        """steam_optimal 데이터 로드"""
        logger.info("\n[Step 3] steam_optimal 데이터 로드 중...")

        # .inter 파일 로드 (상호작용)
        inter_df = pd.read_csv(
            self.dataset_path / 'steam_optimal.inter',
            sep='\t',
            dtype={'user_id:token': str, 'item_id:token': str}
        )
        # inter_df structure [user_id:token, item_id:token, rating:float] (3 columns)
        inter_df.columns = ['user_id', 'item_id', 'rating']
        logger.info(f"✅ .inter 파일 로드: {len(inter_df):,}개 상호작용")

        # .item 파일 로드
        item_df = pd.read_csv(
            self.dataset_path / 'steam_optimal.item',
            sep='\t',
            dtype={'item_id:token': str}
        )
        item_df.columns = ['item_id', 'popularity', 'avg_rating']
        logger.info(f"✅ .item 파일 로드: {len(item_df)}개 아이템")

        # .user 파일 로드
        user_df = pd.read_csv(
            self.dataset_path / 'steam_optimal.user',
            sep='\t',
            dtype={'user_id:token': str}
        )
        user_df.columns = ['user_id', 'num_items', 'avg_playtime']
        logger.info(f"✅ .user 파일 로드: {len(user_df)}명 사용자")

        # 사용자-게임 상호작용 셋으로 변환 (빠른 조회용)
        self.user_item_set = defaultdict(set)
        for _, row in inter_df.iterrows():
            self.user_item_set[row['user_id']].add(row['item_id'])

        logger.info(f"✅ 사용자-게임 상호작용 셋 생성: {len(self.user_item_set)}명 사용자")

        return item_df, user_df, inter_df

    def engineer_features(self, user_id, item_id, item_df, user_df):
        """사용자-게임 쌍의 특성 엔지니어링"""

        # 게임 특성
        item_row = item_df[item_df['item_id'] == item_id]
        if len(item_row) == 0:
            return None

        # 아이템 인기도
        popularity = float(item_row['popularity'].values[0])

        # 사용자 특성
        user_row = user_df[user_df['user_id'] == user_id]
        if len(user_row) == 0:
            return None

        avg_playtime = float(user_row['avg_playtime'].values[0])

        # LightGCN 임베딩 (있으면 추가, 없으면 0 벡터)
        embedding = self.item_embedding_dict.get(item_id, np.zeros(64))

        features = {
            'user_id': user_id,
            'item_id': item_id,
            'popularity': popularity,
            'avg_playtime': avg_playtime,
            'embedding': embedding
        }

        return features

    def create_samples(self, merged_candidates, item_df, user_df):
        """Positive/Negative 샘플 생성 (1:4 비율)"""
        logger.info("\n[Step 4] Positive/Negative 샘플 생성 중 (1:4 비율)...")

        all_samples = []
        positive_count = 0
        negative_count = 0

        total_users = len(merged_candidates)
        for idx, (user_id, candidates) in enumerate(merged_candidates.items()):
            if idx % 10000 == 0:
                logger.info(f"  진행률: {idx}/{total_users} ({100*idx/total_users:.1f}%)")

            candidate_item_ids = [str(c['item_id']) for c in candidates]

            # Positive 샘플: 실제로 이 사용자가 소유한 게임들
            positive_items = [item for item in candidate_item_ids if item in self.user_item_set[user_id]]
            
            # 만약 후보군 중에 소유 게임이 하나도 없다면 (Retrieval이 필터링했기 때문),
            # 실제 플레이 이력에서 무작위로 소량을 가져와 Positive 후보로 추가합니다.
            if not positive_items:
                user_played = list(self.user_item_set[user_id])
                if user_played:
                    # 최대 5개의 상호작용 아이템을 긍정 샘플로 활용
                    positive_items = random.sample(user_played, min(5, len(user_played)))
                    # 로깅 과다 방지를 위해 첫 10회만 기록
                    if idx < 10:
                        logger.info(f"    ℹ️ 사용자 {user_id}: 후보군 내 긍정 샘플 부재로 플레이 이력에서 {len(positive_items)}개 샘플링")

            # 각 Positive 샘플에 대해
            for pos_item in positive_items:
                features = self.engineer_features(user_id, pos_item, item_df, user_df)
                if features is not None:
                    features['label'] = 1
                    all_samples.append(features)
                    positive_count += 1

                # 각 Positive마다 3개의 Negative 샘플 추가
                negative_items = [item for item in candidate_item_ids if item not in self.user_item_set[user_id]]
                negative_samples = random.sample(negative_items, min(3, len(negative_items)))

                for neg_item in negative_samples:
                    features = self.engineer_features(user_id, neg_item, item_df, user_df)
                    if features is not None:
                        features['label'] = 0
                        all_samples.append(features)
                        negative_count += 1

        if not all_samples:
            logger.warning("⚠️ 생성된 샘플이 하나도 없습니다. 데이터셋 확인이 필요합니다.")
            return []

        logger.info(f"✅ 샘플 생성 완료: {len(all_samples):,}개 샘플")
        pos_ratio = 100 * positive_count / len(all_samples) if all_samples else 0.0
        neg_ratio = 100 * negative_count / len(all_samples) if all_samples else 0.0
        logger.info(f"  - Positive: {positive_count:,}개 ({pos_ratio:.1f}%)")
        logger.info(f"  - Negative: {negative_count:,}개 ({neg_ratio:.1f}%)")

        return all_samples

    def split_data(self, all_samples):
        """데이터 분할 (8:1:1)"""
        logger.info("\n[Step 5] 데이터 분할 중 (8:1:1)...")

        random.shuffle(all_samples)

        total_len = len(all_samples)
        train_len = int(total_len * 0.8)
        val_len = int(total_len * 0.1)

        train_data = all_samples[:train_len]
        val_data = all_samples[train_len:train_len + val_len]
        test_data = all_samples[train_len + val_len:]

        logger.info("✅ 분할 완료:")
        logger.info(f"  - 학습 데이터: {len(train_data):,}개 ({100*len(train_data)/total_len:.1f}%)")
        logger.info(f"  - 검증 데이터: {len(val_data):,}개 ({100*len(val_data)/total_len:.1f}%)")
        logger.info(f"  - 테스트 데이터: {len(test_data):,}개 ({100*len(test_data)/total_len:.1f}%)")

        return train_data, val_data, test_data

    def save_data(self, train_data, val_data, test_data):
        """데이터 저장"""
        logger.info("\n[Step 6] 데이터 저장 중...")

        # 저장 경로
        train_path = self.candidates_path / 'ranking_train.pkl'
        val_path = self.candidates_path / 'ranking_val.pkl'
        test_path = self.candidates_path / 'ranking_test.pkl'

        # 저장
        with open(train_path, 'wb') as f:
            pickle.dump(train_data, f)
        logger.info(f"✅ ranking_train.pkl 저장 ({train_path.stat().st_size / (1024**3):.2f}GB)")

        with open(val_path, 'wb') as f:
            pickle.dump(val_data, f)
        logger.info(f"✅ ranking_val.pkl 저장 ({val_path.stat().st_size / (1024**3):.2f}GB)")

        with open(test_path, 'wb') as f:
            pickle.dump(test_data, f)
        logger.info(f"✅ ranking_test.pkl 저장 ({test_path.stat().st_size / (1024**3):.2f}GB)")

    def run(self):
        """전체 파이프라인 실행"""
        try:
            ease_candidates, lightgcn_candidates = self.load_candidates()
            merged_candidates = self.merge_candidates(ease_candidates, lightgcn_candidates)
            item_df, user_df, inter_df = self.load_dataset()
            all_samples = self.create_samples(merged_candidates, item_df, user_df)
            train_data, val_data, test_data = self.split_data(all_samples)
            self.save_data(train_data, val_data, test_data)

            logger.info("\n" + "=" * 80)
            logger.info("✅ Task 1 완료!")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"\n❌ 오류 발생: {e}", exc_info=True)
            raise

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run in test mode with reduced users")
    args = parser.parse_args()

    builder = RankingDatasetBuilder(is_test=args.test)
    builder.run()
