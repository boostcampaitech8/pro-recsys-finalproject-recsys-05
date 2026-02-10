import argparse
import json
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


def _detect_vector_columns(df: pd.DataFrame) -> List[str]:
    lowered = {c.lower(): c for c in df.columns}
    for key in ("vector", "embedding", "embeddings", "vec"):
        if key in lowered:
            return [lowered[key]]

    non_appid_cols = [c for c in df.columns if c.lower() != "appid"]
    if len(non_appid_cols) == 1:
        return non_appid_cols

    return non_appid_cols


def _normalize_appid(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_to_vector(row: pd.Series, vector_cols: List[str]) -> Optional[List[float]]:
    if len(vector_cols) == 1:
        val = row[vector_cols[0]]
        if isinstance(val, list):
            return val
        if hasattr(val, "tolist"):
            return val.tolist()
    try:
        return row[vector_cols].tolist()
    except Exception:
        return None


def build_vector_map(df: pd.DataFrame) -> dict:
    if "appid" not in [c.lower() for c in df.columns]:
        raise ValueError("Parquet 파일에 appid 컬럼이 필요합니다.")

    appid_col = next(c for c in df.columns if c.lower() == "appid")
    vector_cols = _detect_vector_columns(df)

    vector_map = {}
    for _, row in df.iterrows():
        appid = _normalize_appid(row[appid_col])
        if appid is None:
            continue
        vector = _row_to_vector(row, vector_cols)
        if vector is None:
            continue
        vector_map[appid] = vector

    return vector_map


def merge_vectors(jsonl_path: Path, parquet_path: Path, output_path: Path) -> None:
    df = pd.read_parquet(parquet_path)
    vector_map = build_vector_map(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("r", encoding="utf-8") as fin, output_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            row = json.loads(line)
            appid = _normalize_appid(row.get("appid"))
            if appid is not None and appid in vector_map:
                row["vector"] = vector_map[appid]
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="JSONL에 appid 기준으로 벡터 병합")
    parser.add_argument(
        "--jsonl",
        default="app/data/games_metadata.jsonl",
        help="입력 JSONL 경로 (기본: app/data/games_metadata.jsonl)",
    )
    parser.add_argument(
        "--parquet",
        default=r"C:\Users\jwlee\Desktop\rag_vectors_BAAI__bge-m3.parquet",
        help="벡터 parquet 경로",
    )
    parser.add_argument(
        "--output",
        default="app/data/games_metadata_with_vector.jsonl",
        help="출력 JSONL 경로",
    )
    args = parser.parse_args()

    merge_vectors(Path(args.jsonl), Path(args.parquet), Path(args.output))


if __name__ == "__main__":
    main()
