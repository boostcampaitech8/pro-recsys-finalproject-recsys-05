FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
# COPY uv.lock . # Copy lock file if it exists, otherwise uv sync will generate it. 
# Assuming uv.lock might not be perfectly synced in the context of the build if strictly copied, 
# but best practice is to copy it. User has uv.lock.
COPY uv.lock .

# Install dependencies using uv
# uv sync creates a virtual environment at .venv by default
RUN uv sync --frozen

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY proto/repl .

# Environment variables
ENV PYTHONUNBUFFERED=1
# Model cache directory
ENV HF_HOME=/app/models 

# Expose Streamlit port
EXPOSE 8501

# Entrypoint is handled by docker-compose commands
