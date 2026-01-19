# ==============================================================================
# [설정 영역] 프로젝트 환경에 맞게 아래 변수들을 수정하세요.
# ==============================================================================

# 1. 실행할 파이썬 스크립트 파일명
$PYTHON_SCRIPT = "raw_to_doc.py"

# 2. 입력 데이터 경로 (Parquet 파일)
$INPUT_FILE = "./output/hugging_steam_fronkon_clean.parquet"

# 3. 템플릿 파일 경로 (Jinja2)
$TEMPLATE_FILE = "./doc_template/default.j2"

# 4. 매핑 설정 파일 경로 (JSON)
$MAPPING_FILE = ""

# 5. 결과물이 저장될 경로
$OUTPUT_FILE = "./output/output.jsonl"

# 6. RAW 데이터의 ID 컬럼명 (예: appID)
$ID_COLUMN = "appID"

# ==============================================================================
# [실행 영역]
# ==============================================================================

Write-Host "[INFO] 문서 변환 작업을 시작합니다..."
Write-Host "----------------------------------------"
Write-Host " - Python Script : $PYTHON_SCRIPT"
Write-Host " - Input Data    : $INPUT_FILE"
Write-Host " - Template      : $TEMPLATE_FILE"
Write-Host " - Output        : $OUTPUT_FILE"
Write-Host "----------------------------------------"

# 출력 파일의 디렉토리가 없으면 생성
$OUTPUT_DIR = Split-Path -Path $OUTPUT_FILE -Parent

# 만약 경로 없이 파일명만 있다면(현재 폴더) 건너뜀, 경로가 있고 존재하지 않으면 생성
if ((-not [string]::IsNullOrEmpty($OUTPUT_DIR)) -and (-not (Test-Path -Path $OUTPUT_DIR))) {
    Write-Host "[INFO] 출력 디렉토리($OUTPUT_DIR)를 생성합니다."
    New-Item -ItemType Directory -Path $OUTPUT_DIR -Force | Out-Null
}

# 1. 필수 인자들을 먼저 리스트에 담습니다.
# 주의: $PYTHON_SCRIPT는 명령어(python) 바로 뒤에 오므로 여기 리스트에는 넣지 않아도 되지만,
#       같이 관리하는 것이 편하다면 넣고 호출 방식을 바꿔도 됩니다.
#       여기서는 헷갈리지 않게 '스크립트 뒤에 붙는 인자들'만 모으겠습니다.

$scriptArgs = @(
    "--input_parquet", $INPUT_FILE,
    "--template_path", $TEMPLATE_FILE,
    "--output_path",   $OUTPUT_FILE,
    "--id_col",        $ID_COLUMN
)

# 2. 매핑 파일 변수가 비어있지 않을 때만 인자에 추가합니다.
if (-not [string]::IsNullOrEmpty($MAPPING_FILE)) {
    Write-Host " [INFO] 매핑 설정이 감지되어 옵션을 추가합니다."
    $scriptArgs += "--mapping_config"
    $scriptArgs += $MAPPING_FILE
}

# 3. 파이썬 스크립트 실행 (@scriptArgs를 사용하면 배열이 펼쳐져서 전달됩니다)
Write-Host "[INFO] Python 스크립트를 실행합니다..."
python $PYTHON_SCRIPT @scriptArgs

# 실행 결과 확인 ($LASTEXITCODE는 마지막 외부 프로그램의 종료 코드를 담습니다)
if ($LASTEXITCODE -eq 0) {
    Write-Host "----------------------------------------"
    Write-Host "[SUCCESS] 변환이 성공적으로 완료되었습니다." -ForegroundColor Green
} else {
    Write-Host "----------------------------------------"
    Write-Host "[ERROR] 변환 중 오류가 발생했습니다." -ForegroundColor Red
    exit 1
}
