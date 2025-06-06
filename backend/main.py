from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

from rag_pipeline import retrieve_documents

app = FastAPI()

class ChatRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to handle chat queries.
    Retrieves relevant documents from the vector store based on the user's query.
    """
    retrieved_docs = await retrieve_documents(request.query)
    
    # For now, return the retrieved documents directly for testing
    # We will later pass these to a language model to generate a response
    return {"retrieved_documents": retrieved_docs}
