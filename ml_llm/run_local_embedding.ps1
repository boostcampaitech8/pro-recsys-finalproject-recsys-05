# =============================================================================
# [Project] Steam Game Recommendation Service
# Step 2: Doc to Vector Embedding Runner (Windows PowerShell)
# =============================================================================

# 에러 발생 시 즉시 중단 설정
$ErrorActionPreference = "Stop"

# 1. 환경 변수 및 설정 정의 (Configuration)
# -----------------------------------------------------------------------------
$PythonCmd = "python"
$ScriptPath = "doc_to_vector_local.py"

# 입력/출력 경로
$InputFile = ".\output\output.jsonl"
$OutputDir = ".\output\vectors"

# 사용할 모델 (BAAI/bge-m3 등)
$ModelId = "BAAI/bge-m3"

# 배치 크기
$BatchSize = 32

# 2. 사전 검사 (Pre-flight Check)
# -----------------------------------------------------------------------------
if (-not (Test-Path -Path $InputFile)) {
    Write-Host "❌ [Error] Input file not found: $InputFile" -ForegroundColor Red
    Write-Host "   Please run Step 1 (RAW -> Doc) first." -ForegroundColor Gray
    exit 1
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "🚀 Starting Embedding Pipeline (Direct Run)" -ForegroundColor Cyan
Write-Host "   - Model: $ModelId"
Write-Host "   - Batch: $BatchSize"
Write-Host "   - Input: $InputFile"
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 3. 전체 데이터 실행 (Production Run)
# -----------------------------------------------------------------------------
Write-Host "⏳ Processing full dataset..." -ForegroundColor Yellow

# limit 옵션 없이 바로 실행
& $PythonCmd $ScriptPath `
    --input $InputFile `
    --output_dir $OutputDir `
    --model $ModelId `
    --batch_size $BatchSize

# 종료 코드 확인
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🎉 All jobs finished successfully." -ForegroundColor Green
} else {
    Write-Host "`n❌ Job failed with exit code $LASTEXITCODE." -ForegroundColor Red
    exit 1
}
