# ==========================================
# [Stage 1] (빌드용) - uv 공식 이미지 사용
# ==========================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# 환경 변수 설정
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 의존성 파일 복사
# uv.lock이 아직 없더라도 pyproject.toml만으로도 설치 가능합니다.
# (나중에 로컬에서 uv sync 후 lock 파일이 생기면 같이 COPY 됩니다)
COPY backend/pyproject.toml backend/uv.lock* ./

# uv.lock이 없으므로 --frozen 옵션을 빼고 실행해야 합니다.
# (최초 빌드 시 lock 파일 생성 허용)
RUN uv sync --no-dev --no-install-project

# ==========================================
# [Stage 2] (실행용)
# ==========================================
FROM python:3.11-slim-bookworm AS runner

WORKDIR /app

# 1. 빌드 스테이지에서 설치된 가상환경(.venv) 복사
COPY --from=builder /app/.venv /app/.venv

# 2. 소스 코드 복사
COPY configs/ ./configs/
COPY ml_rec/ ./ml_rec/
COPY backend/ ./backend/

# 3. 환경 변수 (가상환경 bin을 PATH에 추가)
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# 4. 실행
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]