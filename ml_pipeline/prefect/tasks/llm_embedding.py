import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional
from prefect import task, get_run_logger
import polars as pl
from ml_pipeline.prefect.utils import BASE_DIR, get_ml_python_executable

@task(name="Prepare RAG Documents")
def prepare_rag_documents(config: Dict):
    """Parquet 게임 데이터를 RAG용 텍스트 문서(JSONL)로 변환합니다."""
    logger = get_run_logger()
    project_root = Path(BASE_DIR).parent
    ml_llm_dir = project_root / "ml_llm"
    
    input_parquet = project_root / "data/steam_games_info.parquet"
    if not input_parquet.exists():
        logger.warning(f"[WARN] Parquet 파일을 찾을 수 없습니다: {input_parquet}")
        input_parquet = project_root / "data/steam_games_info.jsonl"
    
    output_jsonl = ml_llm_dir / "data/game_docs.jsonl"
    template_path = ml_llm_dir / "doc_template/default.j2"
    reviews_parquet = project_root / "data/steam_reviews.parquet"
    
    os.makedirs(output_jsonl.parent, exist_ok=True)
    
    python_exe = get_ml_python_executable()
    cmd = [
        python_exe, str(ml_llm_dir / "raw_to_doc.py"),
        "--input_parquet", str(input_parquet),
        "--template_path", str(template_path),
        "--output_path", str(output_jsonl),
        "--id_col", "appid"
    ]
    if reviews_parquet.exists():
        cmd.extend(["--reviews_parquet", str(reviews_parquet)])
    
    try:
        logger.info(f"[INFO] RAG 문서 변환 시작: {input_parquet.name} -> {output_jsonl.name}")
        subprocess.run(cmd, check=True, text=True, capture_output=False)
        return str(output_jsonl)
    except Exception as e:
        logger.error(f"[ERROR] RAG 문서 변환 실패: {e}")
        return None

@task(name="Generate Game Embeddings")
def generate_game_embeddings(input_jsonl: str, config: Dict, limit: Optional[int] = None, incremental: bool = True):
    """RAG 문서를 벡터화하여 Parquet로 저장합니다."""
    logger = get_run_logger()
    if not input_jsonl or not os.path.exists(input_jsonl):
        return None
    
    project_root = Path(BASE_DIR).parent
    ml_llm_dir = project_root / "ml_llm"
    output_dir = ml_llm_dir / "data/vectors"
    
    python_exe = get_ml_python_executable()
    cmd = [
        python_exe, str(ml_llm_dir / "doc_to_vector_local.py"),
        "--input", input_jsonl,
        "--output_dir", str(output_dir),
        "--model", "BAAI/bge-m3",
        "--batch_size", "128"
    ]
    if limit:
        cmd.extend(["--limit", str(limit)])
    if incremental:
        cmd.append("--incremental")
    
    try:
        logger.info(f"[ML] 게임 벡터 생성 시작 (Model: BAAI/bge-m3)")
        subprocess.run(cmd, check=True, text=True, capture_output=False)
        output_path = output_dir / "vectors_BAAI__bge-m3.parquet"
        return str(output_path)
    except Exception as e:
        logger.error(f"[ERROR] 임베딩 생성 실패: {e}")
        return None

@task(name="Merge Vectors to Metadata")
def merge_vectors_to_metadata(jsonl_path: str, vector_parquet: str, config: Dict):
    """메타데이터(JSONL)와 벡터(Parquet)를 병합하여 새로운 Parquet를 생성합니다."""
    logger = get_run_logger()
    
    if not jsonl_path or not os.path.exists(jsonl_path):
        logger.error(f"❌ 메타데이터 파일 없음: {jsonl_path}")
        return None
        
    if not vector_parquet or not os.path.exists(vector_parquet):
        logger.warning(f"⚠️ 벡터 파일 없음: {vector_parquet} (병합 건너뜀)")
        return jsonl_path

    try:
        # 1. 벡터 데이터 로드 (Parquet -> Dict)
        logger.info(f"🧬 벡터 데이터 로드 중... ({Path(vector_parquet).name})")
        df_vec = pl.read_parquet(vector_parquet)
        vector_map = {str(row["app_id"]): row["vector"] for row in df_vec.iter_rows(named=True)}
        
        # 2. 메타데이터 로드 및 유효성 검사 (JSONL -> List[Dict])
        valid_rows = []
        broken_count = 0
        
        logger.info(f"🔄 병합 시작: {Path(jsonl_path).name} + Vectors")
        
        with open(jsonl_path, "r", encoding="utf-8") as fin:
            for line_no, line in enumerate(fin, 1):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    app_id = str(data.get("appid") or data.get("app_id"))
                    
                    # 필수 필드 검증 (예: app_id)
                    if not app_id or app_id == "None":
                        logger.warning(f"⚠️ [Line {line_no}] app_id 누락 (Skip)")
                        broken_count += 1
                        continue

                    # 벡터 매핑
                    if app_id in vector_map:
                        data["vector"] = vector_map[app_id]
                    else:
                        data["vector"] = None
                    
                    valid_rows.append(data)
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ [Line {line_no}] JSON 파싱 오류 (Skip)")
                    broken_count += 1
        
        if broken_count > 0:
            logger.warning(f"⚠️ 총 {broken_count}개의 손상된/유효하지 않은 라인이 제거되었습니다.")

        if not valid_rows:
            logger.error("❌ 유효한 데이터가 없습니다.")
            return None

        # 3. Parquet로 저장 (Polars 사용)
        output_path = jsonl_path.replace(".jsonl", "_with_vectors.parquet")
        
        # Schema 유추 및 Parquet 저장
        # JSONL -> DataFrame 변환 시 스키마 불일치 방지를 위해 일부 컬럼 타입 강제 가능
        # 여기서는 자동 유추 사용하되, 에러 발생 시 문자열로 처리하는 fallback 고려
        try:
            df_merged = pl.DataFrame(valid_rows)
            
            # [Optimization] 불필요한 중첩 구조(movies 등)가 있다면 drop하거나 stringify 할 수 있음
            # 일단 그대로 저장
            
            df_merged.write_parquet(output_path, compression="zstd")
            
            # 4. 저장된 Parquet 검증 (Read Check)
            pl.read_parquet(output_path) # 읽기 테스트
            
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"✅ 병합 및 Parquet 변환 완료: {len(df_merged)}건 ({file_size_mb:.2f}MB)")
            logger.info(f"📍 저장 경로: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Parquet 변환/저장 실패: {e}")
            return None

    except Exception as e:
        logger.error(f"❌ 데이터 병합 프로세스 실패: {e}")
        return None

