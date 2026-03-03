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
# [Stage 2] Dev: 개발 환경 (uv 도구 포함, 개발용 의존성 설치)
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

# 헬스체크용 curl 설치 (개발 환경에서도 헬스체크가 필요한 경우)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Entrypoint 스크립트 복사 및 실행 권한 부여
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000 5678
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ==========================================
# [Stage 3] Builder: 프로덕션 빌드 단계 (개발툴 제외)
# ==========================================
FROM base AS builder
# 운영(Prod) 환경용 의존성만 설치
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

# 모델과 데이터를 다운로드 받아서 이미지 굽기 (Baking)
# GCS 다운로드 스크립트를 임시 폴더에서 실행하여 다운로드 캐시 활용
COPY backend/scripts/manage_data.py /app/backend/scripts/manage_data.py
COPY backend/app/core/config.py /app/backend/app/core/config.py
COPY backend/app/core/logger.py /app/backend/app/core/logger.py
# gcs_key.json 대신 임시 환경 변수로 다운로드를 처리하거나
# 빌드 인자(ARG)로 인증 토큰을 넘기는 방식을 사용할 수 있습니다.
# (이 예시에서는 manage_data.py 가 이미 존재하는 파일 다운인 경우 캐싱에 의존)
# RUN --mount=type=secret,id=gcs_key \
#     GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcs_key \
#     mkdir -p /app/backend/app/data/processed && \
#     cd /app/backend && \
#     python scripts/manage_data.py games_metadata.jsonl --download && \
#     python scripts/manage_data.py item_similarity.pkl --download

# ==========================================
# [Stage 4] Runner: 최종 실행 이미지 (Slim 버전, uv 빌드도구 미포함)
# ==========================================
FROM python:3.11-slim-bookworm AS runner
WORKDIR /app

# 헬스체크용 curl 설치
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Builder 단계에서 생성한 가상환경(.venv) 복사
COPY --from=builder /app/.venv /app/.venv

# 소스 코드 복사 (운영 환경은 이미지 내부에 코드를 포함)
COPY configs/ ./configs/
COPY ml_rec/ ./ml_rec/
COPY backend/ ./backend/

# Entrypoint 스크립트 복사 및 실행 권한 부여
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 실행 경로 설정
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/backend:/app
ENV ML_REC_ROOT=/app/ml_rec

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]