#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
선택된 최적 필터링 옵션으로 steam_optimal.inter 생성

K=30, Item_max=10000 설정으로 최종 데이터셋 생성
"""

import os
import pandas as pd
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OptimalDatasetCreator:
    """최적 필터링 옵션으로 데이터셋 생성"""

    def __init__(self, input_path: str, output_dir: str):
        self.input_path = input_path
        self.output_dir = output_dir
        self.df = None

        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")

    def load_data(self):
        """데이터 로드"""
        # [Refinement] RecBole 및 데이터 브릿지와의 호환성을 위해 탭(\t) 구분자 사용
        self.df = pd.read_csv(self.input_path, sep='\t')
        self.df.columns = self.df.columns.str.strip()
        logger.info(f"Loaded {len(self.df):,} interactions")
        logger.info(f"Users: {self.df['user_id:token'].nunique():,}, "
                    f"Items: {self.df['item_id:token'].nunique():,}")

    def apply_kcore_filtering(self, df: pd.DataFrame, k: int = 30, max_iterations: int = 10) -> pd.DataFrame:
        """K-core 필터링"""
        logger.info(f"Applying K-core filtering (k={k})...")

        iteration = 0

        while iteration < max_iterations:
            user_counts = df['user_id:token'].value_counts()
            users_below_k = user_counts[user_counts < k].index

            item_counts = df['item_id:token'].value_counts()
            items_below_k = item_counts[item_counts < k].index

            mask = ~(df['user_id:token'].isin(users_below_k) |
                    df['item_id:token'].isin(items_below_k))

            new_df = df[mask].copy()

            if len(new_df) == len(df):
                logger.info(f"  K-core: Converged at iteration {iteration + 1}")
                break

            df = new_df
            iteration += 1

        logger.info(f"  Removed interactions ({len(df):,} remaining)")
        return df

    def apply_activity_range_filtering(
        self,
        df: pd.DataFrame,
        min_user: int = 20,
        max_user: int = 500,
        min_item: int = 20,
        max_item: int = 10000
    ) -> pd.DataFrame:
        """활동도 범위 필터링"""
        logger.info(f"Applying activity range filtering...")
        logger.info(f"  User activity: {min_user}-{max_user}, Item popularity: {min_item}-{max_item}")

        original_size = len(df)

        # User activity range
        user_counts = df['user_id:token'].value_counts()
        valid_users = user_counts[
            (user_counts >= min_user) & (user_counts <= max_user)
        ].index
        df = df[df['user_id:token'].isin(valid_users)].copy()

        # Item popularity range
        item_counts = df['item_id:token'].value_counts()
        valid_items = item_counts[
            (item_counts >= min_item) & (item_counts <= max_item)
        ].index
        df = df[df['item_id:token'].isin(valid_items)].copy()

        removed = original_size - len(df)
        logger.info(f"  Removed {removed:,} interactions ({len(df):,} remaining)")
        return df

    def apply_combined_filtering(
        self,
        k: int = 30,
        min_user: int = 20,
        max_user: int = 500,
        min_item: int = 20,
        max_item: int = 10000,
        iterations: int = 5
    ) -> pd.DataFrame:
        """K-core + Activity range 반복 필터링"""
        logger.info("="*80)
        logger.info("Starting combined filtering (K-core + Activity range)")
        logger.info("="*80)

        df = self.df.copy()

        for iter_idx in range(iterations):
            logger.info(f"\nIteration {iter_idx + 1}/{iterations}")

            # Activity range
            df = self.apply_activity_range_filtering(
                df,
                min_user=min_user,
                max_user=max_user,
                min_item=min_item,
                max_item=max_item
            )

            # K-core
            df = self.apply_kcore_filtering(df, k=k, max_iterations=1)

            if len(df) == 0:
                logger.warning(f"No data remaining after iteration {iter_idx + 1}")
                break

        return df

    def save_dataset(self, df: pd.DataFrame, output_name: str = "steam_optimal"):
        """데이터셋 저장"""
        output_path = os.path.join(self.output_dir, f"{output_name}.inter")

        logger.info(f"\nSaving filtered dataset to {output_path}...")
        df.to_csv(output_path, index=False, sep='\t')

        logger.info(f"✅ {len(df):,} 상호작용 저장 완료")
        logger.info(f"✅ Users: {df['user_id:token'].nunique():,}")
        logger.info(f"✅ Items: {df['item_id:token'].nunique():,}")

        # .item 및 .user 메타데이터 생성 및 저장
        self.save_item_user_metadata(df, output_name)

        return output_path

    def save_item_user_metadata(self, df: pd.DataFrame, output_name: str):
        """아이템 및 사용자 메타데이터 (.item, .user) 생성 및 저장"""
        # 1. .item 파일 생성: [item_id:token, popularity:float, avg_rating:float]
        item_stats = df.groupby('item_id:token')['rating:float'].agg(['count', 'mean']).reset_index()
        item_stats.columns = ['item_id:token', 'popularity:float', 'avg_rating:float']

        item_path = os.path.join(self.output_dir, f"{output_name}.item")
        item_stats.to_csv(item_path, index=False, sep='\t')
        logger.info(f"✅ Saved item metadata to {item_path} ({len(item_stats)} items)")

        # 2. .user 파일 생성: [user_id:token, num_items:float, avg_playtime:float]
        user_stats = df.groupby('user_id:token')['rating:float'].agg(['count', 'mean']).reset_index()
        user_stats.columns = ['user_id:token', 'num_items:float', 'avg_playtime:float']

        user_path = os.path.join(self.output_dir, f"{output_name}.user")
        user_stats.to_csv(user_path, index=False, sep='\t')
        logger.info(f"✅ Saved user metadata to {user_path} ({len(user_stats)} users)")

    def get_dataset_stats(self, df: pd.DataFrame):
        """데이터셋 통계"""
        n_users = df['user_id:token'].nunique()
        n_items = df['item_id:token'].nunique()
        n_interactions = len(df)

        # 메모리 추정
        bytes_per_float = 4
        memory_gb = (n_users * n_items * bytes_per_float) / (1024 ** 3)

        # 통계
        user_stats = df['user_id:token'].value_counts()
        item_stats = df['item_id:token'].value_counts()

        logger.info("\n" + "="*80)
        logger.info("FINAL DATASET STATISTICS")
        logger.info("="*80)
        logger.info(f"Interactions: {n_interactions:,}")
        logger.info(f"Users: {n_users:,}")
        logger.info(f"Items: {n_items:,}")
        logger.info(f"Sparsity: {1 - (n_interactions / (n_users * n_items)):.4f}")
        logger.info(f"Estimated memory (dense): {memory_gb:.2f}GB")
        logger.info(f"\nUser activity statistics:")
        logger.info(f"  Min: {user_stats.min()}, Max: {user_stats.max()}")
        logger.info(f"  Mean: {user_stats.mean():.2f}, Std: {user_stats.std():.2f}")
        logger.info(f"\nItem popularity statistics:")
        logger.info(f"  Min: {item_stats.min()}, Max: {item_stats.max()}")
        logger.info(f"  Mean: {item_stats.mean():.2f}, Std: {item_stats.std():.2f}")
        logger.info("="*80)

    def run(self):
        """전체 파이프라인 실행"""
        # 데이터 로드
        self.load_data()

        # 필터링 적용
        filtered_df = self.apply_combined_filtering(
            k=30,
            min_user=20,
            max_user=500,
            min_item=20,
            max_item=10000,
            iterations=5
        )

        # 통계
        self.get_dataset_stats(filtered_df)

        # 저장
        output_path = self.save_dataset(filtered_df, output_name="steam_optimal")

        logger.info(f"\n✅ Dataset creation completed!")
        logger.info(f"Output: {output_path}")

        return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Create optimal dataset with selected filtering options"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input .inter file path"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="dataset/steam_optimal/",
        help="Output directory (default: dataset/steam_optimal/)"
    )

    args = parser.parse_args()

    creator = OptimalDatasetCreator(
        input_path=args.input,
        output_dir=args.output_dir
    )
    creator.run()


if __name__ == "__main__":
    main()
