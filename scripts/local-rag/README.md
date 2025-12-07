# Local RAG Services

This directory contains scripts for running local RAG (Retrieval-Augmented Generation) services on Apple Silicon Macs.

## Quick Start

The easiest way to start everything (production + local RAG) is:

```bash
./scripts/run-prod.sh -d --local-rag --pull
```

Or start local RAG separately:

```bash
./scripts/run-local-rag.sh --pull
```

## Overview

The Local RAG feature provides:
- **Local Query Rewriting**: Uses Ollama (llama3.2:3b) to rewrite queries for better search
- **Local Embeddings**: Uses stella_en_1.5B_v5 (1024-dim) for fast, local embedding generation
- **Redis Stack Cache**: Semantic vector cache with HNSW index for instant repeated query responses

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Apple Silicon Mac                             │
├─────────────────────────────────────────────────────────────────────┤
│  Docker (ARM64 Native)              │  Native Python + Metal        │
│  ┌─────────────────────┐            │  ┌─────────────────────────┐  │
│  │   Redis Stack       │            │  │  embeddings_server.py   │  │
│  │   (port 6380)       │            │  │  (port 7997)            │  │
│  │   - Vector cache    │            │  │  - stella_en_1.5B_v5    │  │
│  │   - HNSW index      │            │  │  - Metal acceleration   │  │
│  └─────────────────────┘            │  │  - ~10-20x faster than  │  │
│  ┌─────────────────────┐            │  │    Docker/Rosetta       │  │
│  │   Ollama            │            │  └─────────────────────────┘  │
│  │   (port 11434)      │            │                               │
│  │   - llama3.2:3b     │            │                               │
│  │   - Query rewriting │            │                               │
│  └─────────────────────┘            │                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Why Native Embeddings?

The Infinity Docker image (`michaelf34/infinity`) is built for x86_64 (AMD64) only. On Apple Silicon:
- Docker runs it via **Rosetta 2 emulation** → ~10x slower
- Memory usage is significantly higher
- The container frequently crashes due to memory limits

By running the embedding server natively:
- **Full Metal (MPS) acceleration** on your M1/M2/M3/M4 GPU
- **~10-20x faster** embedding generation
- **Lower memory usage**
- **No emulation overhead**

## Quick Start

### Start All Services

```bash
./scripts/run-local-rag.sh
```

This will:
1. Start Redis Stack and Ollama in Docker (ARM64 native)
2. Create a Python virtual environment at `~/infinity-env`
3. Start the native embedding server with Metal acceleration
4. Wait for all services to be ready

### Pull Ollama Model

```bash
./scripts/run-local-rag.sh --pull
```

Or manually:

```bash
docker exec -it litecoin-ollama ollama pull llama3.2:3b
```

### Stop All Services

```bash
./scripts/down-local-rag.sh
```

To also remove volumes (cached models, data):

```bash
./scripts/down-local-rag.sh -v
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Embedding Server | http://localhost:7997 | OpenAI-compatible embedding API |
| Ollama | http://localhost:11434 | Local LLM for query rewriting |
| Redis Stack | redis://localhost:6380 | Vector cache with HNSW |

## Testing Services

```bash
# Test embedding server
curl http://localhost:7997/health
curl http://localhost:7997/models
curl -X POST http://localhost:7997/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "dunzhang/stella_en_1.5B_v5", "input": "What is Litecoin?"}'

# Test Ollama
curl http://localhost:11434/api/tags

# Test Redis Stack
redis-cli -p 6380 ping
```

## Environment Variables

Enable local RAG in your backend by setting:

```bash
# Feature flags
USE_LOCAL_REWRITER=true
USE_INFINITY_EMBEDDINGS=true
USE_REDIS_CACHE=true

# Service URLs (defaults)
OLLAMA_URL=http://localhost:11434
INFINITY_URL=http://localhost:7997
REDIS_STACK_URL=redis://localhost:6380
```

## Files

- `embeddings_server.py` - FastAPI server providing OpenAI-compatible embedding API
- `../run-local-rag.sh` - Start all local RAG services
- `../down-local-rag.sh` - Stop all local RAG services

## Logs

- Embedding server logs: `logs/infinity.log`
- Docker logs: `docker logs litecoin-ollama` / `docker logs litecoin-redis-stack`

## Troubleshooting

### Embedding server won't start

Check the logs:
```bash
tail -f logs/infinity.log
```

Common issues:
- Model download failed - check internet connection
- Port 7997 already in use - kill existing process
- Python dependencies missing - run `pip install sentence-transformers fastapi uvicorn`

### Ollama model not found

Pull the model manually:
```bash
docker exec -it litecoin-ollama ollama pull llama3.2:3b
```

### Redis Stack connection refused

Check if the container is running:
```bash
docker ps | grep redis-stack
docker logs litecoin-redis-stack
```

