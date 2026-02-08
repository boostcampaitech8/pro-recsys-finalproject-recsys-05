import argparse
import sys
from recbole.quick_start import run_recbole
import torch

# [Fix] PyTorch 2.6+에서 torch.load의 기본값이 weights_only=True로 변경되어 
# RecBole의 모델 로딩이 실패하는 문제를 해결하기 위한 몽키패치
original_torch_load = torch.load
def patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return original_torch_load(*args, **kwargs)
torch.load = patched_torch_load

def main():
    parser = argparse.ArgumentParser(description="RecBole Runner Wrapper")
    parser.add_argument("--model", type=str, required=True, help="Model name (e.g., EASE, LightGCN)")
    parser.add_argument("--dataset", type=str, required=True, help="Dataset name")
    parser.add_argument("--config_file", type=str, help="Path to config file")
    parser.add_argument("--checkpoint", type=str, help="Path to checkpoint file (.pth) for fine-tuning")
    
    # RecBole might have other arguments, we pass them as a list if needed, 
    # but run_recbole primarily uses the ones we defined.
    args, extra_args = parser.parse_known_args()
    
    config_dict = {}
    if args.checkpoint:
        # 체크포인트가 있으면 해당 경로를 설정에 추가하여 파인튜닝 모드로 동작하게 함
        config_dict['checkpoint_path'] = args.checkpoint
        print(f"📍 Loading Checkpoint for Fine-tuning: {args.checkpoint}")

    # Parse extra args if any (e.g., --learning_rate=0.01)
    for i in range(0, len(extra_args), 2):
        if extra_args[i].startswith("--") and i+1 < len(extra_args):
            key = extra_args[i][2:]
            val = extra_args[i+1]
            # Try to convert to float/int if possible
            try:
                if '.' in val: val = float(val)
                else: val = int(val)
            except ValueError:
                pass
            config_dict[key] = val

    config_file_list = [args.config_file] if args.config_file else None
    
    print(f"Starting RecBole: Model={args.model}, Dataset={args.dataset}, Config={args.config_file}")
    run_recbole(model=args.model, dataset=args.dataset, config_file_list=config_file_list, config_dict=config_dict)

if __name__ == "__main__":
    main()
