#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RecBole 포맷 변환: .inter, .item, .user 파일 생성

입력: steam_optimal.inter (user_id, item_id, rating)
출력:
- steam_optimal.inter (RecBole format with timestamp)
- steam_optimal.item (item metadata)
- steam_optimal.user (user profile)
"""

import os
import pandas as pd
import numpy as np
import argparse
import logging
from pathlib import Path
from typing import Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RecBoleFormatConverter:
    """RecBole 포맷으로 변환"""

    def __init__(self, inter_path: str, output_dir: str, dataset_name: str = "steam_optimal"):
        self.inter_path = inter_path
        self.output_dir = output_dir
        self.dataset_name = dataset_name
        self.inter_df = None
        self.item_df = None
        self.user_df = None

        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")

    def load_data(self):
        """데이터 로드"""
        logger.info(f"Loading interaction data from {self.inter_path}...")
        self.inter_df = pd.read_csv(self.inter_path)
        self.inter_df.columns = self.inter_df.columns.str.strip()
        logger.info(f"Loaded {len(self.inter_df):,} interactions")

    def prepare_inter_file(self) -> pd.DataFrame:
        """
        RecBole .inter 파일 준비

        Format: user_id:token    item_id:token    rating:float    timestamp:float
        """
        logger.info("\nPreparing .inter file...")

        inter_df = self.inter_df.copy()

        # rating 확인 및 준비
        if 'rating:float' not in inter_df.columns and 'rating' not in inter_df.columns:
            logger.info("  Adding rating column (default: 1.0)")
            inter_df['rating:float'] = 1.0
        elif 'rating' in inter_df.columns and 'rating:float' not in inter_df.columns:
            inter_df.rename(columns={'rating': 'rating:float'}, inplace=True)

        # timestamp 생성 (없으면)
        if 'timestamp:float' not in inter_df.columns and 'timestamp' not in inter_df.columns:
            logger.info("  Generating timestamp column (sequential)")
            # 순차적 timestamp 생성 (소팅 후)
            inter_df = inter_df.sort_values(['user_id:token', 'item_id:token']).reset_index(drop=True)
            inter_df['timestamp:float'] = range(len(inter_df))
        elif 'timestamp' in inter_df.columns and 'timestamp:float' not in inter_df.columns:
            inter_df.rename(columns={'timestamp': 'timestamp:float'}, inplace=True)

        # 필요한 컬럼만 선택
        inter_df = inter_df[['user_id:token', 'item_id:token', 'rating:float', 'timestamp:float']]

        logger.info(f"  ✅ Prepared {len(inter_df):,} interactions")
        return inter_df

    def prepare_item_file(self) -> pd.DataFrame:
        """
        RecBole .item 파일 준비

        Format: item_id:token    [추가 메타데이터...]

        이 프로젝트에서는 기본적으로 item_id만 포함
        나중에 Steam API에서 메타데이터 추가 가능
        """
        logger.info("\nPreparing .item file...")

        # 고유한 item_id 추출
        item_ids = self.inter_df['item_id:token'].unique()
        item_df = pd.DataFrame({'item_id:token': item_ids})

        # 추가 메타데이터 계산 (선택사항)
        # - popularity: 이 아이템을 플레이한 사용자 수
        # - avg_rating: 평균 평점

        item_popularity = self.inter_df.groupby('item_id:token').size().reset_index(name='popularity:float')
        item_df = item_df.merge(item_popularity, on='item_id:token', how='left')

        # rating이 있으면 평균 계산
        if 'rating:float' in self.inter_df.columns:
            item_rating = self.inter_df.groupby('item_id:token')['rating:float'].mean().reset_index(
                name='avg_rating:float'
            )
            item_df = item_df.merge(item_rating, on='item_id:token', how='left')

        logger.info(f"  ✅ Prepared {len(item_df):,} items")
        return item_df

    def prepare_user_file(self) -> pd.DataFrame:
        """
        RecBole .user 파일 준비

        Format: user_id:token    [추가 프로필...]

        이 프로젝트에서는 기본적으로 user_id만 포함
        나중에 Steam 프로필 정보 추가 가능
        """
        logger.info("\nPreparing .user file...")

        # 고유한 user_id 추출
        user_ids = self.inter_df['user_id:token'].unique()
        user_df = pd.DataFrame({'user_id:token': user_ids})

        # 사용자 통계 계산 (선택사항)
        # - num_items: 플레이한 게임 수
        # - avg_rating: 평균 플레이 시간

        user_activity = self.inter_df.groupby('user_id:token').size().reset_index(name='num_items:float')
        user_df = user_df.merge(user_activity, on='user_id:token', how='left')

        # rating이 있으면 평균 계산
        if 'rating:float' in self.inter_df.columns:
            user_rating = self.inter_df.groupby('user_id:token')['rating:float'].mean().reset_index(
                name='avg_playtime:float'
            )
            user_df = user_df.merge(user_rating, on='user_id:token', how='left')

        logger.info(f"  ✅ Prepared {len(user_df):,} users")
        return user_df

    def save_files(self, inter_df: pd.DataFrame, item_df: pd.DataFrame, user_df: pd.DataFrame):
        """파일 저장"""
        logger.info("\n" + "="*80)
        logger.info("Saving RecBole format files...")
        logger.info("="*80)

        # .inter 파일
        inter_path = os.path.join(self.output_dir, f"{self.dataset_name}.inter")
        inter_df.to_csv(inter_path, sep='\t', index=False)
        logger.info(f"✅ Saved: {inter_path}")
        logger.info(f"  Rows: {len(inter_df):,}, Columns: {inter_df.shape[1]}")

        # .item 파일
        item_path = os.path.join(self.output_dir, f"{self.dataset_name}.item")
        item_df.to_csv(item_path, sep='\t', index=False)
        logger.info(f"✅ Saved: {item_path}")
        logger.info(f"  Rows: {len(item_df):,}, Columns: {item_df.shape[1]}")

        # .user 파일
        user_path = os.path.join(self.output_dir, f"{self.dataset_name}.user")
        user_df.to_csv(user_path, sep='\t', index=False)
        logger.info(f"✅ Saved: {user_path}")
        logger.info(f"  Rows: {len(user_df):,}, Columns: {user_df.shape[1]}")

        logger.info("="*80)

    def run(self):
        """전체 파이프라인 실행"""
        self.load_data()

        inter_df = self.prepare_inter_file()
        item_df = self.prepare_item_file()
        user_df = self.prepare_user_file()

        self.save_files(inter_df, item_df, user_df)

        logger.info(f"\n✅ RecBole format conversion completed!")
        logger.info(f"Output files:")
        logger.info(f"  - {self.output_dir}/{self.dataset_name}.inter")
        logger.info(f"  - {self.output_dir}/{self.dataset_name}.item")
        logger.info(f"  - {self.output_dir}/{self.dataset_name}.user")


def main():
    parser = argparse.ArgumentParser(
        description="Convert to RecBole format (.inter, .item, .user)"
    )
    parser.add_argument(
        "--inter",
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
    parser.add_argument(
        "--dataset_name",
        type=str,
        default="steam_optimal",
        help="Dataset name for output files"
    )

    args = parser.parse_args()

    converter = RecBoleFormatConverter(
        inter_path=args.inter,
        output_dir=args.output_dir,
        dataset_name=args.dataset_name
    )
    converter.run()


if __name__ == "__main__":
    main()
