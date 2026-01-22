"""
학습된 EASE 모델을 로드하여 전체(Full) 모드로 평가 지표를 재계산하는 스크립트

[YAML vs Python 코드 설정의 우선순위]

1. YAML 설정 (recbole_config_ease.yaml)
   - mode: uni100 (정답 1개 + 무작위 오답 100개)
   - valid_sample_rate: 0.1 (검증 데이터 10% 샘플링)

2. Python 코드에서 덮어쓰기
   - mode: 'full' ← uni100을 완전히 무시
   - valid_sample_rate: 1.0 ← 0.1을 무시하고 모든 데이터 사용
   - test_sample_rate: 1.0 ← 모든 테스트 데이터 사용

[결과]
Python 코드의 설정이 YAML을 완전히 덮어쓰므로,
실제로는 YAML의 설정을 무시하고 Full 모드로 평가합니다.

[평가 모드 비교]

### uni100 모드 (기존 학습)
- 정답 1개 + 무작위 오답 100개만 비교
- 속도: 매우 빠름 (약 55분)
- 정확도: 근사값 (전체 미상호작용을 고려하지 않음)
- 사용 샘플: 10% (valid_sample_rate=0.1)

### Full 모드 (이 스크립트)
- 모든 미상호작용 아이템 고려
- 속도: 매우 느림 (약 2-4시간 예상)
- 정확도: 완전히 정확한 평가 지표
- 사용 샘플: 100% (valid_sample_rate=1.0)
"""

import torch
import pandas as pd
import numpy as np
from recbole.config import Config
from recbole.data import create_dataset, data_preparation
from recbole.utils import init_logger, get_model, init_seed, get_trainer
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_model_and_data(model_file, config_file_list):
    """
    학습된 모델과 데이터셋을 로드합니다.

    Args:
        model_file: 학습된 모델 파일 경로 (.pth)
        config_file_list: 설정 파일 리스트

    Returns:
        model: 로드된 모델
        dataset: 데이터셋
        config: 설정 객체
    """
    print("\n" + "="*70)
    print("모델 및 데이터 로드")
    print("="*70)

    # 설정 로드
    config = Config(model='EASE', config_file_list=config_file_list)
    init_seed(config['seed'], config['reproducibility'])

    # 로거 초기화
    init_logger(config)

    # 데이터셋 로드
    print(f"\n[1] 데이터셋 로드 중...")
    dataset = create_dataset(config)
    print(f"    ✓ 데이터셋: {config['dataset']}")
    print(f"    ✓ 사용자 수: {dataset.user_num}")
    print(f"    ✓ 아이템 수: {dataset.item_num}")
    print(f"    ✓ 상호작용 수: {len(dataset)}")

    # 모델 초기화
    print(f"\n[2] 모델 로드 중...")
    model = get_model(config['model'])(config, dataset).to(config['device'])
    print(f"    ✓ 모델 생성 완료")

    # 학습된 파라미터 로드
    print(f"\n[3] 학습된 가중치 로드 중... ({model_file})")
    checkpoint = torch.load(model_file, map_location=config['device'])
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()
    print(f"    ✓ 모델 로드 완료")

    return model, dataset, config


def evaluate_model_full(model, dataset, config):
    """
    전체(Full) 모드로 모델을 평가합니다.

    uni100 모드가 아닌 전체 미상호작용 아이템을 고려하여 평가합니다.

    Args:
        model: 학습된 모델
        dataset: 데이터셋
        config: 설정 객체

    Returns:
        results: 평가 결과 딕셔너리
    """
    print("\n" + "="*70)
    print("모델 평가 (Full 모드)")
    print("="*70)

    # 데이터 분할 (train/valid/test)
    print(f"\n[1] 데이터 분할 중...")
    train_data, valid_data, test_data = data_preparation(config, dataset)
    print(f"    ✓ Train: {len(train_data)}")
    print(f"    ✓ Valid: {len(valid_data)}")
    print(f"    ✓ Test: {len(test_data)}")

    # 평가 설정
    print(f"\n[2] 평가 설정 중...")

    # YAML에서 읽은 기존 설정 출력 (무시될 것들)
    eval_mode = config['eval_args']['mode'] if 'mode' in config['eval_args'] else 'unknown'
    v_rate = config['valid_sample_rate'] if 'valid_sample_rate' in config else 1.0
    print(f"    이전 설정 (YAML):")
    print(f"      - mode: {eval_mode}")
    print(f"      - valid_sample_rate: {v_rate}")

    # 평가 옵션 (Full 모드로 완전히 변경)
    eval_args = {
        'mode': 'full',  # 모든 미상호작용 아이템 고려 (uni100 무시)
        'order': 'RO',   # Random Order (무작위 순서)
    }

    # YAML 설정 완전히 덮어쓰기
    config['eval_args'] = eval_args
    config['topk'] = [10, 20]
    config['metrics'] = ['Recall', 'NDCG', 'MRR', 'Hit', 'Precision']
    config['valid_sample_rate'] = 1.0  # YAML의 0.1을 무시하고 모든 데이터 사용
    config['test_sample_rate'] = 1.0   # 모든 테스트 데이터 사용

    # Trainer 생성 (평가용)
    trainer_class = get_trainer(config['MODEL_TYPE'], config['model'])
    trainer = trainer_class(config, model)

    new_valid_rate = config['valid_sample_rate'] if 'valid_sample_rate' in config else 1.0
    new_test_rate = config['test_sample_rate'] if 'test_sample_rate' in config else 1.0

    print(f"\n    새로운 설정 (Full 평가):")
    print(f"      - mode: {config['eval_args']['mode']}")
    print(f"      - valid_sample_rate: {new_valid_rate}")
    print(f"      - test_sample_rate: {new_test_rate}")
    print(f"\n    ✓ 평가 설정 완료")
    print(f"    ✓ 모드: Full (모든 미상호작용 고려)")
    print(f"    ✓ Top-K: {config['topk']}")
    print(f"    ✓ 메트릭: {config['metrics']}")

    # 검증 세트에 대한 평가
    print(f"\n[3] 검증(Valid) 세트 평가 중...")
    print(f"    (처리 중... 시간이 소요될 수 있습니다)")

    with torch.no_grad():
        model.eval()
        valid_result = trainer.evaluate(valid_data, load_best_model=False, show_progress=False)
    print(f"    ✓ 검증 평가 완료")

    # 테스트 세트에 대한 평가
    print(f"\n[4] 테스트(Test) 세트 평가 중...")
    print(f"    (처리 중... 시간이 소요될 수 있습니다)")

    with torch.no_grad():
        test_result = trainer.evaluate(test_data, load_best_model=False, show_progress=False)
    print(f"    ✓ 테스트 평가 완료")

    return {
        'valid': valid_result,
        'test': test_result,
        'config': config
    }


def print_evaluation_results(results):
    """
    평가 결과를 보기 좋게 출력합니다.

    Args:
        results: 평가 결과 딕셔너리
    """
    print("\n" + "="*70)
    print("📊 평가 결과")
    print("="*70)

    # 검증 세트 결과
    print("\n[검증(Valid) 세트 결과]")
    print("-" * 70)
    valid_result = results['valid']

    for metric_name, metric_value in sorted(valid_result.items()):
        if isinstance(metric_value, (int, float)):
            print(f"  {metric_name:20s}: {metric_value:.4f}")

    # 테스트 세트 결과
    print("\n[테스트(Test) 세트 결과]")
    print("-" * 70)
    test_result = results['test']

    for metric_name, metric_value in sorted(test_result.items()):
        if isinstance(metric_value, (int, float)):
            print(f"  {metric_name:20s}: {metric_value:.4f}")

    # 주요 메트릭 강조
    print("\n" + "="*70)
    print("⭐ 주요 메트릭 (NDCG@10, Recall@10)")
    print("="*70)

    print(f"\n검증(Valid) 세트:")
    for key in ['ndcg@10', 'recall@10', 'mrr@10', 'hit@10']:
        val = valid_result.get(key, 'N/A')
        val_str = f"{val:.4f}" if isinstance(val, (int, float)) else str(val)
        print(f"  • {key.upper():12s}: {val_str}")

    print(f"\n테스트(Test) 세트:")
    for key in ['ndcg@10', 'recall@10', 'mrr@10', 'hit@10']:
        val = test_result.get(key, 'N/A')
        val_str = f"{val:.4f}" if isinstance(val, (int, float)) else str(val)
        print(f"  • {key.upper():12s}: {val_str}")


def save_evaluation_results(results, output_file):
    """
    평가 결과를 JSON/CSV 파일로 저장합니다.

    Args:
        results: 평가 결과 딕셔너리
        output_file: 출력 파일 경로
    """
    import json

    print("\n" + "="*70)
    print("결과 저장")
    print("="*70)

    # JSON으로 저장 (더 자세한 정보)
    output_json = output_file.replace('.csv', '_results.json')
    results_dict = {
        'timestamp': datetime.now().isoformat(),
        'valid': results['valid'],
        'test': results['test']
    }

    with open(output_json, 'w') as f:
        json.dump(results_dict, f, indent=2)

    print(f"\n✓ 결과 저장 완료")
    print(f"  • JSON: {output_json}")

    # CSV로도 저장 (비교하기 좋음)
    output_csv = output_file.replace('.csv', '_results.csv')

    # 검증과 테스트 결과를 나란히 비교
    rows = []
    all_metrics = set(list(results['valid'].keys()) + list(results['test'].keys()))

    for metric in sorted(all_metrics):
        if isinstance(results['valid'].get(metric), (int, float)):
            rows.append({
                'Metric': metric,
                'Valid': results['valid'].get(metric, 'N/A'),
                'Test': results['test'].get(metric, 'N/A')
            })

    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
    print(f"  • CSV: {output_csv}")


def main():
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "EASE 모델 Full 모드 평가" + " "*29 + "║")
    print("╚" + "="*68 + "╝")

    MODEL_FILE = '../saved/EASE-Jan-21-2026_05-18-10.pth'
    CONFIG_FILE = '../../configs/recbole_config_ease.yaml'
    OUTPUT_FILE = 'saved/ease_evaluation_full.csv'

    # 1. 모델 및 데이터 로드
    model, dataset, config = load_model_and_data(
        MODEL_FILE,
        config_file_list=[CONFIG_FILE]
    )

    # 2. 평가 실행
    results = evaluate_model_full(model, dataset, config)

    # 3. 결과 출력
    print_evaluation_results(results)

    # 4. 결과 저장
    save_evaluation_results(results, OUTPUT_FILE)

    print("\n" + "="*70)
    print("✓ 모든 작업 완료!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
