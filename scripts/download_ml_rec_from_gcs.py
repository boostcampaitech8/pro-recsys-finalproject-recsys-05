#!/usr/bin/env python3
"""
Week 4: GCS → ML Rec 다운로드 스크립트

새 환경에서 모델/후보/데이터셋을 GCS에서 다운로드합니다.

사용법:
    python scripts/download_ml_rec_from_gcs.py      # 모든 파일 다운로드
    python scripts/download_ml_rec_from_gcs.py models   # 모델만 다운로드
    python scripts/download_ml_rec_from_gcs.py candidates # 후보만 다운로드
"""

import sys
import os
import yaml
import argparse
from pathlib import Path

# backend 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from scripts.gcs_utils import download_blob
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """gcs_config.yaml 로드"""
    config_path = Path(__file__).parent.parent / 'configs' / 'gcs_config.yaml'

    if not config_path.exists():
        logger.error(f"❌ 설정 파일 없음: {config_path}")
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def download_ml_rec(config, category=None):
    """GCS에서 ML Rec 파일 다운로드"""
    bucket_name = config['gcs']['bucket_name']
    ml_rec_config = config.get('ml_rec', {})
    data_root = ml_rec_config.get('data_root', 'ml_rec')
    files = ml_rec_config.get('files', {})

    if not files:
        logger.warning("⚠️ ml_rec 설정이 비어있습니다")
        return False

    # 프로젝트 루트 경로
    project_root = Path(__file__).parent.parent

    total_files = 0
    success_count = 0

    for filename, paths in files.items():
        # 카테고리 필터
        if category:
            file_category = filename.split('_')[0].lower()
            if file_category not in category.lower():
                continue

        local_path = project_root / data_root / paths['local_path']
        upload_path = paths['upload_path']

        # 로컬 디렉토리 생성
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # 이미 있으면 스킵
        if local_path.exists():
            file_size_mb = local_path.stat().st_size / (1024 ** 2)
            logger.info(f"⏭️  이미 존재: {filename} ({file_size_mb:.1f}MB)")
            continue

        total_files += 1
        logger.info(f"\n📥 다운로드: {filename}")
        logger.info(f"   GCS: gs://{bucket_name}/{upload_path}")
        logger.info(f"   로컬: {local_path}")

        try:
            result = download_blob(bucket_name, upload_path, str(local_path))
            if result:
                file_size_mb = local_path.stat().st_size / (1024 ** 2)
                success_count += 1
                logger.info(f"✅ 다운로드 완료: {filename} ({file_size_mb:.1f}MB)")
            else:
                logger.error(f"❌ 다운로드 실패: {filename}")
        except Exception as e:
            logger.error(f"❌ 오류: {filename} - {e}")

    # 결과 요약
    logger.info("\n" + "="*60)
    logger.info(f"📊 다운로드 완료")
    logger.info(f"   총: {total_files} 파일")
    logger.info(f"   성공: {success_count}/{total_files}")
    logger.info(f"   경로: {project_root / data_root}/")
    logger.info("="*60)

    return success_count == total_files or total_files == 0


def main():
    parser = argparse.ArgumentParser(
        description='GCS에서 ML Rec 파일을 다운로드합니다',
        epilog='예: python download_ml_rec_from_gcs.py models'
    )
    parser.add_argument(
        'category',
        nargs='?',
        default=None,
        help='다운로드 카테고리 (models, candidates, dataset, 기본값: 전부)'
    )

    args = parser.parse_args()

    # 설정 로드
    config = load_config()
    if not config:
        sys.exit(1)

    logger.info("="*60)
    logger.info("🚀 GCS → ML Rec 다운로드 시작")
    logger.info("="*60)

    # 다운로드 실행
    success = download_ml_rec(config, args.category)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
