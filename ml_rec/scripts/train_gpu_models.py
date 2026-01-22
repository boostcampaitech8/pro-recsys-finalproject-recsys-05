"""
GPU 기반 모델 훈련 스크립트 (BPR, LightGCN)

EASE 평가(CPU)와 동시에 실행 가능
- BPR: 모델 기반 협업 필터링 (GPU 사용)
- LightGCN: 그래프 신경망 기반 추천 (GPU 사용)

실행:
    python train_gpu_models.py

백그라운드 실행:
    nohup python train_gpu_models.py > training.log 2>&1 &
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path

# RecBole 임포트
from recbole.quick_start import run_recbole


class ModelTrainer:
    """모델 훈련을 관리하는 클래스"""

    def __init__(self, project_root):
        """
        Args:
            project_root: 프로젝트 루트 경로
        """
        self.project_root = Path(project_root)
        self.configs_dir = self.project_root / 'configs'
        self.results_dir = self.project_root / 'scripts' / 'training_results'
        self.results_dir.mkdir(exist_ok=True)

        # 훈련 결과 저장
        self.training_results = {
            'timestamp': datetime.now().isoformat(),
            'models': {}
        }

    def print_header(self, text):
        """헤더 출력"""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)

    def print_section(self, text):
        """섹션 출력"""
        print(f"\n[{text}]")
        print("-"*70)

    def train_model(self, model_name, config_file):
        """
        개별 모델 훈련

        Args:
            model_name: 모델 이름 (BPR, LightGCN)
            config_file: 설정 파일 경로

        Returns:
            dict: 훈련 결과 (시간, 상태 등)
        """
        result = {
            'model': model_name,
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'config_file': config_file,
            'duration': 0,
            'error': None
        }

        self.print_section(f"모델 훈련 시작: {model_name}")

        config_path = self.configs_dir / config_file

        if not config_path.exists():
            error_msg = f"설정 파일 없음: {config_path}"
            print(f"❌ {error_msg}")
            result['status'] = 'failed'
            result['error'] = error_msg
            return result

        print(f"모델: {model_name}")
        print(f"설정: {config_path}")
        print(f"시작: {result['start_time']}")
        print(f"\n훈련 진행 중... (실시간 로그 아래)")
        print("-"*70)

        start_time = time.time()

        try:
            # RecBole 실행
            # config_file_list에 절대 경로 전달
            run_recbole(model=model_name, config_file_list=[str(config_path)])

            elapsed_time = time.time() - start_time
            result['status'] = 'completed'
            result['duration'] = elapsed_time
            result['end_time'] = datetime.now().isoformat()

            print("\n" + "-"*70)
            print(f"✓ {model_name} 훈련 완료")
            print(f"  소요 시간: {elapsed_time:.2f}초 ({elapsed_time/60:.2f}분)")

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            result['status'] = 'failed'
            result['error'] = error_msg
            result['duration'] = elapsed_time
            result['end_time'] = datetime.now().isoformat()

            print("\n" + "-"*70)
            print(f"❌ {model_name} 훈련 실패")
            print(f"  오류: {error_msg}")
            print(f"  소요 시간: {elapsed_time:.2f}초")

        return result

    def print_gpu_info(self):
        """GPU 정보 출력"""
        self.print_section("GPU 정보")
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("GPU 정보를 불러올 수 없습니다")
        except Exception as e:
            print(f"GPU 정보 조회 실패: {e}")

    def print_system_info(self):
        """시스템 정보 출력"""
        self.print_section("시스템 정보")
        print(f"프로젝트 경로: {self.project_root}")
        print(f"설정 디렉토리: {self.configs_dir}")
        print(f"결과 저장 경로: {self.results_dir}")
        print(f"시작 시간: {self.training_results['timestamp']}")

    def save_results(self):
        """훈련 결과 저장"""
        result_file = self.results_dir / f"training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(result_file, 'w') as f:
            json.dump(self.training_results, f, indent=2)

        print(f"\n✓ 결과 저장: {result_file}")
        return result_file

    def print_summary(self):
        """최종 요약 출력"""
        self.print_header("훈련 완료 요약")

        total_duration = sum(m.get('duration', 0) for m in self.training_results['models'].values())

        for model_name, result in self.training_results['models'].items():
            status = result['status']
            status_icon = '✓' if status == 'completed' else '❌'
            duration = result.get('duration', 0)

            print(f"\n{status_icon} {model_name}")
            print(f"  상태: {status}")
            print(f"  소요 시간: {duration:.2f}초 ({duration/60:.2f}분)")

            if result.get('error'):
                print(f"  오류: {result['error']}")

        print(f"\n총 소요 시간: {total_duration:.2f}초 ({total_duration/60:.2f}분)")

        # 상태 요약
        completed = sum(1 for m in self.training_results['models'].values() if m['status'] == 'completed')
        failed = sum(1 for m in self.training_results['models'].values() if m['status'] == 'failed')

        print(f"성공: {completed}/{len(self.training_results['models'])}")
        if failed > 0:
            print(f"실패: {failed}/{len(self.training_results['models'])}")

        print("\n" + "="*70)

    def run(self):
        """전체 훈련 프로세스 실행"""
        self.print_header("GPU 기반 모델 훈련 (BPR, LightGCN)")

        # 시스템 정보 출력
        self.print_system_info()
        self.print_gpu_info()

        # 훈련할 모델 목록
        models = [
            ('BPR', 'recbole_config_bpr.yaml'),
            ('LightGCN', 'recbole_config_lightgcn.yaml')
        ]

        print("\n훈련할 모델:")
        for i, (model_name, config_file) in enumerate(models, 1):
            print(f"  {i}. {model_name} (설정: {config_file})")

        input("\nEnter 키를 눌러 훈련 시작: ")

        # 각 모델 훈련
        for model_name, config_file in models:
            result = self.train_model(model_name, config_file)
            self.training_results['models'][model_name] = result

            # 모델 간 간격
            if model_name != models[-1][0]:
                print("\n대기 중... (다음 모델 준비)")
                time.sleep(2)

        # 결과 저장 및 출력
        self.print_summary()
        self.save_results()

        print("\n훈련 스크립트를 종료합니다.")


def main():
    """메인 함수"""
    try:
        # 프로젝트 루트 경로 설정
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

        # 훈련 실행
        trainer = ModelTrainer(project_root)
        trainer.run()

    except KeyboardInterrupt:
        print("\n\n훈련이 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
