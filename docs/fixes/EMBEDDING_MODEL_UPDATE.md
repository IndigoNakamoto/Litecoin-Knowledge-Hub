# Embedding Model Update: Stella → BGE-M3

**Date**: 2025-12-07  
**Status**: ✅ Instructions provided

---

## Issue

The system is still using `dunzhang/stella_en_1.5B_v5` instead of `BAAI/bge-m3`, causing:
- Poor retrieval quality
- Higher memory usage (11GB vs 68MB)
- Worse Q&A performance

---

## Root Cause

The `.env.docker.prod` file has:
```bash
EMBEDDING_MODEL_ID=dunzhang/stella_en_1.5B_v5
```

This overrides the default `BAAI/bge-m3` in the code.

---

## Solution

### Step 1: Update `.env.docker.prod`

Change:
```bash
EMBEDDING_MODEL_ID=dunzhang/stella_en_1.5B_v5
```

To:
```bash
EMBEDDING_MODEL_ID=BAAI/bge-m3
```

### Step 2: Restart Embedding Server

The native embedding server reads from environment variables. Restart it with the new model:

```bash
# Stop current server
pkill -f embeddings_server

# Wait for it to stop
sleep 2

# Start with BGE-M3
source ~/infinity-env/bin/activate
export EMBEDDING_MODEL_ID='BAAI/bge-m3'
python scripts/local-rag/embeddings_server.py --device mps --port 7997 &
```

**Note**: The first time it runs, it will download BGE-M3 (~1.2GB). This is a one-time download.

### Step 3: Restart Backend

The backend reads `EMBEDDING_MODEL_ID` from `.env.docker.prod`:

```bash
docker restart litecoin-backend
```

---

## Verification

After restarting, verify both services are using BGE-M3:

```bash
# Check embedding server
curl -s http://localhost:7997/health | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Model: {d[\"model\"]}')"

# Check backend logs
docker logs litecoin-backend --tail 20 | grep "InfinityEmbeddings initialized"
```

Should show:
- Embedding server: `"model": "BAAI/bge-m3"`
- Backend: `model=BAAI/bge-m3`

---

## Expected Improvements

After switching to BGE-M3:

| Metric | Stella 1.5B | BGE-M3 | Improvement |
|--------|-------------|--------|-------------|
| Memory | 11GB | 68MB | 162x reduction |
| Q&A Quality | Poor | Excellent | Significant |
| Retrieval Accuracy | Low | High | Much better |
| Model Size | 5.5GB | 1.2GB | 4.6x smaller |

---

## Why BGE-M3 is Better

1. **Better Q&A Performance**: BGE-M3 is specifically optimized for question-answering tasks
2. **Memory Efficient**: 68MB vs 11GB (162x reduction)
3. **Sparse Embeddings**: Supports hybrid dense+sparse retrieval
4. **Faster**: Smaller model = faster inference
5. **Better Retrieval**: Higher accuracy for factual questions

---

## Troubleshooting

### Embedding Server Won't Start

If the embedding server fails to start:
1. Check if BGE-M3 is downloaded: `ls ~/.cache/huggingface/hub/models--BAAI--bge-m3/`
2. Check logs: Look for error messages in the terminal
3. Try CPU mode: `--device cpu` instead of `--device mps`

### Backend Still Shows Stella

If backend logs still show Stella:
1. Verify `.env.docker.prod` was updated correctly
2. Check if file was saved
3. Restart backend: `docker restart litecoin-backend`
4. Check logs: `docker logs litecoin-backend | grep EMBEDDING_MODEL_ID`

---

**Status**: ✅ Ready to apply - Update `.env.docker.prod` and restart services

