import polars as pl
import os

# 파일 경로
PARQUET_PATH = "backend/test/data/hugging_steam_fronkon.parquet"

def check_parquet_columns():
    if not os.path.exists(PARQUET_PATH):
        print(f"File not found: {PARQUET_PATH}")
        return

    print(f"Loading {PARQUET_PATH}...")
    df = pl.read_parquet(PARQUET_PATH)
    
    # Tags 확인
    tags_mean = df['tags'].list.len().mean()
    print(f"1. Tags Column Avg Length: {tags_mean} (If 0.0, it is empty)")
    
    # Categories 확인
    if 'categories' in df.columns:
        cat_mean = df['categories'].list.len().mean()
        print(f"2. Categories Column Avg Length: {cat_mean}")
        print("3. Categories Sample (Top 5):")
        print(df['categories'].head(5))
    else:
        print("Categories column not found.")

if __name__ == "__main__":
    check_parquet_columns()
