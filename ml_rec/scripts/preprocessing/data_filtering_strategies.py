"""
EASE 모델을 위한 데이터 필터링 전략 비교 및 실행 스크립트

여러 필터링 방법을 비교하고 최적의 전략을 선택할 수 있습니다:
1. 사용자 활동 기반 필터링 (User Activity Filter)
2. 아이템 인기도 기반 필터링 (Item Popularity Filter)
3. 결합 필터링 (Combined Filter)
4. K-core 분해 (K-core Decomposition) - 그래프 이론 기반
5. 상호작용 밀도 기반 필터링 (Interaction Density Filter)
"""

import pandas as pd
import numpy as np
import os

class DataFilteringStrategy:
    """데이터 필터링 전략을 구현하는 기본 클래스"""

    def __init__(self, data_path):
        self.data_path = data_path
        self.df = None
        self.load_data()

    def load_data(self):
        """데이터 로드"""
        print(f"Loading data from {self.data_path}...")
        self.df = pd.read_csv(self.data_path, delimiter=',')
        print(f"Original data shape: {self.df.shape}")
        print(f"Users: {self.df['user_id:token'].nunique():,}, Items: {self.df['item_id:token'].nunique():,}\n")

    def get_stats(self, df):
        """필터링 후 통계 출력"""
        n_users = df['user_id:token'].nunique()
        n_items = df['item_id:token'].nunique()
        n_interactions = len(df)
        sparsity = 1 - (n_interactions / (n_users * n_items))

        # 메모리 사용량 추정 (dense matrix, float32)
        bytes_per_float = 4
        memory_mb = (n_users * n_items * bytes_per_float) / (1024 ** 2)
        memory_gb = memory_mb / 1024

        return {
            'users': n_users,
            'items': n_items,
            'interactions': n_interactions,
            'sparsity': sparsity,
            'memory_mb': memory_mb,
            'memory_gb': memory_gb,
            'reduction_ratio': n_interactions / len(self.df)
        }

    def print_comparison(self, strategy_name, filtered_df):
        """필터링 결과 비교"""
        stats = self.get_stats(filtered_df)
        original_stats = self.get_stats(self.df)

        print(f"\n{'='*80}")
        print(f"📊 Strategy: {strategy_name}")
        print(f"{'='*80}")
        print(f"Users:              {stats['users']:>10,} (↓ {original_stats['users'] - stats['users']:>10,})")
        print(f"Items:              {stats['items']:>10,} (↓ {original_stats['items'] - stats['items']:>10,})")
        print(f"Interactions:       {stats['interactions']:>10,} (↓ {len(self.df) - stats['interactions']:>10,})")
        print(f"Reduction Ratio:    {stats['reduction_ratio']:>10.2%}")
        print(f"Sparsity:           {stats['sparsity']:>10.6f}")
        print(f"Memory (Dense):     {stats['memory_gb']:>10.2f} GB (original: {original_stats['memory_gb']:.2f} GB)")
        print(f"Speedup Factor:     {original_stats['memory_gb'] / stats['memory_gb']:>10.2f}x faster")

        return stats


class UserActivityFilter(DataFilteringStrategy):
    """사용자 활동 범위 기반 필터링"""

    def filter(self, min_interactions=10, max_interactions=None):
        """
        사용자 활동 범위로 필터링

        Args:
            min_interactions: 최소 상호작용 수 (기본: 10)
            max_interactions: 최대 상호작용 수 (기본: None - 제한없음)
        """
        user_counts = self.df.groupby('user_id:token').size()

        valid_users = user_counts[user_counts >= min_interactions]

        if max_interactions is not None:
            valid_users = valid_users[valid_users <= max_interactions]

        filtered_df = self.df[self.df['user_id:token'].isin(valid_users.index)]

        self.print_comparison(
            f"User Activity (min={min_interactions}, max={max_interactions})",
            filtered_df
        )

        return filtered_df


class ItemPopularityFilter(DataFilteringStrategy):
    """아이템 인기도 범위 기반 필터링"""

    def filter(self, min_popularity=10, max_popularity=None):
        """
        아이템 인기도 범위로 필터링

        Args:
            min_popularity: 최소 사용자 수
            max_popularity: 최대 사용자 수 (기본: None - 제한없음)
        """
        item_counts = self.df.groupby('item_id:token').size()

        valid_items = item_counts[item_counts >= min_popularity]

        if max_popularity is not None:
            valid_items = valid_items[valid_items <= max_popularity]

        filtered_df = self.df[self.df['item_id:token'].isin(valid_items.index)]

        self.print_comparison(
            f"Item Popularity (min={min_popularity}, max={max_popularity})",
            filtered_df
        )

        return filtered_df


class CombinedFilter(DataFilteringStrategy):
    """사용자와 아이템 모두 필터링"""

    def filter(self, min_user_interactions=10, max_user_interactions=None,
               min_item_popularity=10, max_item_popularity=None, iterations=1):
        """
        사용자와 아이템을 모두 필터링 (반복 적용 가능)

        Args:
            min_user_interactions: 최소 사용자 상호작용
            max_user_interactions: 최대 사용자 상호작용
            min_item_popularity: 최소 아이템 인기도
            max_item_popularity: 최대 아이템 인기도
            iterations: 필터링 반복 횟수
        """
        filtered_df = self.df.copy()

        for iteration in range(iterations):
            prev_len = len(filtered_df)

            # 사용자 필터링
            user_counts = filtered_df.groupby('user_id:token').size()
            valid_users = user_counts[user_counts >= min_user_interactions]
            if max_user_interactions is not None:
                valid_users = valid_users[valid_users <= max_user_interactions]

            filtered_df = filtered_df[filtered_df['user_id:token'].isin(valid_users.index)]

            # 아이템 필터링
            item_counts = filtered_df.groupby('item_id:token').size()
            valid_items = item_counts[item_counts >= min_item_popularity]
            if max_item_popularity is not None:
                valid_items = valid_items[valid_items <= max_item_popularity]

            filtered_df = filtered_df[filtered_df['item_id:token'].isin(valid_items.index)]

            print(f"  Iteration {iteration + 1}: {len(filtered_df):,} interactions")

            # 수렴 확인
            if len(filtered_df) == prev_len:
                print(f"  ✓ Converged at iteration {iteration + 1}")
                break

        self.print_comparison(
            f"Combined (user_min={min_user_interactions}, item_min={min_item_popularity}, iterations={iterations})",
            filtered_df
        )

        return filtered_df


class KCoreFilter(DataFilteringStrategy):
    """K-core 분해 기반 필터링 (그래프 이론)"""

    def filter(self, k=10):
        """
        K-core 필터링 적용
        모든 노드가 최소 k개의 이웃을 가질 때까지 반복적으로 제거

        Args:
            k: 최소 차수 (degree)
        """
        filtered_df = self.df.copy()
        iteration = 0

        print(f"  Applying K-core decomposition (k={k})...")

        while True:
            prev_len = len(filtered_df)

            # 사용자 차수 계산
            user_degrees = filtered_df.groupby('user_id:token').size()
            valid_users = user_degrees[user_degrees >= k]

            # 아이템 차수 계산
            item_degrees = filtered_df.groupby('item_id:token').size()
            valid_items = item_degrees[item_degrees >= k]

            # 필터링
            filtered_df = filtered_df[
                (filtered_df['user_id:token'].isin(valid_users.index)) &
                (filtered_df['item_id:token'].isin(valid_items.index))
            ]

            iteration += 1
            print(f"  Iteration {iteration}: {len(filtered_df):,} interactions remaining")

            # 수렴 확인
            if len(filtered_df) == prev_len or len(filtered_df) == 0:
                print(f"  ✓ K-core decomposition completed at iteration {iteration}")
                break

        self.print_comparison(f"K-core Decomposition (k={k})", filtered_df)

        return filtered_df


class InteractionDensityFilter(DataFilteringStrategy):
    """상호작용 밀도 기반 필터링"""

    def filter(self, target_sparsity=0.99):
        """
        목표 희소성에 도달할 때까지 낮은 활동 사용자/아이템 제거

        Args:
            target_sparsity: 목표 희소성 (0-1)
        """
        filtered_df = self.df.copy()
        iteration = 0

        print(f"  Targeting sparsity: {target_sparsity:.4f}...")

        while True:
            n_users = filtered_df['user_id:token'].nunique()
            n_items = filtered_df['item_id:token'].nunique()
            n_interactions = len(filtered_df)
            current_sparsity = 1 - (n_interactions / (n_users * n_items))

            print(f"  Iteration {iteration + 1}: sparsity={current_sparsity:.6f}, interactions={n_interactions:,}")

            if current_sparsity >= target_sparsity:
                print(f"  ✓ Target sparsity reached")
                break

            # 가장 활동이 적은 사용자 1% 제거
            user_counts = filtered_df.groupby('user_id:token').size()
            threshold = user_counts.quantile(0.01)

            filtered_df = filtered_df[
                filtered_df['user_id:token'].isin(
                    user_counts[user_counts > threshold].index
                )
            ]

            iteration += 1

            if iteration > 100:  # 안전장치
                print(f"  ⚠ Max iterations reached")
                break

        self.print_comparison(
            f"Interaction Density (target_sparsity={target_sparsity})",
            filtered_df
        )

        return filtered_df


def save_filtered_data(filtered_df, output_path):
    """필터링된 데이터 저장"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    filtered_df.to_csv(output_path, index=False)
    print(f"\n✅ Filtered data saved to: {output_path}")


def main():
    """메인 실행 함수"""
    data_path = '../dataset/steam/steam.inter'

    print("\n" + "="*80)
    print("🚀 EASE Model Data Filtering Strategies Comparison")
    print("="*80 + "\n")

    results = {}

    # 1. 사용자 활동 필터링
    print("\n🔹 STRATEGY 1: User Activity Filtering")
    print("-" * 80)
    user_filter = UserActivityFilter(data_path)
    results['User Activity (20-500)'] = user_filter.filter(min_interactions=20, max_interactions=500)

    # 2. 아이템 인기도 필터링
    print("\n🔹 STRATEGY 2: Item Popularity Filtering")
    print("-" * 80)
    item_filter = ItemPopularityFilter(data_path)
    results['Item Popularity (20-1000)'] = item_filter.filter(min_popularity=20, max_popularity=1000)

    # 3. 결합 필터링 (단일 반복)
    print("\n🔹 STRATEGY 3: Combined Filtering (Single Pass)")
    print("-" * 80)
    combined_filter = CombinedFilter(data_path)
    results['Combined (Single Pass)'] = combined_filter.filter(
        min_user_interactions=20,
        max_user_interactions=500,
        min_item_popularity=20,
        max_item_popularity=1000,
        iterations=1
    )

    # 4. 결합 필터링 (수렴까지)
    print("\n🔹 STRATEGY 4: Combined Filtering (Until Convergence)")
    print("-" * 80)
    combined_filter2 = CombinedFilter(data_path)
    results['Combined (Convergence)'] = combined_filter2.filter(
        min_user_interactions=20,
        min_item_popularity=20,
        iterations=10
    )

    # 5. K-core 필터링 (k=10)
    print("\n🔹 STRATEGY 5: K-core Decomposition (k=10)")
    print("-" * 80)
    kcore_filter = KCoreFilter(data_path)
    results['K-core (k=10)'] = kcore_filter.filter(k=10)

    # 6. K-core 필터링 (k=20)
    print("\n🔹 STRATEGY 6: K-core Decomposition (k=20)")
    print("-" * 80)
    kcore_filter2 = KCoreFilter(data_path)
    results['K-core (k=20)'] = kcore_filter2.filter(k=20)

    # 7. 밀도 기반 필터링
    print("\n🔹 STRATEGY 7: Interaction Density Filtering")
    print("-" * 80)
    density_filter = InteractionDensityFilter(data_path)
    results['Density (0.995)'] = density_filter.filter(target_sparsity=0.995)

    # 비교 요약
    print("\n\n" + "="*80)
    print("📈 COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Strategy':<35} {'Users':>10} {'Items':>10} {'Memory(GB)':>12} {'Speedup':>8}")
    print("-" * 80)

    summary_data = []
    for name, df in results.items():
        filter_obj = CombinedFilter(data_path)
        stats = filter_obj.get_stats(df)
        print(f"{name:<35} {stats['users']:>10,} {stats['items']:>10,} {stats['memory_gb']:>12.2f} {stats['memory_gb'] / filter_obj.get_stats(user_filter.df)['memory_gb']:>8.2f}x")
        summary_data.append((name, stats))

    # 권장사항
    print("\n" + "="*80)
    print("✨ RECOMMENDATIONS FOR EASE MODEL")
    print("="*80)
    print("""
🏆 BEST OPTIONS (순위):

1️⃣  K-core Decomposition (k=10) ⭐⭐⭐
   - 이론적으로 가장 견고한 방법
   - 모든 노드(사용자/아이템)가 최소 k개 이웃을 보장
   - 고립된 노드 자동 제거
   - 메모리 효율적
   → 추천 사용!

2️⃣  Combined Filtering with Convergence ⭐⭐
   - 실무에서 직관적이고 이해하기 쉬움
   - 사용자 활동과 아이템 인기도 동시 고려
   - 여러 반복으로 장기적 필터링
   → 대안으로 추천

3️⃣  K-core Decomposition (k=20) ⭐⭐
   - k=10보다 더 공격적인 필터링
   - 매우 높은 메모리 효율
   - 추천 시스템 성능 향상 가능
   → 메모리가 매우 제한적일 때 사용

⚠️  피해야 할 방법:
   ❌ User Activity만 사용 (아이템 고립)
   ❌ Item Popularity만 사용 (사용자 고립)
   ❌ 단일 필터링 (일부 노드 고립 가능)
   ❌ 극단적인 임계값

📊 MEMORY TARGETS FOR EASE:
   - Dense matrix 권장: < 4-8 GB
   - 최적 행렬 크기: 50K-100K users × 10K-20K items
   - 예상 메모리: 2-8 GB 범위
    """)

    # 최고 성능 옵션들 저장
    print("\n" + "="*80)
    print("💾 SAVING RECOMMENDED OPTIONS")
    print("="*80)

    save_filtered_data(results['K-core (k=10)'], '../dataset/steam/steam_filtered_kcore10.inter')
    save_filtered_data(results['K-core (k=20)'], '../dataset/steam/steam_filtered_kcore20.inter')
    save_filtered_data(results['Combined (Convergence)'], '../dataset/steam/steam_filtered_combined.inter')

    print("\n" + "="*80)
    print("✅ ALL ANALYSES COMPLETE!")
    print("="*80)
    print("\n사용할 파일을 선택하세요:")
    print("  1. steam_filtered_kcore10.inter (권장)")
    print("  2. steam_filtered_kcore20.inter (메모리 제약이 있을 때)")
    print("  3. steam_filtered_combined.inter (대안)")


if __name__ == '__main__':
    main()
