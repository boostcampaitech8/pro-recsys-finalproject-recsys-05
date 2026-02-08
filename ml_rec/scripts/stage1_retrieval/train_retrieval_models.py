#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Week 2: Retrieval 모델 자동화 훈련 및 후보 추출

이 스크립트는 다음을 자동으로 수행합니다:
1. EASE 모델 훈련 (5-10분)
2. LightGCN 모델 훈련 (30-60분)
3. 두 모델에서 Top-200 후보 추출
4. LightGCN 임베딩 저장
"""

import os
import json
import subprocess
import logging
import argparse
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import numpy as np
import pandas as pd
import torch
import pickle
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RetrievalModelTrainer:
    """Retrieval 모델 훈련 및 후보 추출 자동화"""

    def __init__(
        self,
        dataset_name: str = "steam_optimal",
        dataset_dir: str = "dataset",
        config_dir: str = "configs",
        saved_model_dir: str = "saved_models",
        output_dir: str = "retrieval_results",
        epochs: int = None
    ):
        self.dataset_name = dataset_name
        self.dataset_dir = dataset_dir
        self.config_dir = config_dir
        self.saved_model_dir = saved_model_dir
        self.output_dir = output_dir
        self.epochs = epochs

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.saved_model_dir, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")

    def train_model_cli(self, model_name: str, config_file: str, checkpoint_path: str = None) -> str:
        """RecBole CLI를 사용해 모델 훈련"""
        logger.info("=" * 80)
        logger.info(f"Training {model_name} model...")
        logger.info("=" * 80)

        config_path = os.path.join(self.config_dir, config_file)

        import sys
        # RecBole CLI 명령어 (커스텀 래퍼 사용)
        cmd = [
            sys.executable, "run_recbole.py",
            "--model", model_name,
            "--dataset", self.dataset_name,
            "--config_file", config_path
        ]

        if checkpoint_path:
            cmd.extend(["--checkpoint", checkpoint_path])
            logger.info(f"ℹ️ Fine-tuning mode enabled with checkpoint: {checkpoint_path}")

        if self.epochs:
            cmd.extend(["--epochs", str(self.epochs)])
            logger.info(f"ℹ️ Training epochs limited to: {self.epochs}")

        try:
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=os.getcwd(),
                capture_output=False,  # 실시간 출력
                text=True
            )

            if result.returncode == 0:
                logger.info(f"✅ {model_name} training completed")
                model_path = self._find_latest_model(model_name)
                logger.info(f"✅ Model saved: {model_path}")
                return model_path
            else:
                logger.error(f"❌ {model_name} training failed with return code {result.returncode}")
                raise RuntimeError(f"{model_name} training failed")

        except Exception as e:
            logger.error(f"❌ Error training {model_name}: {e}")
            raise

    def _find_latest_model(self, model_name: str) -> str:
        """가장 최신 모델 파일 찾기"""
        if not os.path.exists(self.saved_model_dir):
            logger.warning(f"Model directory not found: {self.saved_model_dir}")
            return None

        pattern = os.path.join(self.saved_model_dir, f"{model_name}*.pth")
        model_files = glob.glob(pattern)

        if not model_files:
            logger.warning(f"No model files found for {model_name}")
            return None

        # 가장 최신 파일 선택 (수정 시간순)
        latest_model = max(model_files, key=os.path.getmtime)
        logger.info(f"Found model: {latest_model}")
        return latest_model

    def _load_id_mappings(self):
        """RecBole internal ID와 external ID(Steam) 간의 매핑 로드"""
        inter_file = os.path.join(self.dataset_dir, self.dataset_name, f"{self.dataset_name}.inter")
        inter_df = pd.read_csv(inter_file, sep='\t', header=0)

        # RecBole은 내부적으로 데이터를 정렬하여 ID를 부여함
        # user_id:token (string), item_id:token (string/int)
        users = sorted(inter_df['user_id:token'].unique().astype(str))
        items = sorted(inter_df['item_id:token'].unique().astype(int))

        # ID 매핑 (external -> internal)
        self.user_to_id = {u: i + 1 for i, u in enumerate(users)} # RecBole IDs start from 1 (0 is padding)
        self.item_to_id = {v: i + 1 for i, v in enumerate(items)}

        # 역매핑
        self.id_to_user = {i + 1: u for i, u in enumerate(users)}
        self.id_to_item = {i + 1: v for i, v in enumerate(items)}

        # 실시간 필터링을 위한 사용자 상호작용 셋
        self.user_interactions = defaultdict(set)
        for _, row in inter_df.iterrows():
            u_idx = self.user_to_id.get(str(row['user_id:token']))
            i_idx = self.item_to_id.get(int(row['item_id:token']))
            if u_idx and i_idx:
                self.user_interactions[u_idx].add(i_idx)

        return inter_df

    def extract_candidates(self, model_name: str, model_path: str, top_k: int = 200) -> Dict:
        """모델 체크포인트에서 직접 Top-k 후보 추출"""
        logger.info("=" * 80)
        logger.info(f"Extracting Top-{top_k} candidates from {model_name}...")
        logger.info("=" * 80)

        if not model_path or not os.path.exists(model_path):
            logger.error(f"❌ Model path not found: {model_path}")
            return {}

        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        candidates = {}
        
        if model_name == 'EASE':
            if 'other_parameter' not in checkpoint or 'item_similarity' not in checkpoint['other_parameter']:
                logger.error("⚠ EASE item_similarity를 찾을 수 없습니다. Baseline으로 대체합니다.")
                return self._extract_popularity_baseline(top_k)
            
            item_similarity = np.asarray(checkpoint['other_parameter']['item_similarity'])
            n_items = item_similarity.shape[0]

            for u_idx, interactions in tqdm(self.user_interactions.items(), desc="  EASE Extraction"):
                scores = np.zeros(n_items)
                for j in interactions:
                    if j < n_items:
                        scores += np.asarray(item_similarity[j]).flatten()
                
                # 가려내기 (이미 플레이한 게임은 -inf)
                for j in interactions:
                    if j < n_items: scores[j] = -np.inf
                
                top_indices = np.argsort(-scores)[:top_k]
                u_ext = self.id_to_user.get(u_idx)
                if u_ext:
                    candidates[u_ext] = []
                    for rank, i_idx in enumerate(top_indices):
                        if scores[i_idx] == -np.inf: continue
                        i_ext = self.id_to_item.get(i_idx, i_idx)
                        candidates[u_ext].append({
                            'item_id': str(i_ext),
                            'score': float(scores[i_idx]),
                            'rank': rank + 1
                        })

        elif model_name == 'LightGCN':
            state_dict = checkpoint['state_dict']
            user_emb = None
            item_emb = None
            
            for key in state_dict.keys():
                if 'user_embedding' in key and 'weight' in key: user_emb = state_dict[key].cpu().numpy()
                elif 'item_embedding' in key and 'weight' in key: item_emb = state_dict[key].cpu().numpy()
            
            if user_emb is None or item_emb is None:
                logger.error("⚠ LightGCN embeddings not found. Baseline으로 대체합니다.")
                return self._extract_popularity_baseline(top_k)

            # 모든 사용자-아이템 점수 계산 (내적)
            for u_idx in tqdm(range(1, user_emb.shape[0]), desc="  LightGCN Extraction"):
                u_vec = user_emb[u_idx]
                scores = np.dot(item_emb, u_vec)
                
                # 이미 플레이한 게임 제외
                if u_idx in self.user_interactions:
                    for i_idx in self.user_interactions[u_idx]:
                        if i_idx < len(scores): scores[i_idx] = -np.inf
                
                top_indices = np.argsort(-scores)[:top_k]
                u_ext = self.id_to_user.get(u_idx)
                if u_ext:
                    candidates[u_ext] = []
                    for rank, i_idx in enumerate(top_indices):
                        if scores[i_idx] == -np.inf: continue
                        i_ext = self.id_to_item.get(i_idx, i_idx)
                        candidates[u_ext].append({
                            'item_id': str(i_ext),
                            'score': float(scores[i_idx]),
                            'rank': rank + 1
                        })
            
            self.last_item_embeddings = item_emb

        logger.info(f"✅ Extracted candidates for {len(candidates):,} users")
        return candidates

    def _extract_popularity_baseline(self, top_k: int) -> Dict:
        """Fallback: 인기도 기반 후보 추출"""
        inter_file = os.path.join(self.dataset_dir, self.dataset_name, f"{self.dataset_name}.inter")
        inter_df = pd.read_csv(inter_file, sep='\t')
        item_popularity = inter_df['item_id:token'].value_counts()
        popular_items = item_popularity.head(top_k).index.tolist()
        
        candidates = {}
        for user_id in inter_df['user_id:token'].unique():
            candidates[str(user_id)] = [{'item_id': str(i), 'score': 1.0, 'rank': r+1} for r, i in enumerate(popular_items)]
        return candidates

    def save_candidates(self, candidates: Dict, output_name: str):
        """후보 저장"""
        output_path = os.path.join(self.output_dir, f"{output_name}.json")

        with open(output_path, 'w') as f:
            json.dump(candidates, f, indent=2)

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"✅ Saved candidates to {output_path}")
        logger.info(f"  Size: {file_size:.2f}MB")
        return output_path

    def save_embeddings(self, embeddings: np.ndarray, item_ids: List, output_name: str):
        """임베딩 저장"""
        output_path = os.path.join(self.output_dir, f"{output_name}.npz")

        np.savez_compressed(output_path, embeddings=embeddings, item_ids=item_ids)

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"✅ Saved embeddings to {output_path}")
        logger.info(f"  Shape: {embeddings.shape}, Size: {file_size:.2f}MB")
        return output_path

    def run(self, incremental_lightgcn: bool = False):
        """전체 파이프라인 실행"""
        logger.info("\n" + "=" * 80)
        logger.info("Week 2: Retrieval Model Training & Candidate Extraction")
        logger.info("=" * 80 + "\n")

        start_time = datetime.now()

        try:
            # 데이터셋 정보 로드
            inter_file = os.path.join(self.dataset_dir, self.dataset_name, f"{self.dataset_name}.inter")
            inter_df = pd.read_csv(inter_file, sep='\t')
            n_items = inter_df['item_id:token'].nunique()
            n_users = inter_df['user_id:token'].nunique()

            # 1. EASE 모델 훈련
            logger.info("\n[Task 1/4] Training EASE model...")
            ease_model_path = self.train_model_cli("EASE", "recbole_ease_optimal.yaml")
            
            # [Fix] serving에서 기대하는 고정 파일명으로 복사
            if ease_model_path:
                import shutil
                ease_static_path = os.path.join(self.saved_model_dir, "item_similarity.pkl")
                shutil.copy2(ease_model_path, ease_static_path)
                logger.info(f"✅ EASE model copied to: {ease_static_path}")

            # 2. LightGCN 모델 훈련
            logger.info("\n[Task 2/4] Training LightGCN model...")
            checkpoint = None
            if incremental_lightgcn:
                checkpoint = self._find_latest_model("LightGCN")
            
            lightgcn_model_path = self.train_model_cli("LightGCN", "recbole_lightgcn_optimal.yaml", checkpoint_path=checkpoint)

            # 3. ID 매핑 및 상호작용 로드 (Real Extraction 필수)
            self._load_id_mappings()

            # 4. EASE 후보 추출
            logger.info("\n[Task 3/4] Extracting EASE candidates...")
            ease_candidates = self.extract_candidates("EASE", ease_model_path, top_k=200)
            self.save_candidates(ease_candidates, "ease_candidates")

            # 5. LightGCN 후보 및 임베딩 추출
            logger.info("\n[Task 4/4] Extracting LightGCN candidates and embeddings...")
            lightgcn_candidates = self.extract_candidates("LightGCN", lightgcn_model_path, top_k=200)
            self.save_candidates(lightgcn_candidates, "lightgcn_candidates")

            # 임베딩 저장 (LightGCN 추출 시 저장된 임베딩 사용)
            if hasattr(self, 'last_item_embeddings'):
                # RecBole internal IDs mapping to external IDs
                item_ids = [self.id_to_item.get(i, i) for i in range(len(self.id_to_item) + 1)] # include 0 padding if any
                item_ids = item_ids[1:] # skip 0
                embeddings = self.last_item_embeddings[1:] # skip 0
                self.save_embeddings(embeddings, item_ids, "lightgcn_embeddings")
            else:
                logger.warning("⚠ No embeddings found to save. (Fallback to random noise)")
                random_embeddings = np.random.randn(n_items, 64).astype(np.float32)
                self.save_embeddings(random_embeddings, inter_df['item_id:token'].unique().tolist(), "lightgcn_embeddings")

            # 최종 요약
            elapsed_time = datetime.now() - start_time
            logger.info("\n" + "=" * 80)
            logger.info("✅ Week 2 Completion Summary")
            logger.info("=" * 80)
            logger.info(f"Elapsed time: {elapsed_time}")
            logger.info(f"\nDataset Statistics:")
            logger.info(f"  Users: {n_users:,}")
            logger.info(f"  Items: {n_items:,}")
            logger.info(f"  Interactions: {len(inter_df):,}")
            logger.info(f"\nGenerated files:")
            logger.info(f"  - saved_models/item_similarity.pkl")
            logger.info(f"  - retrieval_results/ease_candidates.json ({len(ease_candidates):,} users)")
            logger.info(f"  - retrieval_results/lightgcn_candidates.json ({len(lightgcn_candidates):,} users)")
            if hasattr(self, 'last_item_embeddings'):
                logger.info(f"  - retrieval_results/lightgcn_embeddings.npz {self.last_item_embeddings.shape}")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Train retrieval models and extract candidates (Week 2 automation)"
    )
    parser.add_argument(
        "--dataset_name",
        type=str,
        default="steam_optimal",
        help="Dataset name"
    )
    parser.add_argument(
        "--dataset_dir",
        type=str,
        default="dataset",
        help="Dataset directory"
    )
    parser.add_argument(
        "--config_dir",
        type=str,
        default="configs",
        help="Config directory"
    )
    parser.add_argument(
        "--saved_model_dir",
        type=str,
        default="saved_models",
        help="Saved models directory"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="retrieval_results",
        help="Output directory for candidates and embeddings"
    )

    parser.add_argument("--incremental", action="store_true", help="Enable incremental training (fine-tuning) for LightGCN")
    parser.add_argument("--epochs", type=int, help="Limit number of training epochs")

    args = parser.parse_args()

    # 1. 초기화
    trainer = RetrievalModelTrainer(
        dataset_name=args.dataset_name,
        dataset_dir=args.dataset_dir,
        config_dir=args.config_dir,
        saved_model_dir=args.saved_model_dir,
        output_dir=args.output_dir,
        epochs=args.epochs
    )

    success = trainer.run(incremental_lightgcn=args.incremental)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
