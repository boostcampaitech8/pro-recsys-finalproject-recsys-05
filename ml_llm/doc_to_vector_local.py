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
    Python 3.10+ 문법을 준수하며, 하드웨어 가속(CUDA, MPS)을 지원합니다.
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
def run_embedding_pipeline(
    input_path: Path,
    output_dir: Path,
    model_id: str,
    batch_size: int,
    limit: int | None = None 
):
    start_time = time.time()
    
    # 2-1. 데이터 로드 (Lazy -> Collect)
    print(f"📂 [Input] 데이터 로드 중: {input_path}")
    
    if not input_path.exists():
        print(f"❌ [Error] 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    # JSONL 로드 (Polars LazyFrame)
    q = pl.scan_ndjson(input_path)
    
    if limit:
        print(f"⚠️ [Limit] 테스트를 위해 상위 {limit}개 데이터만 처리합니다.")
        q = q.limit(limit)
    
    try:
        # 필요한 컬럼만 선택하여 메모리에 로드
        df = q.select(["id", "content"]).collect()
    except Exception as e:
        print(f"❌ [Error] 데이터 로드 실패. JSONL 형식을 확인하세요.\n{e}")
        sys.exit(1)

    if df.is_empty():
        print("❌ [Error] 데이터가 비어있습니다.")
        sys.exit(1)

    print(f"📊 [Data] 처리 대상 게임 수: {len(df):,}개")

    # 2-2. 임베딩 생성
    engine = EmbeddingEngine(model_id=model_id)
    
    texts = df["content"].to_list()
    ids = df["id"].to_list()
    
    print(f"🧠 [Infer] 벡터 생성 시작 (Batch Size: {batch_size})...")
    # type hint: list[list[float]]
    vectors = engine.embed(texts, batch_size=batch_size)
    
    # 2-3. 결과 저장 (Parquet)
    # 모델명에서 슬래시(/)를 언더바(__)로 치환하여 파일명 생성
    safe_model_name = model_id.replace("/", "__")
    output_filename = f"vectors_{safe_model_name}.parquet"
    output_path = output_dir / output_filename
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("💾 [Save] 결과 병합 및 저장 중...")
    
    # Polars DataFrame 생성
    # 스키마: app_id(Int/Str), vector(List[Float])
    # [Tip] 2D numpy array를 list()로 감싸면 -> [1D_array, 1D_array, ...] 형태가 됩니다.
    # 이 과정은 데이터 복사 없이 포인터만 처리하므로 매우 빠릅니다.
    vector_list_of_arrays = list(vectors)

    vector_df = pl.DataFrame(
        {
            "app_id": ids,
            "vector": vector_list_of_arrays 
        },
        schema={
            "app_id": pl.String,
            "vector": pl.List(pl.Float64)
        }
    )
    
    vector_df.write_parquet(output_path, compression="zstd")
    
    elapsed = time.time() - start_time
    print(f"\n✅ [Done] 완료! ({elapsed:.2f}초)")
    print(f"📍 저장 위치: {output_path}")
    if vectors.size > 0:
        print(f"📐 벡터 차원: {vectors.shape[1]}")
    else:
        print("📐 벡터 차원: 0")

# -----------------------------------------------------------------------------
# 3. Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 2: Doc to Vector (Local, Python 3.10+)")
    
    parser.add_argument("--input", type=Path, required=True, help="Input JSONL file path")
    parser.add_argument("--output_dir", type=Path, default=Path("./data/vectors"), help="Directory to save parquet")
    parser.add_argument("--model", type=str, default="BAAI/bge-m3", help="HuggingFace Model ID")
    parser.add_argument("--batch_size", type=int, default=32, help="Inference batch size (adjust for VRAM)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows for testing")
    
    args = parser.parse_args()
    
    run_embedding_pipeline(
        input_path=args.input,
        output_dir=args.output_dir,
        model_id=args.model,
        batch_size=args.batch_size,
        limit=args.limit
    )
