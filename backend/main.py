from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# Load environment variables from .env file
load_dotenv()

# Import the RAG chain constructor
from rag_pipeline import get_rag_chain

app = FastAPI()

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

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to handle chat queries.
    Processes the query through the RAG chain to get a generated response
    and the source documents used.
    """
    # Get the RAG chain
    rag_chain = await get_rag_chain()
    
    # Invoke the chain with the user's query
    # The chain now returns a dictionary with "answer" and "context" (source documents)
    rag_output = await rag_chain.ainvoke(request.query)
    
    # Transform Langchain Document objects to our Pydantic SourceDocument model
    source_documents = [
        SourceDocument(page_content=doc.page_content, metadata=doc.metadata)
        for doc in rag_output.get("context", [])
    ]
    
    return ChatResponse(
        answer=rag_output.get("answer", "No answer generated."),
        sources=source_documents
    )
