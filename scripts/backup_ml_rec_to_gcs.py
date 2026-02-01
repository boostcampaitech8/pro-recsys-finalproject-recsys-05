#!/usr/bin/env python3
"""
Week 4: ML Rec 대용량 파일 → GCS 백업 스크립트

사용법:
    python scripts/backup_ml_rec_to_gcs.py      # 모든 파일 백업
    python scripts/backup_ml_rec_to_gcs.py models   # 모델만 백업
    python scripts/backup_ml_rec_to_gcs.py candidates # 후보만 백업
"""

import sys
import os
import yaml
import argparse
from pathlib import Path

# backend 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from scripts.gcs_utils import upload_blob
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


def backup_ml_rec(config, category=None):
    """ML Rec 파일 백업"""
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
        # 카테고리 필터 (models, candidates, dataset)
        if category:
            file_category = filename.split('_')[0].lower()
            if file_category not in category.lower():
                continue

        local_path = project_root / data_root / paths['local_path']
        upload_path = paths['upload_path']

        # 파일 존재 확인
        if not local_path.exists():
            logger.warning(f"⚠️ 파일 없음: {local_path}")
            continue

        # 파일 크기 확인
        file_size_mb = local_path.stat().st_size / (1024 ** 2)

        total_files += 1
        logger.info(f"\n📤 업로드: {filename} ({file_size_mb:.1f}MB)")
        logger.info(f"   로컬: {local_path}")
        logger.info(f"   GCS: gs://{bucket_name}/{upload_path}")

        try:
            result = upload_blob(bucket_name, str(local_path), upload_path)
            if result:
                success_count += 1
                logger.info(f"✅ 업로드 완료: {filename}")
            else:
                logger.error(f"❌ 업로드 실패: {filename}")
        except Exception as e:
            logger.error(f"❌ 오류: {filename} - {e}")

    # 결과 요약
    logger.info("\n" + "="*60)
    logger.info(f"📊 백업 완료")
    logger.info(f"   총: {total_files} 파일")
    logger.info(f"   성공: {success_count}/{total_files}")
    logger.info(f"   버킷: gs://{bucket_name}/ml_rec/")
    logger.info("="*60)

    return success_count == total_files


def main():
    parser = argparse.ArgumentParser(
        description='ML Rec 대용량 파일을 GCS에 백업합니다',
        epilog='예: python backup_ml_rec_to_gcs.py models'
    )
    parser.add_argument(
        'category',
        nargs='?',
        default=None,
        help='백업 카테고리 (models, candidates, dataset, 기본값: 전부)'
    )

    args = parser.parse_args()

    # 설정 로드
    config = load_config()
    if not config:
        sys.exit(1)

    logger.info("="*60)
    logger.info("🚀 ML Rec → GCS 백업 시작")
    logger.info("="*60)

    # 백업 실행
    success = backup_ml_rec(config, args.category)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
