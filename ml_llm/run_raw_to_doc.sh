#!/bin/bash

# ==============================================================================
# [설정 영역] 프로젝트 환경에 맞게 아래 변수들을 수정하세요.
# ==============================================================================

# 1. 실행할 파이썬 스크립트 파일명
PYTHON_SCRIPT="raw_to_doc.py"

# 2. 입력 데이터 경로 (Parquet 파일)
INPUT_FILE="games.parquet"

# 3. 템플릿 파일 경로 (Jinja2)
TEMPLATE_FILE="./doc_template/default.j2"

# 4. 매핑 설정 파일 경로 (JSON)
# 비워두면("") 파이썬 스크립트가 내부 로직(template 경로 탐색)을 따릅니다.
MAPPING_FILE="" 
# 또는
# MAPPING_FILE="./mapping/default.json"

# 5. 결과물이 저장될 경로
OUTPUT_FILE="output.jsonl"

# 6. RAW 데이터의 ID 컬럼명 (예: appID)
ID_COLUMN="steam_appid"

# ==============================================================================
# [실행 영역]
# ==============================================================================

echo "[INFO] 문서 변환 작업을 시작합니다..."
echo "----------------------------------------"
echo " - Python Script : $PYTHON_SCRIPT"
echo " - Input Data    : $INPUT_FILE"
echo " - Template      : $TEMPLATE_FILE"
echo " - Output        : $OUTPUT_FILE"
if [ -n "$MAPPING_FILE" ]; then
    echo " - Mapping       : $MAPPING_FILE"
else
    echo " - Mapping       : (Auto Detect)"
fi
echo "----------------------------------------"

# 출력 파일의 디렉토리가 없으면 생성
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "[INFO] 출력 디렉토리($OUTPUT_DIR)를 생성합니다."
    mkdir -p "$OUTPUT_DIR"
fi

# -----------------------------------------------------------
# [변경 포인트] 실행 인자를 배열로 동적 생성
# -----------------------------------------------------------

# 1. 필수 인자들을 배열에 담습니다.
CMD_ARGS=(
    --input_parquet "$INPUT_FILE"
    --template_path "$TEMPLATE_FILE"
    --output_path "$OUTPUT_FILE"
    --id_col "$ID_COLUMN"
)

# 2. 매핑 파일 변수가 비어있지 않으면(-n) 배열에 추가합니다.
if [ -n "$MAPPING_FILE" ]; then
    CMD_ARGS+=(--mapping_config "$MAPPING_FILE")
fi

# 3. 파이썬 스크립트 실행 ("${CMD_ARGS[@]}"는 배열을 개별 인자로 풀어서 전달합니다)
python "$PYTHON_SCRIPT" "${CMD_ARGS[@]}"

# 실행 결과 확인
if [ $? -eq 0 ]; then
    echo "----------------------------------------"
    echo "[SUCCESS] 변환이 성공적으로 완료되었습니다."
else
    echo "----------------------------------------"
    echo "[ERROR] 변환 중 오류가 발생했습니다."
    exit 1
fi