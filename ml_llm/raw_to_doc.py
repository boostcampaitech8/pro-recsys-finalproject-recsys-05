import argparse
import json
import sys
from pathlib import Path
from typing import Any

import polars as pl  # pip install polars
from jinja2 import Environment, FileSystemLoader, Template

class ParquetToDocConverter:
    def __init__(self, template_path: Path):
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        # Jinja2 환경 설정
        self.env = Environment(loader=FileSystemLoader(template_path.parent))
        self.template: Template = self.env.get_template(template_path.name)

    def validate_schema(self, df: pl.DataFrame, mapping: dict[str, str], id_col: str) -> None:
        """Polars DataFrame 스키마 검증"""
        exclude_keys = {"_README"}
        filtered_values = [v for k, v in mapping.items() if k not in exclude_keys]
        
        df_cols = set(df.columns)
        # 매핑된 컬럼들 + ID 컬럼이 존재하는지 확인
        required_cols = set(filtered_values) | {id_col}
        
        missing = required_cols - df_cols
        if missing:
            raise ValueError(f"Missing columns in Parquet: {missing}")

    def process_and_save(self, 
                         df: pl.DataFrame, 
                         mapping: dict[str, str], 
                         id_col: str, 
                         output_path: Path) -> None:
        """
        Polars DF를 순회하며 렌더링하고, 즉시 JSONL로 저장합니다.
        메모리 효율을 위해 리스트에 담지 않고 스트림으로 씁니다.
        """
        
        print(f"Processing {len(df)} records using Polars...")

        with output_path.open('w', encoding='utf-8') as f:
            # named=True를 사용하면 row가 {'col': val} 형태의 dict로 나옵니다.
            # Polars에서 Python 객체로 변환하는 가장 효율적인 이터레이터 중 하나입니다.
            for row in df.iter_rows(named=True):
                # 1. 템플릿용 컨텍스트 생성
                # row.get()을 사용하여 안전하게 값 추출
                context = {
                    tpl_var: row.get(df_col, "")
                    for tpl_var, df_col in mapping.items()
                }

                try:
                    # 2. 렌더링
                    rendered_text = self.template.render(**context)
                    
                    # 3. 문서 구조 생성 (Standardized Schema)
                    # --id_col이 무엇이든 결과 JSON의 key는 'id'로 통일
                    doc_structure = {
                        "id": row[id_col],         # 식별자
                        "content": rendered_text,  # 템플릿 결과물
                        "metadata": row            # 원본 데이터 전체
                    }
                    
                    # 4. JSONL 쓰기
                    f.write(json.dumps(doc_structure, ensure_ascii=False) + "\n")

                except Exception as e:
                    # 에러 발생 시 stderr로 출력하고 계속 진행
                    print(f"[WARN] Failed to render ID {row.get(id_col)}: {e}", file=sys.stderr)

def main() -> None:
    parser = argparse.ArgumentParser(description="Parquet to RAG Document (Polars & Python 3.10+)")
    parser.add_argument("--input_parquet", type=Path, required=True, help="Input .parquet file path")
    parser.add_argument("--template_path", type=Path, required=True, help="Template .j2 file path")
    parser.add_argument("--output_path", type=Path, required=True, help="Output .jsonl file path")
    parser.add_argument("--mapping_config", type=Path, default=None, help="Mapping config .json path")
    parser.add_argument("--id_col", type=str, default="steam_appid", help="Column name for unique ID")
    parser.add_argument("--reviews_parquet", type=Path, default=None, help="Optional reviews .parquet file path for stats join")

    args = parser.parse_args()
    if args.mapping_config is None:
        args.mapping_config = Path(args.template_path).with_suffix(".json")

    # 1. 설정 로드
    try:
        mapping_data = json.loads(args.mapping_config.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"Error reading mapping config: {e}", file=sys.stderr)
        sys.exit(1)

    converter = ParquetToDocConverter(args.template_path)

    # 2. Polars로 데이터 로드
    print("Loading Parquet with Polars...")
    try:
        # 200k 정도는 메모리에 다 올려도 문제 없으므로 read_parquet 사용
        df = pl.read_parquet(args.input_parquet)
        
        # 2.1 리뷰 데이터 조인 (선택 사항)
        if args.reviews_parquet and args.reviews_parquet.exists():
            print(f"Joining with reviews data from {args.reviews_parquet}...")
            df_rev = pl.read_parquet(args.reviews_parquet)
            
            # stats 컬럼 unnest (appid가 String임을 확인했으므로 조인 가능)
            if "stats" in df_rev.columns:
                df_rev = df_rev.select(["appid", "stats"]).unnest("stats")
            
            # appid 컬럼명 통일 (id_col과 맞춤)
            if "appid" in df_rev.columns and args.id_col != "appid":
                df_rev = df_rev.rename({"appid": args.id_col})
            
            # Join (Left join to keep all games)
            df = df.join(df_rev, on=args.id_col, how="left")
            
    except Exception as e:
        print(f"Error loading parquet: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. 검증
    try:
        converter.validate_schema(df, mapping_data, args.id_col)
    except ValueError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. 변환 및 저장
    print(f"Converting and saving to {args.output_path}...")
    converter.process_and_save(df, mapping_data, args.id_col, args.output_path)
    
    print("Done.")

if __name__ == "__main__":
    main()
