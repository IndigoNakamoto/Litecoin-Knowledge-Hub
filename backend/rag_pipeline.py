import os
import asyncio
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from pymongo import MongoClient
from typing import List, Tuple, Dict, Any
from langchain_core.documents import Document
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain # Corrected import path
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# --- Environment Variable Checks ---
# Ensure GOOGLE_API_KEY is loaded. This check is critical.
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set!")

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set!")

# --- Constants ---
DB_NAME = os.getenv("MONGO_DB_NAME", "litecoin_rag_db")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "litecoin_docs")
INDEX_NAME = os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index") # Default to 'vector_index'
EMBEDDING_MODEL_NAME = "models/text-embedding-004"
LLM_MODEL_NAME = "gemini-1.5-flash-latest" # Updated to a common model, was gemini-2.5-flash-preview-05-20

# --- RAG Prompt Templates ---
# 1. History-aware question rephrasing prompt
QA_WITH_HISTORY_PROMPT = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("human", "Given the above conversation, generate a standalone question to address the user's input. If the input is already a standalone question, return it as is."),
    ]
)

# 2. RAG prompt for final answer generation
RAG_PROMPT_TEMPLATE = """
You are a helpful expert on cryptocurrency. Answer the user's question based *only* on the provided context. If the context does not contain the answer, say so.

**Context:**
---
{context}
---

**User Question:** {input}

**Answer:**
"""
rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

def format_docs(docs: List[Document]) -> str:
    """Helper function to format a list of documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)

class RAGPipeline:
    """
    Encapsulates the Retrieval-Augmented Generation pipeline.
    """
    def __init__(self, vector_store_manager=None, db_name=None, collection_name=None):
        """
        Initializes the RAGPipeline.

        Args:
            vector_store_manager: An instance of VectorStoreManager. If provided, it's used.
                                  Otherwise, a new MongoDBAtlasVectorSearch instance is created.
            db_name: Name of the database. Defaults to MONGO_DB_NAME env var or "litecoin_rag_db".
            collection_name: Name of the collection. Defaults to MONGO_COLLECTION_NAME env var or "litecoin_docs".
        """
        self.db_name = db_name or DB_NAME
        self.collection_name = collection_name or COLLECTION_NAME
        
        # Initialize Embeddings for queries
        # Reason: Setting task_type to 'retrieval_query' for embedding user queries.
        self.query_embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            task_type="retrieval_query",
            google_api_key=google_api_key
        )

        if vector_store_manager:
            # If a VectorStoreManager instance is passed (e.g., from the test with a specific test collection)
            self.vector_store = vector_store_manager.vector_store # Use its underlying Langchain vector store
            print(f"RAGPipeline using provided VectorStoreManager for collection: {vector_store_manager.collection_name}")
        else:
            # Default initialization for production or general use
            mongo_client = MongoClient(MONGO_URI)
            db = mongo_client[self.db_name]
            collection = db[self.collection_name]
            self.vector_store = MongoDBAtlasVectorSearch(
                collection=collection,
                embedding=self.query_embeddings, # Used by retriever for query embedding if not overridden
                index_name=INDEX_NAME
            )
            print(f"RAGPipeline initialized default VectorStore for collection: {self.collection_name}")

        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(model=LLM_MODEL_NAME, temperature=0.7, google_api_key=google_api_key)

        # Construct the RAG chain
        self._setup_rag_chain()

    def _setup_rag_chain(self):
        """Sets up the main RAG chain with conversational history."""
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 10} # Retrieve top 5 documents for context
        )

        # 1. Create a history-aware retriever
        # This chain takes the chat history and the new question, and rephrases the question
        # to be standalone if necessary.
        history_aware_retriever = create_history_aware_retriever(
            self.llm, retriever, QA_WITH_HISTORY_PROMPT
        )

        # 2. Create the document combining chain
        # This chain takes the retrieved documents and the user's question,
        # formats them, and passes them to the LLM for final answer generation.
        document_chain = create_stuff_documents_chain(self.llm, rag_prompt)

        # 3. Create the full retrieval chain
        # This chain combines the history-aware retriever with the document combining chain.
        self.rag_chain = create_retrieval_chain(history_aware_retriever, document_chain)

    def query(self, query_text: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Document]]:
        """
        Processes a query through the RAG pipeline with conversational history.

        Args:
            query_text: The user's current query.
            chat_history: A list of (human_message, ai_message) tuples representing the conversation history.

        Returns:
            A tuple containing the generated answer (str) and a list of source documents (List[Document]).
        """
        # Convert chat_history to Langchain's BaseMessage format
        converted_chat_history: List[BaseMessage] = []
        for human_msg, ai_msg in chat_history:
            converted_chat_history.append(HumanMessage(content=human_msg))
            converted_chat_history.append(AIMessage(content=ai_msg))

        try:
            # Invoke the new rag_chain with input and chat history
            result = self.rag_chain.invoke(
                {"input": query_text, "chat_history": converted_chat_history}
            )
            
            answer = result.get("answer", "Error: Could not generate answer.")
            # The 'context' key from the retriever is now directly available in the result
            sources = result.get("context", []) 
            return answer, sources
        except Exception as e:
            print(f"Error during RAG query execution: {e}")
            return f"Error processing query: {e}", []

# --- Standalone functions (can be removed or kept for other uses if RAGPipeline class is primary) ---

async def retrieve_documents(query: str, vector_store_instance: MongoDBAtlasVectorSearch) -> List[Document]:
    """
    Retrieves documents from a given MongoDB Atlas Vector Search instance.
    """
    retriever = vector_store_instance.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10} 
    )
    retrieved_docs = await retriever.ainvoke(query)
    return retrieved_docs

async def get_rag_chain_async(vector_store_instance: MongoDBAtlasVectorSearch, llm_instance: ChatGoogleGenerativeAI):
    """
    Constructs and returns an asynchronous RAG chain using provided instances.
    """
    retriever = vector_store_instance.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10} 
    )
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | rag_prompt
        | llm_instance
        | StrOutputParser()
    )
    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)
    return rag_chain_with_source


# Example of how to use the RAGPipeline class (for testing or direct script use)
if __name__ == "__main__":
    # This ensures .env is loaded if running this script directly
    from dotenv import load_dotenv
    dotenv_path_actual = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path_actual):
        print(f"RAGPipeline direct run: Loading .env from {dotenv_path_actual}")
        load_dotenv(dotenv_path=dotenv_path_actual, override=True)
    else:
        print("RAGPipeline direct run: .env file not found. Ensure GOOGLE_API_KEY and MONGO_URI are set.")

    print("Testing RAGPipeline class with conversational history...")
    try:
        pipeline = RAGPipeline() # Uses default collection

        # Test 1: Initial query
        initial_query = "What is Litecoin?"
        print(f"\nQuerying pipeline with: '{initial_query}' (initial query)")
        answer, sources = pipeline.query(initial_query, chat_history=[])
        print("\n--- Answer (Initial Query) ---")
        print(answer)
        print("\n--- Sources (Initial Query) ---")
        if sources:
            for i, doc in enumerate(sources):
                print(f"Source {i+1}: {doc.page_content[:150]}... (Metadata: {doc.metadata.get('title', 'N/A')})")
        else:
            print("No sources retrieved.")

        # Test 2: Follow-up query with history
        follow_up_query = "Who created it?"
        # Assuming the AI's previous answer was 'Litecoin was created by Charlie Lee.'
        # For testing purposes, we'll simulate a simple history.
        simulated_history = [
            ("What is Litecoin?", "Litecoin is a peer-to-peer cryptocurrency and open-source software project released under the MIT/X11 license. It was inspired by Bitcoin but designed to have a faster block generation rate and use a different hashing algorithm.")
        ]
        print(f"\nQuerying pipeline with: '{follow_up_query}' (follow-up query)")
        answer, sources = pipeline.query(follow_up_query, chat_history=simulated_history)
        
        print("\n--- Answer (Follow-up Query) ---")
        print(answer)
        print("\n--- Sources (Follow-up Query) ---")
        if sources:
            for i, doc in enumerate(sources):
                print(f"Source {i+1}: {doc.page_content[:150]}... (Metadata: {doc.metadata.get('title', 'N/A')})")
        else:
            print("No sources retrieved.")
            
    except ValueError as ve:
        print(f"Initialization Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")
