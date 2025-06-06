from fastapi import FastAPI
from pydantic import BaseModel
from rag_pipeline import get_placeholder_chain

app = FastAPI()

class ChatRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest):
    chain = get_placeholder_chain()
    response = await chain.ainvoke(request.query)
    # The response from the prompt template is a ChatPromptValue, we need to extract the string
    return {"response": response.to_string()}
