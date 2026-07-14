#!/bin/bash

# =============================================================================
# [Project] Steam Game Recommendation Service
# Step 2: Doc to Vector Embedding Runner
# =============================================================================

# 1. 환경 변수 및 설정 정의 (Configuration)
# -----------------------------------------------------------------------------
PYTHON_CMD="python"  # python3, python3.13 등으로 변경 가능
SCRIPT_PATH="doc_to_vector_local.py"

# 입력 파일 경로 (1단계에서 생성된 파일 위치를 정확히 지정하세요)
INPUT_FILE="./data/processed/output.jsonl"
OUTPUT_DIR="./data/vectors"

# 사용할 모델 (실험에 따라 변경: BAAI/bge-m3, intfloat/multilingual-e5-large 등)
MODEL_ID="BAAI/bge-m3"

# 하드웨어 설정 (VRAM에 맞춰 조절: 32, 64, 128...)
BATCH_SIZE=32


# 2. 사전 검사 (Pre-flight Check)
# -----------------------------------------------------------------------------
# 에러 발생 시 즉시 중단
set -e 

if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ [Error] Input file not found: $INPUT_FILE"
    echo "   Please run Step 1 (RAW -> Doc) first."
    exit 1
fi

echo "========================================================"
echo "🚀 Starting Embedding Pipeline"
echo "   - Model: $MODEL_ID"
echo "   - Batch: $BATCH_SIZE"
echo "   - Input: $INPUT_FILE"
echo "========================================================"
echo ""


# 3. 테스트 실행 (Sanity Check)
# -----------------------------------------------------------------------------
# 전체를 돌리기 전, 50개만 샘플링하여 파이프라인(로드->임베딩->저장) 검증
# echo "🧪 [Phase 1] Running Sanity Check (Limit: 50)..."

# $PYTHON_CMD "$SCRIPT_PATH" \
#     --input "$INPUT_FILE" \
#     --output_dir "$OUTPUT_DIR" \
#     --model "$MODEL_ID" \
#     --batch_size "$BATCH_SIZE" \
#     --limit 50

# if [ $? -eq 0 ]; then
#     echo "✅ Sanity check passed!"
# else
#     echo "❌ Sanity check failed. Please check the logs above."
#     exit 1
# fi
# echo ""


# 4. 실전 실행 (Production Run)
# -----------------------------------------------------------------------------
# 사용자에게 진행 여부 묻기 (실수 방지)
# read -p "❓ Proceed with FULL data processing? (y/n): " confirm

if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    echo "🚀 [Phase 2] Running Full Processing..."
    
    # limit 옵션을 제거하여 전체 데이터 처리
    $PYTHON_CMD "$SCRIPT_PATH" \
        --input "$INPUT_FILE" \
        --output_dir "$OUTPUT_DIR" \
        --model "$MODEL_ID" \
        --batch_size "$BATCH_SIZE"
        
    echo "🎉 All jobs finished successfully."
else
    echo "🚫 Operation cancelled by user."
fi
