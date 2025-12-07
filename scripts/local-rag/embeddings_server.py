#!/usr/bin/env python3
"""
Native Embedding Server for Apple Silicon (M1/M2/M3/M4)

This provides an OpenAI-compatible embedding API using sentence-transformers
with Metal (MPS) acceleration. Much faster than running Infinity under Rosetta.

Usage:
    python embeddings_server.py [--port 7997] [--device mps|cpu]

API Endpoints:
    GET  /models     - List available models
    POST /embeddings - Generate embeddings (OpenAI-compatible format)
    GET  /health     - Health check
"""

import argparse
import logging
import os
from typing import List, Union, Optional, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
# BGE-M3: Excellent Q&A retrieval, 1024-dim, ~2GB memory (vs Stella's 11GB)
MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "BAAI/bge-m3")
DEFAULT_PORT = int(os.getenv("INFINITY_PORT", "7997"))
DEFAULT_DEVICE = os.getenv("EMBEDDING_DEVICE", "mps")  # mps for Metal on Apple Silicon

app = FastAPI(
    title="Native Embedding Server",
    description="OpenAI-compatible embedding API for Apple Silicon",
    version="1.0.0"
)

# Global model instance (loaded at startup)
model: SentenceTransformer = None
# Global device (for batch size optimization)
current_device: str = DEFAULT_DEVICE


class EmbeddingRequest(BaseModel):
    """OpenAI-compatible embedding request"""
    model: str
    input: Union[str, List[str]]


class EmbeddingData(BaseModel):
    """Single embedding result"""
    embedding: List[float]
    index: int
    object: str = "embedding"
    sparse_embedding: Optional[Dict[str, float]] = None  # Sparse embedding for BGE-M3


class EmbeddingResponse(BaseModel):
    """OpenAI-compatible embedding response"""
    data: List[EmbeddingData]
    model: str
    object: str = "list"
    usage: dict = {"prompt_tokens": 0, "total_tokens": 0}


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    object: str = "model"
    owned_by: str = "local"


class ModelsResponse(BaseModel):
    """List of available models"""
    data: List[ModelInfo]
    object: str = "list"


@app.on_event("startup")
async def load_model():
    """Load the embedding model at startup"""
    global model, current_device
    device = os.getenv("EMBEDDING_DEVICE", DEFAULT_DEVICE)
    current_device = device
    logger.info(f"Loading model {MODEL_ID} on device {device}...")
    
    try:
        # Load model with default settings (BGE-M3 handles optimization internally)
        model = SentenceTransformer(MODEL_ID, device=device)
        
        # Set model to eval mode for inference (saves memory)
        if hasattr(model, "eval"):
            model.eval()
        
        logger.info(f"Model loaded successfully! Vector dimension: {model.get_sentence_embedding_dimension()}")
        logger.info(f"Device: {device}, Batch size will be reduced for MPS")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy", "model": MODEL_ID}


@app.get("/models", response_model=ModelsResponse)
async def list_models():
    """List available embedding models (OpenAI-compatible)"""
    return ModelsResponse(
        data=[ModelInfo(id=MODEL_ID)]
    )


@app.post("/embeddings", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    """Generate embeddings (OpenAI-compatible format)"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Handle single string or list of strings
    texts = [request.input] if isinstance(request.input, str) else request.input
    
    if not texts:
        raise HTTPException(status_code=400, detail="Input cannot be empty")
    
    try:
        # Generate dense embeddings with memory optimization
        # Use smaller batch size for MPS to reduce memory pressure
        batch_size = 8 if current_device == "mps" else 32
        dense_embeddings = model.encode(
            texts, 
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True  # Free GPU memory faster
        )
        
        # For BGE-M3, generate TF-IDF-based sparse embeddings for hybrid retrieval
        supports_sparse = MODEL_ID.lower().endswith("bge-m3")
        sparse_embeddings_list = []
        
        if supports_sparse:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                import re
                
                # Simple TF-IDF on texts
                tfidf = TfidfVectorizer(max_features=1000, lowercase=True, stop_words='english')
                tfidf_vectors = tfidf.fit_transform(texts)
                
                # Convert to dict format {word: weight}
                feature_names = tfidf.get_feature_names_out()
                for i, vector in enumerate(tfidf_vectors):
                    sparse_dict = {}
                    # Get non-zero entries
                    rows, cols = vector.nonzero()
                    for row, col in zip(rows, cols):
                        word = feature_names[col]
                        weight = float(vector[row, col])
                        if weight > 0.01:  # Threshold to keep only significant terms
                            sparse_dict[word] = weight
                    sparse_embeddings_list.append(sparse_dict)
            except ImportError:
                logger.warning("scikit-learn not available, skipping sparse embeddings")
                sparse_embeddings_list = [None] * len(texts)
            except Exception as e:
                logger.warning(f"Failed to generate sparse embeddings: {e}")
                sparse_embeddings_list = [None] * len(texts)
        else:
            sparse_embeddings_list = [None] * len(texts)
        
        # Format response
        data = []
        for i, dense in enumerate(dense_embeddings):
            data.append(EmbeddingData(
                embedding=dense.tolist(),
                sparse_embedding=sparse_embeddings_list[i],
                index=i
            ))
        
        return EmbeddingResponse(
            data=data,
            model=request.model
        )
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    parser = argparse.ArgumentParser(description="Native Embedding Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Device: mps (Metal), cpu, or cuda")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    # Set device via environment for startup handler
    os.environ["EMBEDDING_DEVICE"] = args.device
    
    logger.info(f"Starting embedding server on {args.host}:{args.port} with device={args.device}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

