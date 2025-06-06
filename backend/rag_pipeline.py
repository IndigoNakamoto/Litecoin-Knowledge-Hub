from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

def get_placeholder_chain():
    """
    Returns a simple, placeholder Langchain chain.
    
    This chain takes a query, passes it through, and formats a basic response.
    """
    prompt = ChatPromptTemplate.from_template("Received query: {query} - Langchain placeholder response.")
    
    # Using a simple chain with a passthrough for the query
    chain = {"query": RunnablePassthrough()} | prompt
    
    return chain
