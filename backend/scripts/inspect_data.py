import pandas as pd
import glob
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test", "data")

def inspect():
    # 1. Inspect Parquet
    parquet_path = os.path.join(DATA_DIR, "collected_user_data_concat.parquet")
    if os.path.exists(parquet_path):
        print(f"=== {os.path.basename(parquet_path)} ===")
        df_parquet = pd.read_parquet(parquet_path)
        print(df_parquet.info())
        print(df_parquet.head(2))
        print("-" * 50)
    else:
        print("Parquet file not found")

    # 2. Inspect first JSONL
    jsonl_files = glob.glob(os.path.join(DATA_DIR, "crawled_users_*.jsonl"))
    if jsonl_files:
        first_jsonl = jsonl_files[0]
        print(f"=== {os.path.basename(first_jsonl)} (1 of {len(jsonl_files)}) ===")
        # Read only first few lines to avoid loading gigabytes
        df_jsonl = pd.read_json(first_jsonl, lines=True, chunksize=5)
        for chunk in df_jsonl:
            print(chunk.info())
            print(chunk.head(2))
            break
        print("-" * 50)
    else:
        print("JSONL files not found")

if __name__ == "__main__":
    inspect()
