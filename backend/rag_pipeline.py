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
        search_kwargs={"k": 10}  # Retrieve top 5 most similar documents
    )
    retrieved_docs = await retriever.ainvoke(query)
    return retrieved_docs

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20", temperature=0.7)

# Define the RAG prompt template
RAG_PROMPT_TEMPLATE = """
### ROLE & OBJECTIVE ###
You are a specialized AI analyst for the Litecoin protocol, functioning as a precise information extraction and synthesis engine. Your primary objective is to provide accurate, factual answers based exclusively on the provided `CONTEXT`. You must operate with a neutral, objective tone and never use information outside of the provided text.

### INSTRUCTIONS ###
You must follow this process to construct your answer:
1.  **Analyze and Synthesize:** Carefully analyze the user's `QUESTION` and synthesize a direct and concise answer using *only* the information found in the `CONTEXT`.
2.  **Strict Grounding:** Ensure every claim in your answer is directly supported by the provided `CONTEXT`. Do not add information, make assumptions, or use any prior knowledge.
3.  **Handle Insufficient Information:** If the `CONTEXT` does not contain the necessary information to answer the `QUESTION`, you must state: "Based on the provided context, I cannot answer this question." Do not attempt to guess.
4.  **Acknowledge Conflicts:** If the `CONTEXT` contains conflicting information, present the different points and explicitly state that the sources are in disagreement.
5.  **Provide Confidence and Justification:** After the answer, you must assess your confidence in the answer's completeness and accuracy based on the provided `CONTEXT`.

---

### INPUT ###

**CONTEXT:**
{context}

**QUESTION:**
{question}

---

### OUTPUT ###

**Answer:**
[Your synthesized answer based ONLY on the context. Adhere to the instructions above.]

**Confidence Score:** [High, Medium, or Low]

**Justification:**
[Explain your confidence score.
- **High:** The answer is explicitly and comprehensively stated in the context.
- **Medium:** The answer is inferred by combining multiple pieces of the context, but not stated directly.
- **Low:** The context is related to the question but is incomplete, ambiguous, or provides only partial information.]
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
