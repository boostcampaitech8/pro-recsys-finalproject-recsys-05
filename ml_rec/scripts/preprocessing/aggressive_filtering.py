"""
EASE 모델 학습을 위한 공격적 필터링 (메모리/속도 최적화)

현재 문제: Killed 상태 → 데이터 크기 추가 감소 필요
해결책: K-core + User Activity Range + Item Popularity Range 결합
"""

import pandas as pd
import numpy as np
import os

class AggressiveFilteringStrategy:
    def __init__(self, data_path):
        self.data_path = data_path
        self.df = None
        self.load_data()

    def load_data(self):
        print(f"Loading data from {self.data_path}...")
        self.df = pd.read_csv(self.data_path, delimiter=',')
        print(f"Original: {len(self.df):,} interactions, "
              f"{self.df['user_id:token'].nunique():,} users, "
              f"{self.df['item_id:token'].nunique():,} items\n")

    def get_stats(self, df, strategy_name=""):
        n_users = df['user_id:token'].nunique()
        n_items = df['item_id:token'].nunique()
        n_interactions = len(df)
        sparsity = 1 - (n_interactions / (n_users * n_items))

        bytes_per_float = 4
        memory_mb = (n_users * n_items * bytes_per_float) / (1024 ** 2)
        memory_gb = memory_mb / 1024

        reduction = (1 - n_interactions / len(self.df)) * 100

        print(f"{'='*70}")
        print(f"📊 {strategy_name}")
        print(f"{'='*70}")
        print(f"Users:        {n_users:>10,} (removed: {self.df['user_id:token'].nunique() - n_users:,})")
        print(f"Items:        {n_items:>10,} (removed: {self.df['item_id:token'].nunique() - n_items:,})")
        print(f"Interactions: {n_interactions:>10,} (reduced: {reduction:>6.2f}%)")
        print(f"Sparsity:     {sparsity:>10.6f}")
        print(f"Memory (GB):  {memory_gb:>10.2f}")
        print(f"Speedup:      {self.get_stats(self.df)['memory_gb'] / memory_gb:>10.2f}x\n")

        return {'users': n_users, 'items': n_items, 'interactions': n_interactions, 'memory_gb': memory_gb}

    def combined_filter(self, k=30, min_user_interactions=20, max_user_interactions=None,
                       min_item_popularity=20, max_item_popularity=None, iterations=5):
        """
        K-core + User Activity Range + Item Popularity Range 결합

        Args:
            k: K-core 값
            min_user_interactions: 최소 사용자 활동
            max_user_interactions: 최대 사용자 활동 (이상현상 제거)
            min_item_popularity: 최소 아이템 인기도
            max_item_popularity: 최대 아이템 인기도 (인기 아이템 수 제한)
            iterations: 반복 횟수
        """
        filtered_df = self.df.copy()

        print(f"  Applying combined filtering:")
        print(f"    K-core: k={k}")
        print(f"    User activity: [{min_user_interactions}, {max_user_interactions}]")
        print(f"    Item popularity: [{min_item_popularity}, {max_item_popularity}]")
        print(f"    Iterations: {iterations}\n")

        for iteration in range(iterations):
            prev_len = len(filtered_df)

            # Step 1: User Activity Range 필터링
            user_counts = filtered_df.groupby('user_id:token').size()
            valid_users = user_counts[user_counts >= min_user_interactions]
            if max_user_interactions is not None:
                valid_users = valid_users[valid_users <= max_user_interactions]

            filtered_df = filtered_df[filtered_df['user_id:token'].isin(valid_users.index)]

            # Step 2: Item Popularity Range 필터링
            item_counts = filtered_df.groupby('item_id:token').size()
            valid_items = item_counts[item_counts >= min_item_popularity]
            if max_item_popularity is not None:
                valid_items = valid_items[valid_items <= max_item_popularity]

            filtered_df = filtered_df[filtered_df['item_id:token'].isin(valid_items.index)]

            # Step 3: K-core 필터링
            user_degrees = filtered_df.groupby('user_id:token').size()
            valid_users_kcore = user_degrees[user_degrees >= k]

            item_degrees = filtered_df.groupby('item_id:token').size()
            valid_items_kcore = item_degrees[item_degrees >= k]

            filtered_df = filtered_df[
                (filtered_df['user_id:token'].isin(valid_users_kcore.index)) &
                (filtered_df['item_id:token'].isin(valid_items_kcore.index))
            ]

            print(f"  Iteration {iteration + 1}: {len(filtered_df):,} interactions")

            # 수렴 확인
            if len(filtered_df) == prev_len or len(filtered_df) == 0:
                print(f"  ✓ Converged at iteration {iteration + 1}\n")
                break

        return filtered_df

    def save_data(self, df, filename):
        """데이터 저장"""
        output_path = f'/data/ephemeral/home/steam_project/dataset/steam/{filename}'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✅ Saved to: {output_path}\n")
        return output_path


def main():
    print("\n" + "="*70)
    print("🚀 AGGRESSIVE FILTERING FOR EASE MODEL")
    print("Combined: K-core + User Activity + Item Popularity")
    print("="*70 + "\n")

    strategy = AggressiveFilteringStrategy('/data/ephemeral/home/steam_project/dataset/steam_filtered_kcore20/steam_filtered_kcore20.inter')

    results = {}

    # Strategy 1: 중간 필터링 (K-core 30 + 활동 범위 제한)
    print("Strategy 1: K-core 30 + User (20-500) + Item (20-1000)")
    print("-" * 70)
    result1 = strategy.combined_filter(
        k=30,
        min_user_interactions=20,
        max_user_interactions=500,
        min_item_popularity=20,
        max_item_popularity=1000,
        iterations=5
    )
    stats1 = strategy.get_stats(result1, "K30 + Activity Range")
    results['K30 + Activity'] = (result1, stats1)

    # Strategy 2: 강한 필터링 (K-core 40)
    print("Strategy 2: K-core 40 + User (30-300) + Item (30-800)")
    print("-" * 70)
    result2 = strategy.combined_filter(
        k=40,
        min_user_interactions=30,
        max_user_interactions=300,
        min_item_popularity=30,
        max_item_popularity=800,
        iterations=5
    )
    stats2 = strategy.get_stats(result2, "K40 + Activity Range")
    results['K40 + Activity'] = (result2, stats2)

    # Strategy 3: 매우 강한 필터링 (K-core 50)
    print("Strategy 3: K-core 50 + User (40-200) + Item (40-600)")
    print("-" * 70)
    result3 = strategy.combined_filter(
        k=50,
        min_user_interactions=40,
        max_user_interactions=200,
        min_item_popularity=40,
        max_item_popularity=600,
        iterations=5
    )
    stats3 = strategy.get_stats(result3, "K50 + Activity Range")
    results['K50 + Activity'] = (result3, stats3)

    # Strategy 4: 극단적 필터링 (K-core 60)
    print("Strategy 4: K-core 60 + User (50-150) + Item (50-500)")
    print("-" * 70)
    result4 = strategy.combined_filter(
        k=60,
        min_user_interactions=50,
        max_user_interactions=150,
        min_item_popularity=50,
        max_item_popularity=500,
        iterations=5
    )
    stats4 = strategy.get_stats(result4, "K60 + Activity Range")
    results['K60 + Activity'] = (result4, stats4)

    # Strategy 5: 보수적 필터링 (K-core 25)
    print("Strategy 5: K-core 25 + User (15-600) + Item (15-1200)")
    print("-" * 70)
    result5 = strategy.combined_filter(
        k=25,
        min_user_interactions=15,
        max_user_interactions=600,
        min_item_popularity=15,
        max_item_popularity=1200,
        iterations=5
    )
    stats5 = strategy.get_stats(result5, "K25 + Activity Range")
    results['K25 + Activity'] = (result5, stats5)

    # Comparison
    print("\n" + "="*70)
    print("📈 COMPARISON TABLE")
    print("="*70)
    print(f"{'Strategy':<25} {'Users':>10} {'Items':>10} {'Memory(GB)':>12} {'Speedup':>8}")
    print("-" * 70)

    original_stats = strategy.get_stats(strategy.df, "Original (Reference)")
    original_memory = original_stats['memory_gb']

    for name, (df, stats) in results.items():
        speedup = original_memory / stats['memory_gb']
        print(f"{name:<25} {stats['users']:>10,} {stats['items']:>10,} {stats['memory_gb']:>12.2f} {speedup:>8.2f}x")

    # Recommendations
    print("\n" + "="*70)
    print("✨ RECOMMENDATIONS FOR KILLED 상황 해결")
    print("="*70)
    print("""
🎯 문제 해결 순서 (Killed 상태 극복):

1️⃣  FIRST TRY (가장 추천) ⭐⭐⭐
   → K-core 30 + User (20-500) + Item (20-1000)
   → 설정: steam_filtered_k30_activity.inter
   → 기대 메모리: ~8-12GB
   → 적당한 데이터 유지 + 빠른 학습

2️⃣  SECOND TRY (여전히 Killed면) ⭐⭐
   → K-core 40 + User (30-300) + Item (30-800)
   → 설정: steam_filtered_k40_activity.inter
   → 기대 메모리: ~5-8GB
   → 더 공격적인 필터링

3️⃣  THIRD TRY (극한 상황) ⭐
   → K-core 50 + User (40-200) + Item (40-600)
   → 설정: steam_filtered_k50_activity.inter
   → 기대 메모리: ~3-5GB
   → 핵심 데이터만 유지

⚠️  추가 설정 최적화 (eval_args.mode 이미 적용됨):
   1. eval_args.mode = uni100 ✓ (이미 적용)
   2. eval_batch_size = 2048 (필요시 1024로 감소)
   3. train_batch_size = 2048 (필요시 1024로 감소)
   4. valid_sample_rate = 0.1 (평가 10% 샘플만 사용)

🔍 메모리 vs 정확도 트레이드오프:
   - K30: 균형 (추천)
   - K40: 메모리 우선
   - K50: 극단적 메모리 절감
    """)

    # Save best options
    print("\n" + "="*70)
    print("💾 SAVING RECOMMENDED DATASETS")
    print("="*70)

    strategy.save_data(results['K30 + Activity'][0], 'steam_filtered_k30_activity.inter')
    strategy.save_data(results['K40 + Activity'][0], 'steam_filtered_k40_activity.inter')
    strategy.save_data(results['K50 + Activity'][0], 'steam_filtered_k50_activity.inter')
    strategy.save_data(results['K60 + Activity'][0], 'steam_filtered_k60_activity.inter')

    print("\n" + "="*70)
    print("🚀 NEXT STEPS")
    print("="*70)
    print("""
1. RecBole 설정 파일 수정:

   configs/recbole_config_ease.yaml 에서:
   ```yaml
   dataset: steam_filtered_k30_activity  # 첫 번째 시도
   ```

2. 학습 재실행:
   python -m recbole.main --model EASE --config configs/recbole_config_ease.yaml

3. 여전히 Killed 되면:
   - dataset을 steam_filtered_k40_activity로 변경
   - 또는 eval_batch_size를 1024로 낮춤
   - 또는 eval_args.mode를 'uni50'으로 변경 (50개 오답만 비교)

4. 학습 완료 후:
   - 검증 데이터: 10% (eval_args에서 설정)
   - 테스트 데이터: 10%
   - 훈련 데이터: 80%
    """)


if __name__ == '__main__':
    main()
