import pandas as pd
import glob
import os
import sys

# 경로 설정
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # backend/
DATA_DIR = os.path.join(BACKEND_DIR, "test", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "merged_user_data.parquet")

def flatten_games_data(df, source_name="Data"):
    """
    DataFrame 내의 'games' 컬럼(List of Dict)을 펼쳐서 User-Item Interaction 형태로 변환합니다.
    Ref: matches steamid, games -> user_id, game_id, playtime_forever
    """
    print(f"   Using flatten logic for {source_name}...")
    
    # Check columns
    if 'steamid' not in df.columns or 'games' not in df.columns:
        print(f"   ⚠️ Skipping flatten: 'steamid' or 'games' missing in {df.columns.tolist()}")
        return pd.DataFrame()

    # 필요한 컬럼만 선택
    df = df[['steamid', 'games']]
    
    # 1. Explode
    df_exploded = df.explode('games')
    df_exploded = df_exploded.dropna(subset=['games'])
    
    # 2. Extract dict values
    # List comprehension for speed
    games_list = df_exploded['games'].tolist()
    appids = [g.get('appid') if isinstance(g, dict) else None for g in games_list]
    playtimes = [g.get('playtime_forever') if isinstance(g, dict) else None for g in games_list]
    
    df_exploded['game_id'] = appids
    df_exploded['playtime'] = playtimes
    
    # 3. Rename & Select
    df_result = df_exploded.rename(columns={'steamid': 'user_id'})
    df_result = df_result[['user_id', 'game_id', 'playtime']]
    
    # 4. Type conversion (optimize)
    df_result['user_id'] = df_result['user_id'].astype(str)
    # game_id, playtime -> numeric
    df_result['game_id'] = pd.to_numeric(df_result['game_id'], errors='coerce')
    df_result['playtime'] = pd.to_numeric(df_result['playtime'], errors='coerce')
    
    df_result = df_result.dropna(subset=['game_id', 'playtime'])
    df_result['game_id'] = df_result['game_id'].astype(int)
    
    print(f"   -> {source_name} flattened: {len(df_result):,} rows")
    return df_result

def process_data():
    print("🚀 데이터 병합 작업을 시작합니다... (Flattening Both)")

    # 1. Collected Data 로드
    collected_path = os.path.join(DATA_DIR, "collected_user_data_concat.parquet")
    df_final_list = []

    if os.path.exists(collected_path):
        print(f"📖 1. Collected Data 읽는 중... ({collected_path})")
        df_collected = pd.read_parquet(collected_path)
        print(f"   -> Raw Rows: {len(df_collected):,}")
        
        # Flatten
        df_collected_flat = flatten_games_data(df_collected, "Collected Data")
        if not df_collected_flat.empty:
            df_final_list.append(df_collected_flat)
    else:
        print(f"❌ collected data not found: {collected_path}")

    # 2. Crawled Data 로드
    jsonl_pattern = os.path.join(DATA_DIR, "crawled_users_*.jsonl")
    jsonl_files = glob.glob(jsonl_pattern)
    
    if jsonl_files:
        print(f"📖 2. Crawled Data 읽는 중... (Files: {len(jsonl_files)})")
        for f in jsonl_files:
            print(f"   -> Processing {os.path.basename(f)}...")
            try:
                df_chunk = pd.read_json(f, lines=True)
                df_crawled_flat = flatten_games_data(df_chunk, f"Crawled({os.path.basename(f)})")
                if not df_crawled_flat.empty:
                    df_final_list.append(df_crawled_flat)
            except Exception as e:
                print(f"      ❌ Error processing {f}: {e}")
    else:
        print("❌ Crawled data files not found.")

    # 3. Merge & Save
    if df_final_list:
        print("🔄 3. 병합 중...")
        merged_df = pd.concat(df_final_list, ignore_index=True)
        print(f"   -> Total Rows: {len(merged_df):,}")
        
        print("🧹 4. 중복 제거 중...")
        # user_id, game_id 기준 중복 제거 (playtime은 최신것? 혹은 sum? 보통 overwrite)
        # 여기서는 단순히 drop_duplicates (first keep)
        merged_df = merged_df.drop_duplicates(subset=['user_id', 'game_id'])
        print(f"   -> Final Rows: {len(merged_df):,}")
        
        print(f"💾 5. 저장 중... ({OUTPUT_FILE})")
        merged_df.to_parquet(OUTPUT_FILE, index=False)
        print("✅ 완료!")
    else:
        print("⚠️ 병합할 데이터가 없습니다.")

if __name__ == "__main__":
    process_data()
