# ==========================================
# [Stage 1] Base: 공통 환경 및 uv 설치
# ==========================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

# 의존성 파일 복사 (Common)
COPY backend/pyproject.toml backend/uv.lock ./

# ==========================================
# [Stage 2] Dev: 개발 환경 (uv 포함, dev 의존성 설치)
# ==========================================
FROM base AS dev
# 개발용 환경변수
ENV PYTHONDONTWRITEBYTECODE=1
# 실행 경로 설정
ENV PATH="/app/.venv/bin:$PATH"

# Dev 의존성 설치 (--no-dev 옵션 제거)
# 소스 코드는 볼륨 마운트로 들어오므로 COPY 하지 않음
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# 헬스체크용 curl 설치 (User Request: Dev 환경에서도 필요 시)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

EXPOSE 8000 5678
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ==========================================
# [Stage 3] Builder: 프로덕션용 빌드 (no-dev)
# ==========================================
FROM base AS builder
# Prod 의존성만 설치
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

# ==========================================
# [Stage 4] Runner: 프로덕션 실행 이미지 (Slim, uv 미포함)
# ==========================================
FROM python:3.11-slim-bookworm AS runner
WORKDIR /app

# 헬스체크용 curl 설치
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 가상환경 복사 from Builder
COPY --from=builder /app/.venv /app/.venv

# 소스 코드 복사 (Prod는 이미지 안에 코드 포함)
COPY configs/ ./configs/
COPY ml_rec/ ./ml_rec/
COPY backend/ ./backend/

# 실행 경로 설정
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/backend:/app
ENV ML_REC_ROOT=/app/ml_rec

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]