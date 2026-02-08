#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
데이터셋 검증: 품질 확인 및 통계

RecBole 형식의 데이터셋이 제대로 생성되었는지 검증합니다.
"""

import os
import pandas as pd
import numpy as np
import argparse
import logging
from typing import Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetValidator:
    """데이터셋 검증 및 통계"""

    def __init__(self, dataset_dir: str, dataset_name: str = "steam_optimal"):
        self.dataset_dir = dataset_dir
        self.dataset_name = dataset_name
        self.inter_df = None
        self.item_df = None
        self.user_df = None

    def load_files(self):
        """파일 로드"""
        logger.info("Loading dataset files...")

        inter_path = os.path.join(self.dataset_dir, f"{self.dataset_name}.inter")
        item_path = os.path.join(self.dataset_dir, f"{self.dataset_name}.item")
        user_path = os.path.join(self.dataset_dir, f"{self.dataset_name}.user")

        try:
            self.inter_df = pd.read_csv(inter_path, sep='\t')
            logger.info(f"✅ Loaded {len(self.inter_df):,} interactions")
        except FileNotFoundError:
            logger.error(f"❌ Not found: {inter_path}")
            raise

        try:
            self.item_df = pd.read_csv(item_path, sep='\t')
            logger.info(f"✅ Loaded {len(self.item_df):,} items")
        except FileNotFoundError:
            logger.warning(f"⚠️ Not found: {item_path}")

        try:
            self.user_df = pd.read_csv(user_path, sep='\t')
            logger.info(f"✅ Loaded {len(self.user_df):,} users")
        except FileNotFoundError:
            logger.warning(f"⚠️ Not found: {user_path}")

    def validate_inter_format(self) -> bool:
        """
        .inter 파일 형식 검증

        Required columns:
        - user_id:token
        - item_id:token
        - rating:float (or similar)
        - timestamp:float
        """
        logger.info("\n" + "="*80)
        logger.info("VALIDATING .inter FORMAT")
        logger.info("="*80)

        # 컬럼 확인
        expected_cols = ['user_id:token', 'item_id:token']
        missing_cols = [col for col in expected_cols if col not in self.inter_df.columns]

        if missing_cols:
            logger.error(f"❌ Missing columns: {missing_cols}")
            return False

        logger.info("✅ Required columns found")
        logger.info(f"  Columns: {list(self.inter_df.columns)}")

        # 데이터 타입 확인
        logger.info("\n✅ Column data types:")
        for col in self.inter_df.columns:
            logger.info(f"  {col}: {self.inter_df[col].dtype}")

        # Null 값 확인
        null_counts = self.inter_df.isnull().sum()
        if null_counts.any():
            logger.warning("⚠️ Null values detected:")
            for col, count in null_counts[null_counts > 0].items():
                logger.warning(f"  {col}: {count}")
        else:
            logger.info("✅ No null values found")

        return True

    def validate_consistency(self) -> bool:
        """
        데이터 일관성 검증

        - .item에 없는 item_id가 .inter에 있는지 확인
        - .user에 없는 user_id가 .inter에 있는지 확인
        """
        logger.info("\n" + "="*80)
        logger.info("VALIDATING DATA CONSISTENCY")
        logger.info("="*80)

        inter_items = set(self.inter_df['item_id:token'].unique())
        inter_users = set(self.inter_df['user_id:token'].unique())

        if self.item_df is not None:
            item_file_items = set(self.item_df['item_id:token'].unique())
            missing_items = inter_items - item_file_items
            if missing_items:
                logger.warning(f"⚠️ Items in .inter but not in .item: {len(missing_items)}")
            else:
                logger.info("✅ All items in .inter are in .item")
        else:
            logger.info("⚠️ .item file not loaded, skipping item validation")

        if self.user_df is not None:
            user_file_users = set(self.user_df['user_id:token'].unique())
            missing_users = inter_users - user_file_users
            if missing_users:
                logger.warning(f"⚠️ Users in .inter but not in .user: {len(missing_users)}")
            else:
                logger.info("✅ All users in .inter are in .user")
        else:
            logger.info("⚠️ .user file not loaded, skipping user validation")

        return True

    def validate_kcore_property(self, k: int = 30) -> bool:
        """
        K-core 특성 검증

        모든 사용자가 최소 k개 게임을 소유하고,
        모든 게임이 최소 k명에게 소유되었는지 확인
        """
        logger.info(f"\n" + "="*80)
        logger.info(f"VALIDATING K-CORE PROPERTY (k={k})")
        logger.info("="*80)

        user_counts = self.inter_df['user_id:token'].value_counts()
        item_counts = self.inter_df['item_id:token'].value_counts()

        users_below_k = (user_counts < k).sum()
        items_below_k = (item_counts < k).sum()

        if users_below_k == 0:
            logger.info(f"✅ All users have >= {k} interactions")
        else:
            logger.warning(f"⚠️ {users_below_k} users have < {k} interactions")

        if items_below_k == 0:
            logger.info(f"✅ All items have >= {k} interactions")
        else:
            logger.warning(f"⚠️ {items_below_k} items have < {k} interactions")

        return users_below_k == 0 and items_below_k == 0

    def validate_no_duplicates(self) -> bool:
        """중복 상호작용 확인"""
        logger.info(f"\n" + "="*80)
        logger.info("VALIDATING DUPLICATES")
        logger.info("="*80)

        # (user_id, item_id) 쌍이 유일한지 확인
        duplicates = self.inter_df.duplicated(
            subset=['user_id:token', 'item_id:token']
        ).sum()

        if duplicates == 0:
            logger.info("✅ No duplicate user-item pairs")
            return True
        else:
            logger.warning(f"⚠️ {duplicates} duplicate pairs found")
            return False

    def print_statistics(self):
        """데이터셋 통계 출력"""
        logger.info("\n" + "="*80)
        logger.info("DATASET STATISTICS")
        logger.info("="*80)

        n_interactions = len(self.inter_df)
        n_users = self.inter_df['user_id:token'].nunique()
        n_items = self.inter_df['item_id:token'].nunique()
        sparsity = 1 - (n_interactions / (n_users * n_items))
        density = 1 - sparsity

        logger.info(f"\nBasic Statistics:")
        logger.info(f"  Interactions: {n_interactions:,}")
        logger.info(f"  Users: {n_users:,}")
        logger.info(f"  Items: {n_items:,}")
        logger.info(f"  Sparsity: {sparsity:.4f}")
        logger.info(f"  Density: {density:.6f}")

        # 메모리 추정
        bytes_per_float = 4
        memory_gb = (n_users * n_items * bytes_per_float) / (1024 ** 3)
        logger.info(f"  Estimated memory (dense matrix): {memory_gb:.2f}GB")

        # 사용자 활동도 통계
        user_activity = self.inter_df['user_id:token'].value_counts()
        logger.info(f"\nUser Activity Statistics:")
        logger.info(f"  Min: {user_activity.min()}, Max: {user_activity.max()}")
        logger.info(f"  Mean: {user_activity.mean():.2f}, Median: {user_activity.median():.2f}")
        logger.info(f"  Std: {user_activity.std():.2f}")

        # 게임 인기도 통계
        item_popularity = self.inter_df['item_id:token'].value_counts()
        logger.info(f"\nItem Popularity Statistics:")
        logger.info(f"  Min: {item_popularity.min()}, Max: {item_popularity.max()}")
        logger.info(f"  Mean: {item_popularity.mean():.2f}, Median: {item_popularity.median():.2f}")
        logger.info(f"  Std: {item_popularity.std():.2f}")

        # Rating 통계 (있으면)
        if 'rating:float' in self.inter_df.columns:
            logger.info(f"\nRating Statistics:")
            rating_stats = self.inter_df['rating:float'].describe()
            logger.info(f"  Min: {rating_stats['min']:.2f}, Max: {rating_stats['max']:.2f}")
            logger.info(f"  Mean: {rating_stats['mean']:.2f}, Std: {rating_stats['std']:.2f}")

        logger.info("="*80)

    def run(self, check_kcore: bool = True):
        """전체 검증 파이프라인 실행"""
        logger.info("Starting dataset validation...")
        logger.info("="*80)

        # 파일 로드
        self.load_files()

        # 검증 실행
        checks = []
        checks.append(("Format validation", self.validate_inter_format()))
        checks.append(("Data consistency", self.validate_consistency()))
        if check_kcore:
            checks.append(("K-core property (k=30)", self.validate_kcore_property(k=30)))
        checks.append(("No duplicates", self.validate_no_duplicates()))

        # 통계 출력
        self.print_statistics()

        # 검증 결과 요약
        logger.info("\n" + "="*80)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*80)

        passed = sum(1 for _, result in checks if result)
        total = len(checks)

        for check_name, result in checks:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status}: {check_name}")

        logger.info(f"\nResult: {passed}/{total} checks passed")
        logger.info("="*80)

        if passed == total:
            logger.info("\n✅ All validations passed! Dataset is ready for training.")
            return True
        else:
            logger.warning(f"\n⚠️ {total - passed} validation(s) failed.")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate dataset quality"
    )
    parser.add_argument(
        "--dataset_dir",
        type=str,
        default="dataset/steam_optimal/",
        help="Dataset directory containing .inter, .item, .user files"
    )
    parser.add_argument(
        "--dataset_name",
        type=str,
        default="steam_optimal",
        help="Dataset name (prefix of files)"
    )
    parser.add_argument(
        "--check_kcore",
        action="store_true",
        default=True,
        help="Check K-core property"
    )

    args = parser.parse_args()

    validator = DatasetValidator(
        dataset_dir=args.dataset_dir,
        dataset_name=args.dataset_name
    )
    success = validator.run(check_kcore=args.check_kcore)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
