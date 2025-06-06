import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from pymongo import MongoClient

# Constants
# Ensure GOOGLE_API_KEY is loaded for ChatGoogleGenerativeAI
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable not set!")
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

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20", temperature=0.7)

# Define the RAG prompt template
RAG_PROMPT_TEMPLATE = """
You are an assistant for question-answering tasks. Use the following pieces of retrieved context to augment your answer the question.
If you don't know the answer, just say that you don't know. Keep the answer concise.

Question: {question}
Context: {context}

Answer:
"""

rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

async def get_rag_chain():
    """
    Constructs and returns an asynchronous RAG chain.
    The chain retrieves documents, formats them with the query,
    passes to the LLM, and parses the output.
    """
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 20} # Retrieve top 3 most similar documents
    )

    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)
    
    # The final chain will take a query string and return a dict 
    # containing the "answer" and the "context" (source documents)
    return rag_chain_with_source
