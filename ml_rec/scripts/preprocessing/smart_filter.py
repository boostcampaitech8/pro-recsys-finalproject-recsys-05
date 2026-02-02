#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SmartDataFilter: 메모리-데이터량 트레이드오프를 최적화하는 필터러

여러 K-core 값과 Item popularity max cap을 조합하여 테스트하고,
메모리 예측을 통해 최적의 필터링 조합을 추천합니다.
"""

import os
import pandas as pd
import numpy as np
import psutil
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmartDataFilter:
    """메모리-데이터량 트레이드오프를 최적화하는 필터러"""

    def __init__(self, data_path: str, target_memory_gb: float = 8.0):
        """
        Args:
            data_path: 입력 .inter 파일 경로
            target_memory_gb: 목표 메모리 (GB)
        """
        self.data_path = data_path
        self.target_memory_gb = target_memory_gb
        self.df = None
        self.results = []

        logger.info(f"Loading data from {data_path}")
        self.load_data()

        logger.info(f"Original data shape: {self.df.shape}")
        logger.info(f"Users: {self.df['user_id:token'].nunique()}, "
                    f"Items: {self.df['item_id:token'].nunique()}")

    def load_data(self):
        """RecBole .inter 파일 로드"""
        try:
            self.df = pd.read_csv(
                self.data_path,
                sep=None,  # Auto-detect separator (tab or comma)
                engine='python',
                na_values=['']
            )
            # 컬럼명 정규화 (공백 제거)
            self.df.columns = self.df.columns.str.strip()
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise

    def estimate_memory_gb(self, n_users: int, n_items: int) -> float:
        """
        Dense matrix 메모리 예측 (GB)

        EASE/LightGCN과 같은 모델들은 user-item interaction matrix를
        생성하므로 메모리는 대략 O(n_users * n_items)
        """
        bytes_per_float = 4  # float32
        bytes_per_int = 4    # int32

        # user-item matrix (float32)
        matrix_memory = (n_users * n_items * bytes_per_float) / (1024 ** 3)

        # overhead (인덱싱, 메타데이터 등)
        overhead = (n_users * bytes_per_int + n_items * bytes_per_int) / (1024 ** 3)

        total_memory = matrix_memory + overhead
        return total_memory

    def apply_kcore_filtering(self, df: pd.DataFrame, k: int, max_iterations: int = 10) -> pd.DataFrame:
        """
        K-core 필터링 적용 (반복)

        모든 사용자가 최소 k개 게임을 소유하고,
        모든 게임이 최소 k명에게 소유되도록 필터링
        """
        original_size = len(df)
        iteration = 0

        while iteration < max_iterations:
            # 사용자 활동도 계산
            user_counts = df['user_id:token'].value_counts()
            users_below_k = user_counts[user_counts < k].index

            # 게임 인기도 계산
            item_counts = df['item_id:token'].value_counts()
            items_below_k = item_counts[item_counts < k].index

            # 제거할 행 찾기
            mask = ~(df['user_id:token'].isin(users_below_k) |
                    df['item_id:token'].isin(items_below_k))

            new_df = df[mask].copy()

            # 수렴 체크
            if len(new_df) == len(df):
                logger.info(f"  K-core (k={k}): Converged at iteration {iteration}")
                break

            df = new_df
            iteration += 1

        removed = original_size - len(df)
        logger.info(f"  K-core (k={k}): Removed {removed} interactions "
                    f"({len(df)} remaining)")
        return df

    def apply_activity_range_filtering(
        self,
        df: pd.DataFrame,
        min_user_activity: int = 20,
        max_user_activity: int = 500,
        min_item_popularity: int = 20,
        max_item_popularity: Optional[int] = 1000
    ) -> pd.DataFrame:
        """
        사용자 활동도 및 아이템 인기도 범위 필터링
        """
        original_size = len(df)

        # 사용자 활동도 범위
        user_counts = df['user_id:token'].value_counts()
        valid_users = user_counts[
            (user_counts >= min_user_activity) & (user_counts <= max_user_activity)
        ].index
        df = df[df['user_id:token'].isin(valid_users)].copy()

        # 게임 인기도 범위
        item_counts = df['item_id:token'].value_counts()
        if max_item_popularity is None:
            valid_items = item_counts[item_counts >= min_item_popularity].index
        else:
            valid_items = item_counts[
                (item_counts >= min_item_popularity) &
                (item_counts <= max_item_popularity)
            ].index
        df = df[df['item_id:token'].isin(valid_items)].copy()

        removed = original_size - len(df)
        max_str = str(max_item_popularity) if max_item_popularity else "no_limit"
        logger.info(f"  Activity range ({min_user_activity}-{max_user_activity}, "
                    f"item:{min_item_popularity}-{max_str}): "
                    f"Removed {removed} interactions ({len(df)} remaining)")
        return df

    def apply_combined_filtering(
        self,
        k: int,
        min_user: int = 20,
        max_user: int = 500,
        min_item: int = 20,
        max_item: Optional[int] = 1000,
        iterations: int = 5
    ) -> pd.DataFrame:
        """
        K-core + Activity Range 필터링을 반복 적용
        """
        df = self.df.copy()

        for iter_idx in range(iterations):
            logger.info(f"Iteration {iter_idx + 1}/{iterations}")

            # Step 1: Activity range filtering
            df = self.apply_activity_range_filtering(
                df,
                min_user_activity=min_user,
                max_user_activity=max_user,
                min_item_popularity=min_item,
                max_item_popularity=max_item
            )

            # Step 2: K-core filtering
            df = self.apply_kcore_filtering(df, k=k, max_iterations=1)

            if len(df) == 0:
                logger.warning(f"No data left after iteration {iter_idx + 1}")
                break

        return df

    def get_stats(
        self,
        df: pd.DataFrame,
        k: int,
        item_max: Optional[int],
        filter_config: Dict
    ) -> Dict:
        """필터링 결과 통계 계산"""
        n_users = df['user_id:token'].nunique()
        n_items = df['item_id:token'].nunique()
        n_interactions = len(df)

        memory_gb = self.estimate_memory_gb(n_users, n_items)

        item_max_str = str(item_max) if item_max else "no_limit"

        stats = {
            "k": k,
            "item_max": item_max_str,
            "min_user": filter_config.get("min_user", 20),
            "max_user": filter_config.get("max_user", 500),
            "min_item": filter_config.get("min_item", 20),
            "n_users": n_users,
            "n_items": n_items,
            "n_interactions": n_interactions,
            "memory_gb": round(memory_gb, 2),
            "sparsity": round(1 - (n_interactions / (n_users * n_items)), 4),
            "user_interaction_stats": {
                "min": int(df['user_id:token'].value_counts().min()),
                "max": int(df['user_id:token'].value_counts().max()),
                "mean": round(float(df['user_id:token'].value_counts().mean()), 2)
            },
            "item_popularity_stats": {
                "min": int(df['item_id:token'].value_counts().min()),
                "max": int(df['item_id:token'].value_counts().max()),
                "mean": round(float(df['item_id:token'].value_counts().mean()), 2)
            }
        }

        return stats

    def test_filter_combinations(self) -> List[Dict]:
        """
        여러 K-core와 Item max cap 조합 테스트
        """
        k_values = [20, 25, 30]
        item_max_values = [1000, 2000, 3000, 5000, 10000, None]  # None = no_limit

        filter_config = {
            "min_user": 20,
            "max_user": 500,
            "min_item": 20
        }

        logger.info("="*80)
        logger.info("Testing filter combinations...")
        logger.info("="*80)

        results = []

        for k in k_values:
            for item_max in item_max_values:
                logger.info(f"\n[Test] K={k}, Item_max={item_max if item_max else 'no_limit'}")

                try:
                    filtered_df = self.apply_combined_filtering(
                        k=k,
                        min_user=filter_config["min_user"],
                        max_user=filter_config["max_user"],
                        min_item=filter_config["min_item"],
                        max_item=item_max,
                        iterations=5
                    )

                    stats = self.get_stats(filtered_df, k, item_max, filter_config)
                    results.append(stats)

                    # 요약 출력
                    logger.info(f"✓ Result: Memory={stats['memory_gb']}GB, "
                                f"Interactions={stats['n_interactions']:,}, "
                                f"Users={stats['n_users']:,}, "
                                f"Items={stats['n_items']:,}")

                except Exception as e:
                    logger.error(f"✗ Failed: {e}")
                    continue

        self.results = results
        return results

    def recommend_best_options(self, top_k: int = 5) -> List[Dict]:
        """메모리 한계 내에서 최적의 옵션 추천"""
        if not self.results:
            logger.warning("No results to recommend")
            return []

        # 메모리 한계 내 결과 필터링
        valid_results = [r for r in self.results
                        if r['memory_gb'] <= self.target_memory_gb]

        if not valid_results:
            logger.warning(f"No results within {self.target_memory_gb}GB target")
            # 가장 메모리가 적은 것들 추천
            valid_results = sorted(self.results, key=lambda x: x['memory_gb'])[:top_k]

        # 상호작용 수 기준 정렬 (많을수록 좋음)
        sorted_results = sorted(valid_results,
                              key=lambda x: x['n_interactions'],
                              reverse=True)

        logger.info("\n" + "="*80)
        logger.info("RECOMMENDED OPTIONS (Top 5)")
        logger.info("="*80)

        for idx, result in enumerate(sorted_results[:top_k], 1):
            logger.info(f"\n{idx}. K={result['k']}, Item_max={result['item_max']}")
            logger.info(f"   Memory: {result['memory_gb']}GB "
                       f"(Target: {self.target_memory_gb}GB)")
            logger.info(f"   Interactions: {result['n_interactions']:,}")
            logger.info(f"   Users: {result['n_users']:,}, Items: {result['n_items']:,}")
            logger.info(f"   Sparsity: {result['sparsity']}")

        return sorted_results[:top_k]

    def save_results(self, output_dir: str):
        """결과를 CSV 및 JSON으로 저장"""
        os.makedirs(output_dir, exist_ok=True)

        # CSV로 저장
        results_df = pd.DataFrame(self.results)
        csv_path = os.path.join(output_dir, "filter_results.csv")
        results_df.to_csv(csv_path, index=False)
        logger.info(f"\n✓ Results saved to {csv_path}")

        # JSON으로 저장 (권장 옵션)
        recommended = self.recommend_best_options()
        json_path = os.path.join(output_dir, "recommended_options.json")
        with open(json_path, 'w') as f:
            json.dump(recommended, f, indent=2)
        logger.info(f"✓ Recommended options saved to {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Test multiple filtering combinations to find optimal configuration"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input .inter file path"
    )
    parser.add_argument(
        "--target_memory",
        type=float,
        default=8.0,
        help="Target memory in GB (default: 8.0)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="filter_results",
        help="Output directory for results"
    )

    args = parser.parse_args()

    # SmartFilter 실행
    filter_obj = SmartDataFilter(
        data_path=args.input,
        target_memory_gb=args.target_memory
    )

    # 모든 조합 테스트
    filter_obj.test_filter_combinations()

    # 최적 옵션 추천 및 저장
    filter_obj.save_results(args.output_dir)

    logger.info("\n✓ Smart filtering completed!")


if __name__ == "__main__":
    main()
