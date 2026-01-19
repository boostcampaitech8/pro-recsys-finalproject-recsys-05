# ==========================================
# [Stage 1] (빌드용)
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y curl build-essential

# Poetry 설치
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# 의존성 파일 복사
COPY backend/pyproject.toml backend/poetry.lock ./

# ★ 핵심: 가상환경을 프로젝트 내부에 만듦
# (PyTorch CPU 버전 설정을 pyproject.toml에 했다면 여기서 용량이 확 줄어듦)
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-root --no-interaction --no-ansi

# ==========================================
# [Stage 2]
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

# 1. 주방에서 만든 '가상환경(.venv)'만 쏙 빼옴 (15GB짜리 캐시는 버림)
COPY --from=builder /app/.venv /app/.venv

# 2. 소스 코드 복사 (608MB 문제 해결 여부 확인)
COPY configs/ ./configs/
COPY ml_rec/ ./ml_rec/
COPY backend/ ./backend/

# 3. 환경 변수
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# 4. 실행
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]