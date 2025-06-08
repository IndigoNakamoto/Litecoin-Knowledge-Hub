from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# Load environment variables from .env file
load_dotenv()

# Import the RAG chain constructor
from backend.rag_pipeline import RAGPipeline
from backend.api.v1.sources import router as sources_router

from bson import ObjectId # Import ObjectId
from fastapi.encoders import jsonable_encoder # Import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add custom JSON encoder for ObjectId
app.json_encoders = {
    ObjectId: str
}

origins = [
    "*",
    "http://localhost:3001",  # Allow requests from the frontend development server
]

app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins, # works with ["*"], but not with origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(sources_router, prefix="/api/v1/sources", tags=["Data Sources"])

# Initialize RAGPipeline globally or as a dependency
# For simplicity, initializing globally for now. Consider dependency injection for better testability.
rag_pipeline_instance = RAGPipeline()

class ChatRequest(BaseModel):
    query: str

class SourceDocument(BaseModel):
    page_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.options("/api/v1/chat")
async def chat_options():
    """
    Handle CORS preflight requests for the chat endpoint.
    """
    return {"status": "ok"}

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to handle chat queries.
    Processes the query through the RAG chain to get a generated response
    and the source documents used.
    """
    # Use the globally initialized RAG pipeline instance
    rag_output = await rag_pipeline_instance.rag_chain_with_source.ainvoke(request.query)
    
    # Transform Langchain Document objects to our Pydantic SourceDocument model
    source_documents = [
        SourceDocument(page_content=doc.page_content, metadata=doc.metadata)
        for doc in rag_output.get("context", [])
    ]
    
    return ChatResponse(
        answer=rag_output.get("answer", "No answer generated."),
        sources=source_documents
    )
