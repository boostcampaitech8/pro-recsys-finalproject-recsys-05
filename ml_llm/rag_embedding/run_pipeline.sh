#!/bin/bash
set -e  # 에러 발생 시 즉시 종료

# ==================== 설정 ====================
# 입력 파일 경로
REVIEWS_JSONL="/data/ephemeral/home/T8161/game_data/extracted/steam_reviews.jsonl"
GAMES_INFO_JSONL="/data/ephemeral/home/T8161/game_data/extracted/steam_games_info.jsonl"

# 출력 디렉토리
OUTPUT_DIR="/data/ephemeral/home/T8161/game3/processed"
VECTORS_DIR="${OUTPUT_DIR}/vectors"

# 중간 파일 경로
SENTENCES_JSONL="${OUTPUT_DIR}/steam_review_sents.jsonl"
RAG_DOCS_JSONL="${OUTPUT_DIR}/rag_documents.jsonl"

# Step 1 파라미터
ALLOWED_LANGS="koreana english"  # ← 영어 추가!
MIN_SENT_LEN=20
MAX_SENT_LEN=200

# Step 2 파라미터
TOP_POS=80
TOP_NEG=40
BULLETS=8

# Step 3 파라미터
MODEL="BAAI/bge-m3"
BATCH_SIZE=32

# ==================== 파이프라인 실행 ====================
echo "=========================================="
echo "🚀 Steam Game RAG Pipeline"
echo "=========================================="
echo ""

# 출력 디렉토리 생성
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${VECTORS_DIR}"

# Step 1: 리뷰 문장 전처리
echo "📝 Step 1/3: 리뷰 문장 전처리"
echo "------------------------------------------"
python3 step1_review_to_sentences.py \
    --input "${REVIEWS_JSONL}" \
    --output "${SENTENCES_JSONL}" \
    --allowed_langs ${ALLOWED_LANGS} \
    --min_sent_len ${MIN_SENT_LEN} \
    --max_sent_len ${MAX_SENT_LEN}

if [ $? -ne 0 ]; then
    echo "❌ Step 1 failed"
    exit 1
fi
echo ""

# Step 2: RAG 문서 생성
echo "📝 Step 2/3: RAG 문서 생성"
echo "------------------------------------------"
python3 step2_generate_rag_docs.py \
    --sents "${SENTENCES_JSONL}" \
    --info "${GAMES_INFO_JSONL}" \
    --output "${RAG_DOCS_JSONL}" \
    --top_pos ${TOP_POS} \
    --top_neg ${TOP_NEG} \
    --bullets ${BULLETS}

if [ $? -ne 0 ]; then
    echo "❌ Step 2 failed"
    exit 1
fi
echo ""

# Step 3: 임베딩 생성
echo "📝 Step 3/3: 임베딩 생성"
echo "------------------------------------------"
python3 step3_embed_documents.py \
    --input "${RAG_DOCS_JSONL}" \
    --output_dir "${VECTORS_DIR}" \
    --model "${MODEL}" \
    --batch_size ${BATCH_SIZE}

if [ $? -ne 0 ]; then
    echo "❌ Step 3 failed"
    exit 1
fi
echo ""

# 완료
echo "=========================================="
echo "✅ Pipeline Complete!"
echo "=========================================="
echo ""
echo "📁 Output Files:"
echo "  - Sentences: ${SENTENCES_JSONL}"
echo "  - RAG Docs:  ${RAG_DOCS_JSONL}"
echo "  - Vectors:   ${VECTORS_DIR}/rag_vectors_*.parquet"
echo ""
echo "💡 Next Steps:"
echo "  1. Load vectors to pgvector"
echo "  2. Build search API"
echo "  3. Create recommendation system"