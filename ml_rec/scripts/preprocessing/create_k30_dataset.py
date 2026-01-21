"""
K-core 30 + User Activity + Item Popularity 필터링 데이터셋 생성
RecBole 형식으로 저장
"""

import pandas as pd
import os

def combined_filter(df, k=30, min_user=20, max_user=500,
                   min_item=20, max_item=1000, iterations=5):
    """K-core + User Activity + Item Popularity 결합 필터링"""
    filtered_df = df.copy()

    for iteration in range(iterations):
        prev_len = len(filtered_df)

        # User Activity Range
        user_counts = filtered_df.groupby('user_id:token').size()
        valid_users = user_counts[
            (user_counts >= min_user) & (user_counts <= max_user)
        ]
        filtered_df = filtered_df[filtered_df['user_id:token'].isin(valid_users.index)]

        # Item Popularity Range
        item_counts = filtered_df.groupby('item_id:token').size()
        valid_items = item_counts[
            (item_counts >= min_item) & (item_counts <= max_item)
        ]
        filtered_df = filtered_df[filtered_df['item_id:token'].isin(valid_items.index)]

        # K-core
        user_degrees = filtered_df.groupby('user_id:token').size()
        valid_users_kcore = user_degrees[user_degrees >= k]

        item_degrees = filtered_df.groupby('item_id:token').size()
        valid_items_kcore = item_degrees[item_degrees >= k]

        filtered_df = filtered_df[
            (filtered_df['user_id:token'].isin(valid_users_kcore.index)) &
            (filtered_df['item_id:token'].isin(valid_items_kcore.index))
        ]

        print(f"  Iteration {iteration + 1}: {len(filtered_df):,} interactions")

        if len(filtered_df) == prev_len or len(filtered_df) == 0:
            print(f"  ✓ Converged\n")
            break

    return filtered_df


def main():
    print("\n" + "="*70)
    print("🚀 Creating K30 + Activity Filtered Dataset")
    print("="*70 + "\n")

    # Load original filtered data
    print("📂 Loading base data...")
    df = pd.read_csv(
        '/data/ephemeral/home/steam_project/dataset/steam_filtered_kcore20/steam_filtered_kcore20.inter',
        delimiter=','
    )
    print(f"✓ Loaded: {len(df):,} interactions")
    print(f"  Users: {df['user_id:token'].nunique():,}")
    print(f"  Items: {df['item_id:token'].nunique():,}\n")

    # Apply K30 + Activity filtering
    print("🔧 Applying K30 + User (20-500) + Item (20-1000) filtering...")
    filtered_df = combined_filter(
        df,
        k=30,
        min_user=20,
        max_user=500,
        min_item=20,
        max_item=1000,
        iterations=5
    )

    # Statistics
    n_users = filtered_df['user_id:token'].nunique()
    n_items = filtered_df['item_id:token'].nunique()
    n_interactions = len(filtered_df)

    bytes_per_float = 4
    memory_gb = (n_users * n_items * bytes_per_float) / (1024 ** 3)

    print("="*70)
    print("📊 Filtered Dataset Statistics")
    print("="*70)
    print(f"Users:        {n_users:>10,}")
    print(f"Items:        {n_items:>10,}")
    print(f"Interactions: {n_interactions:>10,}")
    print(f"Memory (GB):  {memory_gb:>10.2f}")
    print(f"Reduction:    {((1 - n_interactions / len(df)) * 100):>10.2f}%\n")

    # Create RecBole dataset directory
    dataset_name = 'steam_filtered_k30_activity'
    output_dir = f'/data/ephemeral/home/steam_project/dataset/{dataset_name}'
    output_file = f'{output_dir}/{dataset_name}.inter'

    os.makedirs(output_dir, exist_ok=True)

    # Save with header
    print(f"💾 Saving to: {output_file}")
    filtered_df.to_csv(output_file, index=False)
    print(f"✓ Saved successfully\n")

    print("="*70)
    print("✅ NEXT STEP: Update RecBole config")
    print("="*70)
    print(f"""
Edit configs/recbole_config_ease.yaml:

  dataset: {dataset_name}

Then run:
  python -m recbole.main --model EASE --config configs/recbole_config_ease.yaml
    """)


if __name__ == '__main__':
    main()
