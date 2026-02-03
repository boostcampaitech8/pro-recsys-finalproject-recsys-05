"""
JSON 후보 파일을 Pickle로 변환하는 스크립트
"""
import json
import pickle
from pathlib import Path
import time

# 경로 설정
candidates_dir = Path('ml_rec/candidates')

files_to_convert = [
    ('ease_candidates.json', 'ease_candidates.pkl'),
    ('lightgcn_candidates.json', 'lightgcn_candidates.pkl'),
]

print("=" * 60)
print("JSON → Pickle 변환 시작")
print("=" * 60)

for json_file, pkl_file in files_to_convert:
    json_path = candidates_dir / json_file
    pkl_path = candidates_dir / pkl_file

    print(f"\n📖 {json_file} 로드 중...")
    start_time = time.time()

    # JSON 로드
    with open(json_path, 'r') as f:
        data = json.load(f)

    json_load_time = time.time() - start_time
    print(f"   ✓ {len(data)} 사용자 로드 완료 ({json_load_time:.1f}초)")

    # Pickle 저장
    print(f"💾 {pkl_file} 저장 중...")
    start_time = time.time()

    with open(pkl_path, 'wb') as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    pkl_save_time = time.time() - start_time
    json_size = json_path.stat().st_size / (1024**3)  # GB
    pkl_size = pkl_path.stat().st_size / (1024**3)    # GB

    print(f"   ✓ 저장 완료 ({pkl_save_time:.1f}초)")
    print(f"   JSON 크기: {json_size:.2f}GB → Pickle: {pkl_size:.2f}GB")

print("\n" + "=" * 60)
print("✅ 변환 완료!")
print("=" * 60)
