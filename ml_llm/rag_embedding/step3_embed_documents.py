#!/usr/bin/env python3
"""
Steam RAG Document Embedding Generator
RAG 문서(game_card, pros_summary, cons_summary)를 벡터로 변환

입력: rag_documents.jsonl (Step 2 출력)
출력: rag_vectors_{model}.parquet

사용법:
python step3_embed_documents.py \
    --input /data/rag_documents.jsonl \
    --output_dir ./vectors \
    --model BAAI/bge-m3 \
    --batch_size 32
"""

import argparse
import sys
import time
from pathlib import Path
from collections import Counter
from typing import Optional

# 의존성 체크
try:
    import numpy as np
    import polars as pl
    import torch
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"❌ Error: Required package not found: {e}")
    print("\n📦 Please install required packages:")
    print("   pip install polars torch sentence-transformers")
    sys.exit(1)


# -----------------------------------------------------------------------------
# 1. Embedding Engine Class
# -----------------------------------------------------------------------------
class EmbeddingEngine:
    """로컬 임베딩 모델 래퍼 클래스"""
    
    def __init__(self, model_id: str, device: str = "auto", use_fp16: bool = True):
        self.model_id = model_id
        self.device = self._detect_device(device)
        self.use_fp16 = use_fp16
        
        print(f"🚀 [Init] 모델 로드 중: {model_id}")
        print(f"🖥️ [Device] 사용 장치: {self.device.upper()}")
        
        try:
            self.model = SentenceTransformer(
                model_id, 
                device=self.device, 
                trust_remote_code=True
            )
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print("\n💡 Tip: 모델을 처음 다운로드하는 경우 시간이 걸릴 수 있습니다.")
            print("   인터넷 연결을 확인하거나 다른 모델을 시도해보세요.")
            sys.exit(1)
        
        # FP16 적용
        if self.use_fp16 and self.device != "cpu":
            try:
                self.model.half()
                print("⚡ [Optim] FP16(Half Precision) 모드 활성화됨")
            except Exception as e:
                print(f"⚠️  [Warn] FP16 설정 실패 (FP32로 진행): {e}")

    def _detect_device(self, request: str) -> str:
        """디바이스 자동 감지"""
        if request != "auto":
            return request
        
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"🎮 [GPU] {gpu_name}")
            return "cuda"
        elif torch.backends.mps.is_available():
            print(f"🍎 [MPS] Apple Silicon detected")
            return "mps"
        
        print(f"💻 [CPU] No GPU detected, using CPU")
        return "cpu"

    def embed(self, texts: list[str], batch_size: int) -> np.ndarray:
        """텍스트 리스트를 벡터로 변환"""
        if not texts:
            return np.array([])
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                normalize_embeddings=True,  # 코사인 유사도용 정규화
                convert_to_numpy=True,
                convert_to_tensor=False
            )
            return embeddings
        except Exception as e:
            print(f"\n❌ Error during embedding: {e}")
            print("💡 Tip: batch_size를 줄여보세요 (예: --batch_size 16)")
            raise


# -----------------------------------------------------------------------------
# 2. Main Process Logic
# -----------------------------------------------------------------------------
def run_embedding_pipeline(
    input_path: Path,
    output_dir: Path,
    model_id: str,
    batch_size: int,
    limit: Optional[int] = None,
    save_metadata: bool = False
):
    """RAG 문서 임베딩 파이프라인"""
    start_time = time.time()
    
    # 2-1. 데이터 로드
    print(f"📂 [Input] 데이터 로드 중: {input_path}")
    
    if not input_path.exists():
        print(f"❌ [Error] 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    # JSONL 로드
    try:
        q = pl.scan_ndjson(input_path)
    except Exception as e:
        print(f"❌ [Error] JSONL 파일을 읽을 수 없습니다: {e}")
        sys.exit(1)
    
    if limit:
        print(f"⚠️  [Limit] 테스트를 위해 상위 {limit}개 문서만 처리합니다.")
        q = q.limit(limit)
    
    try:
        # 필요한 컬럼만 선택
        if save_metadata:
            df = q.select(["doc_id", "appid", "doc_type", "text", "meta"]).collect()
        else:
            df = q.select(["doc_id", "appid", "doc_type", "text"]).collect()
    except Exception as e:
        print(f"❌ [Error] 데이터 로드 실패. JSONL 형식 및 스키마를 확인하세요.")
        print(f"   예상 스키마: doc_id, appid, doc_type, text")
        print(f"   에러: {e}")
        sys.exit(1)

    if df.is_empty():
        print("❌ [Error] 데이터가 비어있습니다.")
        sys.exit(1)

    print(f"📊 [Data] 총 문서 수: {len(df):,}개")
    
    # 문서 타입별 통계
    doc_type_counts = Counter(df["doc_type"].to_list())
    print(f"📑 [Stats] 문서 타입별 분포:")
    for doc_type, count in doc_type_counts.most_common():
        print(f"   - {doc_type}: {count:,}개")
    
    # 고유 게임 수
    unique_appids = df["appid"].n_unique()
    print(f"🎮 [Stats] 고유 게임(appid) 수: {unique_appids:,}개")

    # 2-2. 임베딩 생성
    engine = EmbeddingEngine(model_id=model_id)
    
    texts = df["text"].to_list()
    doc_ids = df["doc_id"].to_list()
    appids = df["appid"].to_list()
    doc_types = df["doc_type"].to_list()
    
    print(f"\n🧠 [Infer] 벡터 생성 시작 (Batch Size: {batch_size})...")
    vectors = engine.embed(texts, batch_size=batch_size)
    
    # 2-3. 결과 저장 (Parquet)
    safe_model_name = model_id.replace("/", "__")
    output_filename = f"rag_vectors_{safe_model_name}.parquet"
    output_path = output_dir / output_filename
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n💾 [Save] 결과 병합 및 저장 중...")
    
    # Polars DataFrame 생성
    vector_list = list(vectors)
    
    # 기본 스키마
    output_data = {
        "doc_id": doc_ids,
        "appid": appids,
        "doc_type": doc_types,
        "vector": vector_list
    }
    
    schema = {
        "doc_id": pl.String,
        "appid": pl.Int64,
        "doc_type": pl.String,
        "vector": pl.List(pl.Float64)
    }
    
    # 메타데이터 포함 옵션
    if save_metadata and "meta" in df.columns:
        output_data["meta"] = df["meta"].to_list()
        schema["meta"] = pl.String
        print("📋 [Meta] 메타데이터 포함하여 저장")
    
    try:
        vector_df = pl.DataFrame(output_data, schema=schema)
        vector_df.write_parquet(output_path, compression="zstd")
    except Exception as e:
        print(f"❌ Error saving Parquet: {e}")
        sys.exit(1)
    
    elapsed = time.time() - start_time
    
    # 최종 통계
    print(f"\n" + "=" * 70)
    print(f"✅ [Done] 임베딩 생성 완료! (소요 시간: {elapsed:.2f}초)")
    print(f"=" * 70)
    print(f"📍 저장 위치: {output_path}")
    print(f"📦 파일 크기: {output_path.stat().st_size / (1024**2):.2f} MB")
    
    if vectors.size > 0:
        print(f"📐 벡터 차원: {vectors.shape[1]}")
        print(f"📊 총 벡터 수: {len(vectors):,}개")
        print(f"⚡ 처리 속도: {len(vectors) / elapsed:.1f} docs/sec")
    
    print(f"\n💡 [Next Step] pgvector에 로드:")
    print(f"   python load_to_pgvector.py --input {output_path}")


# -----------------------------------------------------------------------------
# 3. Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RAG Document Embedding Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--input", 
        type=Path, 
        required=True, 
        help="Input RAG documents JSONL file (from Step 2)"
    )
    parser.add_argument(
        "--output_dir", 
        type=Path, 
        default=Path("./vectors"), 
        help="Output directory for parquet files"
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default="BAAI/bge-m3", 
        help="HuggingFace Model ID"
    )
    parser.add_argument(
        "--batch_size", 
        type=int, 
        default=32, 
        help="Inference batch size (reduce if OOM)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=None, 
        help="Limit number of documents for testing"
    )
    parser.add_argument(
        "--save_metadata",
        action="store_true",
        help="Include metadata field in output"
    )
    
    args = parser.parse_args()
    
    try:
        run_embedding_pipeline(
            input_path=args.input,
            output_dir=args.output_dir,
            model_id=args.model,
            batch_size=args.batch_size,
            limit=args.limit,
            save_metadata=args.save_metadata
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
