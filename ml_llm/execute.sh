#!/bin/bash

# Default values
ATTACH_FLAGS="--attach db --attach ingestion --attach app"
SCALE_FLAGS=""
ENV_VARS=""

# Check for --mac flag
if [[ "$1" == "--mac" ]]; then
    echo "🍎 Mac Optimization Mode: Using Host Ollama (GPU Accelerated)"
    # Remove --mac from arguments
    shift 
    
    # 1. Disable in-docker Ollama
    SCALE_FLAGS="--scale ollama=0"
    
    # 2. Point app to host Ollama
    # Note: OLLAMA_BASE_URL is passed via 'env' command or export
    export OLLAMA_BASE_URL="http://host.docker.internal:11434"
else
    # Default Mode: Use containerized Ollama (suppress logs from console)
    :
fi

# Run Docker Compose
# - Pass existing env vars + new ones
docker compose -f proto/repl/docker-compose.yml up --build \
    $ATTACH_FLAGS \
    $SCALE_FLAGS \
    "$@"
