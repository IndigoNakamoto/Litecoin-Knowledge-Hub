import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pymongo import MongoClient

# Constants
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "litecoin_rag_db"
COLLECTION_NAME = "litecoin_docs"
INDEX_NAME = "vector_index"

# Ensure the environment variable is set
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set!")

# Initialize MongoDB client and collection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Initialize Embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# Initialize Vector Store
vector_store = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name=INDEX_NAME
)

async def retrieve_documents(query: str):
    """
    Retrieves documents from MongoDB Atlas Vector Search based on a user query.
    """
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5}  # Retrieve top 5 most similar documents
    )
    
    retrieved_docs = await retriever.ainvoke(query)
    
    return retrieved_docs

def get_placeholder_chain():
    """
    Returns a simple, placeholder Langchain chain.
    
    This chain takes a query, passes it through, and formats a basic response.
    """
    prompt = ChatPromptTemplate.from_template("Received query: {query} - Langchain placeholder response.")
    
    # Using a simple chain with a passthrough for the query
    chain = {"query": RunnablePassthrough()} | prompt
    
    return chain
