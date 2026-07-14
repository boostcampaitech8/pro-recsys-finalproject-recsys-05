"""
Task 2: DCN v2 모델 학습
Ranking 데이터셋을 받아서 DCN v2 모델 학습

구조:
- Deep Network: (256, 128, 64)
- Cross Network: 3층
- Early Stopping: Patience=5
- 배치 크기: 2048
- 에포크: 20
"""

import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import logging
from pathlib import Path
from sklearn.preprocessing import StandardScaler, LabelEncoder
import random

# 랜덤 시드 고정
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)

# 로깅 설정
log_dir = Path('logs/week3_ranking')
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_dir / 'dcn_v2_training.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DCN_V2(nn.Module):
    """DCN v2 모델: Deep + Cross Network"""

    def __init__(self, input_dim, deep_layers=(256, 128, 64), cross_layers=3, dropout_rate=0.1):
        super(DCN_V2, self).__init__()

        # Deep Network
        deep_modules = []
        prev_dim = input_dim
        for hidden_dim in deep_layers:
            deep_modules.append(nn.Linear(prev_dim, hidden_dim))
            deep_modules.append(nn.BatchNorm1d(hidden_dim))
            deep_modules.append(nn.ReLU())
            deep_modules.append(nn.Dropout(dropout_rate))
            prev_dim = hidden_dim

        self.deep_network = nn.Sequential(*deep_modules)

        # Cross Network
        self.cross_layers = nn.ModuleList()
        for _ in range(cross_layers):
            self.cross_layers.append(nn.Linear(input_dim, input_dim))

        # Final output layer
        self.output_layer = nn.Linear(prev_dim + input_dim, 1)
        self.sigmoid = nn.Sigmoid()

        self.input_dim = input_dim

    def forward(self, x):
        # Deep path
        deep_output = self.deep_network(x)

        # Cross path
        cross_x = x
        for cross_layer in self.cross_layers:
            cross_x = x * cross_layer(cross_x) + cross_x

        # Combine
        combined = torch.cat([deep_output, cross_x], dim=1)
        output = self.output_layer(combined)
        output = self.sigmoid(output)

        return output


class DCNTrainer:
    def __init__(self):
        self.base_path = Path.cwd()
        self.candidates_path = self.base_path / 'candidates'
        self.models_path = self.base_path / 'saved_models'
        self.models_path.mkdir(exist_ok=True)

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Device: {self.device}")

        logger.info("=" * 80)
        logger.info("Task 2: DCN v2 모델 학습 시작")
        logger.info("=" * 80)

    def load_data(self):
        """학습/검증/테스트 데이터 로드"""
        logger.info("\n[Step 1] 데이터 로드 중...")

        with open(self.candidates_path / 'ranking_train.pkl', 'rb') as f:
            train_data = pickle.load(f)
        logger.info(f"✓ 학습 데이터 로드: {len(train_data)}개 샘플")

        with open(self.candidates_path / 'ranking_val.pkl', 'rb') as f:
            val_data = pickle.load(f)
        logger.info(f"✓ 검증 데이터 로드: {len(val_data)}개 샘플")

        with open(self.candidates_path / 'ranking_test.pkl', 'rb') as f:
            test_data = pickle.load(f)
        logger.info(f"✓ 테스트 데이터 로드: {len(test_data)}개 샘플")

        return train_data, val_data, test_data

    def prepare_batch(self, batch):
        """배치 데이터 준비"""
        features_list = []
        labels_list = []

        for sample in batch:
            # 특성 벡터화
            embedding = sample['embedding']
            features = np.concatenate([
                [float(sample['popularity'])],
                [float(sample['avg_playtime'])],
                embedding
            ])
            features_list.append(features)
            labels_list.append(float(sample['label']))

        features = np.array(features_list, dtype=np.float32)
        labels = np.array(labels_list, dtype=np.float32).reshape(-1, 1)

        features = torch.tensor(features, device=self.device)
        labels = torch.tensor(labels, device=self.device)

        return features, labels

    def train_epoch(self, model, train_data, batch_size=2048, optimizer=None, criterion=None):
        """한 에포크 학습"""
        model.train()
        total_loss = 0

        # 배치로 분할
        for i in range(0, len(train_data), batch_size):
            batch = train_data[i:i+batch_size]
            features, labels = self.prepare_batch(batch)

            # Forward pass
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)

            # Backward pass
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(batch)

        return total_loss / len(train_data)

    def evaluate(self, model, val_data, batch_size=2048, criterion=None):
        """모델 평가"""
        model.eval()
        total_loss = 0
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for i in range(0, len(val_data), batch_size):
                batch = val_data[i:i+batch_size]
                features, labels = self.prepare_batch(batch)

                outputs = model(features)
                loss = criterion(outputs, labels)

                total_loss += loss.item() * len(batch)
                all_preds.extend(outputs.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        # AUC 계산 (간단한 버전)
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)

        # Threshold 0.5로 정확도 계산
        accuracy = np.mean((all_preds >= 0.5).astype(int) == all_labels)

        avg_loss = total_loss / len(val_data)
        return avg_loss, accuracy

    def train(self):
        """전체 학습 파이프라인"""
        try:
            # 데이터 로드
            train_data, val_data, test_data = self.load_data()

            # 모델 초기화
            logger.info("\n[Step 2] DCN v2 모델 초기화 중...")
            input_dim = 1 + 1 + 64  # popularity + avg_playtime + embedding(64)
            model = DCN_V2(input_dim, deep_layers=(256, 128, 64), cross_layers=3, dropout_rate=0.1).to(self.device)
            logger.info(f"✓ 모델 초기화: 입력 차원={input_dim}")

            # 옵티마이저 및 손실 함수
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.BCELoss()

            # 학습
            logger.info("\n[Step 3] 모델 학습 중...")
            best_val_loss = float('inf')
            patience = 5
            patience_counter = 0

            for epoch in range(20):
                train_loss = self.train_epoch(model, train_data, batch_size=2048, optimizer=optimizer, criterion=criterion)
                val_loss, val_acc = self.evaluate(model, val_data, batch_size=2048, criterion=criterion)

                logger.info(f"Epoch {epoch+1:2d}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}, val_acc={val_acc:.4f}")

                # Early Stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    torch.save({
                        'model_state_dict': model.state_dict(),
                        'epoch': epoch,
                        'val_loss': val_loss,
                        'val_acc': val_acc
                    }, self.models_path / 'dcn_v2_steam.pth')
                    logger.info(f"  → Best model saved (val_loss={val_loss:.4f})")
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        logger.info(f"  → Early stopping at epoch {epoch+1} (patience={patience})")
                        break

            # 테스트 성능 평가
            logger.info("\n[Step 4] 테스트 성능 평가 중...")
            checkpoint = torch.load(self.models_path / 'dcn_v2_steam.pth', map_location=self.device, weights_only=False)
            model.load_state_dict(checkpoint['model_state_dict'])
            test_loss, test_acc = self.evaluate(model, test_data, batch_size=2048, criterion=criterion)

            logger.info(f"✓ 테스트 결과:")
            logger.info(f"  - Test Loss: {test_loss:.4f}")
            logger.info(f"  - Test Accuracy: {test_acc:.4f}")

            logger.info("\n" + "=" * 80)
            logger.info("✅ Task 2 완료!")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"\n❌ 오류 발생: {e}", exc_info=True)
            raise


if __name__ == '__main__':
    trainer = DCNTrainer()
    trainer.train()
