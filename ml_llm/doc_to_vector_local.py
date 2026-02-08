import argparse
import sys
import time
from pathlib import Path
import numpy as np

import polars as pl
import torch
from sentence_transformers import SentenceTransformer

# -----------------------------------------------------------------------------
# 1. Embedding Engine Class (Strategy Pattern)
# -----------------------------------------------------------------------------
class EmbeddingEngine:
    """
    로컬 임베딩 모델을 관리하는 래퍼 클래스입니다.
    Python 3.13+ 문법을 준수하며, 하드웨어 가속(CUDA, MPS)을 지원합니다.
    """
    def __init__(self, model_id: str, device: str = "auto", use_fp16: bool = True):
        self.model_id = model_id
        self.device = self._detect_device(device)
        self.use_fp16 = use_fp16
        
        print(f"🚀 [Init] 모델 로드 중: {model_id}")
        print(f"🖥️ [Device] 사용 장치: {self.device.upper()}")
        
        # trust_remote_code=True: 일부 커스텀 아키텍처 모델(Alibaba, BAAI 등) 로드 허용
        self.model = SentenceTransformer(model_id, device=self.device, trust_remote_code=True)
        
        # FP16 적용: GPU/MPS 사용 시 메모리 절약 및 속도 향상
        if self.use_fp16 and self.device != "cpu":
            try:
                self.model.half()
                print("⚡ [Optim] FP16(Half Precision) 모드 활성화됨")
            except Exception as e:
                print(f"⚠️ [Warn] FP16 설정 실패 (무시하고 FP32로 진행): {e}")

    def _detect_device(self, request: str) -> str:
        if request != "auto":
            return request
        
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"  # Apple Silicon (M1/M2/M3)
        return "cpu"

    # Modern Typing: List[str] -> list[str]
    def embed(self, texts: list[str], batch_size: int) -> np.ndarray:
        """
        텍스트 리스트를 받아 벡터 리스트를 반환합니다.
        normalize_embeddings=True: RAG 검색 품질(코사인 유사도)을 위해 필수
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True, 
            convert_to_numpy=True,    
            convert_to_tensor=False
        )
        return embeddings

# -----------------------------------------------------------------------------
# 2. Main Process Logic
# -----------------------------------------------------------------------------
# Modern Typing: Optional[int] -> int | None
import hashlib

def calculate_hash(text: str) -> str:
    """텍스트의 SHA-256 해시값을 계산합니다."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def run_embedding_pipeline(
    input_path: Path,
    output_dir: Path,
    model_id: str,
    batch_size: int,
    limit: int | None = None,
    incremental: bool = False
):
    start_time = time.time()

    # 출력 경로 설정
    safe_model_name = model_id.replace("/", "__")
    output_filename = f"vectors_{safe_model_name}.parquet"
    output_path = output_dir / output_filename
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 데이터 로드 (Lazy -> Collect)
    print(f"📂 [Input] 데이터 로드 중: {input_path}")
    if not input_path.exists():
        print(f"❌ [Error] 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    # JSONL 로드 (Polars LazyFrame)
    q = pl.scan_ndjson(input_path)

    if limit:
        print(f"⚠️ [Limit] 테스트를 위해 상위 {limit}개 데이터만 처리합니다.")
        q = q.limit(limit)

    df_src = q.select(["id", "content"]).collect()
    if df_src.is_empty():
        print("[ERROR] [Error] 소스 데이터가 비어있습니다.")
        sys.exit(1)

    # 2. 해시 계산
    print("[INFO] [Hash] 콘텐츠 해시 생성 중...")
    df_src = df_src.with_columns(
        pl.col("content").map_elements(calculate_hash, return_dtype=pl.String).alias("content_hash")
    )

    # 3. 변경 감지 (Incremental Logic)
    existing_df = None
    df_to_embed = df_src

    if incremental and output_path.exists():
        print(f"[INFO] [Incremental] 기존 데이터 비교 중: {output_path.name}")
        existing_df = pl.read_parquet(output_path)

        # ID와 Hash가 모두 일치하는 항목 제외
        # existing_df 스키마 확인 (content_hash가 없을 수 있으므로 예외 처리)
        if "content_hash" in existing_df.columns:
            # 기존에 존재하며 해시가 일치하는 ID 목록
            unchanged_ids = df_src.join(
                existing_df.select(["app_id", "content_hash"]),
                left_on="id", right_on="app_id", how="inner"
            ).filter(pl.col("content_hash") == pl.col("content_hash_right")).select("id")

            df_to_embed = df_src.filter(~pl.col("id").is_in(unchanged_ids["id"]))
            print(f"[SKIP] [Skip] {len(unchanged_ids):,}개 게임의 내용이 동일하여 임베딩을 생략합니다.")
        else:
            print("[WARN] [Warn] 기존 파일에 content_hash가 없어 전체 재임베딩을 진행합니다.")

    if df_to_embed.is_empty():
        print("[OK] [Done] 모든 데이터가 최신 상태입니다. 업데이트가 필요하지 않습니다.")
        return

    # 4. 임베딩 생성
    print(f"[INFO] [Data] 처리 대상 게임 수: {len(df_to_embed):,}개")
    engine = EmbeddingEngine(model_id=model_id)

    texts = df_to_embed["content"].to_list()
    ids = df_to_embed["id"].to_list()
    hashes = df_to_embed["content_hash"].to_list()

    print(f"[RUN] [Infer] 벡터 생성 시작 (Batch Size: {batch_size})...")
    vectors = engine.embed(texts, batch_size=batch_size)

    # 5. 결과 병합 및 저장
    new_vector_df = pl.DataFrame(
        {
            "app_id": ids,
            "vector": list(vectors),
            "content_hash": hashes
        },
        schema={
            "app_id": pl.String,
            "vector": pl.List(pl.Float64),
            "content_hash": pl.String
        }
    )

    if existing_df is not None:
        # 기존 데이터에서 새로 임베딩된 ID를 제외하고 병합
        final_df = pl.concat([
            existing_df.filter(~pl.col("app_id").is_in(new_vector_df["app_id"])),
            new_vector_df
        ])
        print(f"[INFO] [Merge] 기존 {len(existing_df):,}개 + 신규/갱신 {len(new_vector_df):,}개 -> 총 {len(final_df):,}개")
    else:
        final_df = new_vector_df

    final_df.write_parquet(output_path, compression="zstd")

    elapsed = time.time() - start_time
    print(f"\n✅ [Done] 완료! ({elapsed:.2f}초)")
    print(f"📍 저장 위치: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 2: Doc to Vector (Local, Python 3.13+)")
    
    parser.add_argument("--input", type=Path, required=True, help="Input JSONL file path")
    parser.add_argument("--output_dir", type=Path, default=Path("./data/vectors"), help="Directory to save parquet")
    parser.add_argument("--model", type=str, default="BAAI/bge-m3", help="HuggingFace Model ID")
    parser.add_argument("--batch_size", type=int, default=32, help="Inference batch size (adjust for VRAM)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows for testing")
    parser.add_argument("--incremental", action="store_true", help="Only embed new or changed items")
    
    args = parser.parse_args()
    
    run_embedding_pipeline(
        input_path=args.input,
        output_dir=args.output_dir,
        model_id=args.model,
        batch_size=args.batch_size,
        limit=args.limit,
        incremental=args.incremental
    )
