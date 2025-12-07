#!/bin/bash
# =============================================================================
# Local RAG Services Startup Script
# =============================================================================
# Starts Redis Stack, Ollama, and Infinity embedding services for local RAG.
#
# On Apple Silicon (M1/M2/M3/M4):
#   - Redis Stack and Ollama run in Docker (native ARM64 support)
#   - Infinity runs natively using Python + Metal acceleration (much faster)
#
# On x86_64 (Intel/AMD):
#   - All services run in Docker
#
# Usage:
#   ./scripts/run-local-rag.sh          # Start all local RAG services
#   ./scripts/run-local-rag.sh --pull   # Pull Ollama model after starting
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect Docker Compose command
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose version &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}❌ Error: Docker Compose not found!${NC}"
    exit 1
fi

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
LOCAL_RAG_DIR="$SCRIPT_DIR/local-rag"

# Detect architecture
ARCH=$(uname -m)
IS_ARM64=false
if [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
    IS_ARM64=true
fi

# Configuration
VENV_DIR="$HOME/infinity-env"
OLLAMA_MODEL="${LOCAL_REWRITER_MODEL:-llama3.2:3b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL_ID:-dunzhang/stella_en_1.5B_v5}"
INFINITY_PORT="${INFINITY_PORT:-7997}"
PULL_MODEL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --pull)
            PULL_MODEL=true
            shift
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            shift
            ;;
    esac
done

echo -e "${BLUE}🚀 Starting Local RAG Services${NC}"
echo ""
echo -e "   Architecture: ${GREEN}$ARCH${NC}"
if $IS_ARM64; then
    echo -e "   Mode: ${GREEN}Native embedding server (Metal acceleration)${NC}"
else
    echo -e "   Mode: ${GREEN}Docker-based (all services)${NC}"
fi
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Load environment variables
if [ -f ".env.docker.prod" ]; then
    echo -e "${BLUE}📦 Loading environment from .env.docker.prod...${NC}"
    set -a
    source <(grep -v '^[[:space:]]*#' .env.docker.prod | grep -v '^[[:space:]]*$')
    set +a
fi

if [ -f ".env.secrets" ]; then
    echo -e "${BLUE}🔐 Loading secrets from .env.secrets...${NC}"
    set -a
    source <(grep -v '^[[:space:]]*#' .env.secrets | grep -v '^[[:space:]]*$')
    set +a
fi

# Provide dummy value for Grafana password (required for docker-compose parsing)
export GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-dummy-for-local-rag}"

# =============================================================================
# Start Docker services (Redis Stack and optionally Ollama)
# =============================================================================
echo ""

# Build compose files argument
COMPOSE_FILES="-f docker-compose.prod.yml"
if [ -f "docker-compose.override.yml" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.override.yml"
fi

# Check if native Ollama is already running
NATIVE_OLLAMA_RUNNING=false
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    # Check it's NOT the Docker container (which would be stopped/starting)
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "litecoin-ollama"; then
        NATIVE_OLLAMA_RUNNING=true
        echo -e "${GREEN}🍎 Native Ollama detected on port 11434 - using it instead of Docker${NC}"
    fi
fi

if $NATIVE_OLLAMA_RUNNING; then
    # Only start Redis Stack when using native Ollama
    echo -e "${BLUE}🐳 Starting Docker services (Redis Stack only - native Ollama detected)...${NC}"
    $DOCKER_COMPOSE $COMPOSE_FILES --profile local-rag up -d redis_stack
    echo -e "${GREEN}   ✓ Redis Stack started (port 6380)${NC}"
    echo -e "${GREEN}   ✓ Ollama running natively (port 11434)${NC}"
else
    # Start both Redis Stack and Ollama in Docker
    echo -e "${BLUE}🐳 Starting Docker services (Redis Stack, Ollama)...${NC}"
    $DOCKER_COMPOSE $COMPOSE_FILES --profile local-rag up -d redis_stack ollama
    echo -e "${GREEN}   ✓ Redis Stack started (port 6380)${NC}"
    echo -e "${GREEN}   ✓ Ollama started (port 11434)${NC}"
fi

# =============================================================================
# Start Infinity Embedding Service
# =============================================================================
echo ""
if $IS_ARM64; then
    # Apple Silicon: Run Infinity natively with Metal
    echo -e "${BLUE}🍎 Starting native embedding server (Apple Silicon + Metal)...${NC}"
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}   Creating virtual environment at $VENV_DIR...${NC}"
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Check if dependencies are installed
    if ! python3 -c "import sentence_transformers, fastapi, uvicorn" 2>/dev/null; then
        echo -e "${YELLOW}   Installing dependencies...${NC}"
        pip install --quiet sentence-transformers fastapi uvicorn pydantic
    fi
    
    # Check if server is already running
    if curl -s http://localhost:$INFINITY_PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}   ✓ Embedding server already running on port $INFINITY_PORT${NC}"
    else
        # Start the embedding server in the background
        echo -e "${BLUE}   Starting embedding server on port $INFINITY_PORT...${NC}"
        nohup python3 "$LOCAL_RAG_DIR/embeddings_server.py" --port $INFINITY_PORT --device mps \
            > "$PROJECT_ROOT/logs/infinity.log" 2>&1 &
        
        # Save PID for later shutdown
        echo $! > "$PROJECT_ROOT/.infinity.pid"
        
        # Wait for server to be ready (model loading takes ~60s)
        echo -e "${YELLOW}   Waiting for model to load (this may take 60-90 seconds)...${NC}"
        MAX_WAIT=120
        WAITED=0
        while ! curl -s http://localhost:$INFINITY_PORT/health > /dev/null 2>&1; do
            sleep 5
            WAITED=$((WAITED + 5))
            if [ $WAITED -ge $MAX_WAIT ]; then
                echo -e "${RED}   ❌ Timeout waiting for embedding server${NC}"
                echo -e "${YELLOW}   Check logs: tail -f $PROJECT_ROOT/logs/infinity.log${NC}"
                exit 1
            fi
            echo -e "${YELLOW}   Still loading... ($WAITED/$MAX_WAIT seconds)${NC}"
        done
        
        echo -e "${GREEN}   ✓ Embedding server ready on port $INFINITY_PORT${NC}"
    fi
    
    deactivate
else
    # x86_64: Use Docker-based Infinity
    echo -e "${BLUE}🐳 Starting Infinity via Docker...${NC}"
    $DOCKER_COMPOSE $COMPOSE_FILES --profile local-rag up -d infinity
    
    echo -e "${YELLOW}   Waiting for Infinity to load model (this may take 2-3 minutes)...${NC}"
    MAX_WAIT=180
    WAITED=0
    while ! curl -s http://localhost:$INFINITY_PORT/models > /dev/null 2>&1; do
        sleep 10
        WAITED=$((WAITED + 10))
        if [ $WAITED -ge $MAX_WAIT ]; then
            echo -e "${RED}   ❌ Timeout waiting for Infinity${NC}"
            echo -e "${YELLOW}   Check logs: docker logs litecoin-infinity${NC}"
            exit 1
        fi
        echo -e "${YELLOW}   Still loading... ($WAITED/$MAX_WAIT seconds)${NC}"
    done
    
    echo -e "${GREEN}   ✓ Infinity ready on port $INFINITY_PORT${NC}"
fi

# =============================================================================
# Pull Ollama Model (optional)
# =============================================================================
if $PULL_MODEL; then
    echo ""
    echo -e "${BLUE}📥 Pulling Ollama model: $OLLAMA_MODEL...${NC}"
    if $NATIVE_OLLAMA_RUNNING; then
        # Use native ollama command
        ollama pull "$OLLAMA_MODEL"
    else
        # Use Docker container
        docker exec litecoin-ollama ollama pull "$OLLAMA_MODEL"
    fi
    echo -e "${GREEN}   ✓ Model $OLLAMA_MODEL ready${NC}"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}✅ Local RAG services are running!${NC}"
echo ""
echo -e "${BLUE}📋 Service URLs:${NC}"
echo -e "   Redis Stack:      redis://localhost:6380"
echo -e "   Ollama:           http://localhost:11434"
echo -e "   Embedding Server: http://localhost:$INFINITY_PORT"
echo ""
echo -e "${BLUE}📋 Test commands:${NC}"
echo -e "   curl http://localhost:$INFINITY_PORT/models"
echo -e "   curl http://localhost:11434/api/tags"
echo -e "   redis-cli -p 6380 ping"
echo ""
echo -e "${BLUE}📋 Environment variables to enable local RAG:${NC}"
echo -e "   USE_LOCAL_REWRITER=true"
echo -e "   USE_INFINITY_EMBEDDINGS=true"
echo -e "   USE_REDIS_CACHE=true"
echo ""
if ! $PULL_MODEL; then
    echo -e "${YELLOW}💡 Tip: Run with --pull to download Ollama model:${NC}"
    echo -e "   ./scripts/run-local-rag.sh --pull"
    echo ""
fi
echo -e "${YELLOW}💡 To stop all local RAG services:${NC}"
echo -e "   ./scripts/down-local-rag.sh"

