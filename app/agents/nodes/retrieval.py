import logfire
from app.agents.state import AgentState
from app.services.retrieval.qdrant_service import search_enterprise_knowledge
from app.services.retrieval.ranking_service import rank_documents

def retrieval_node(state: AgentState):
    """
    Perform vector search and Semantic reranking for the Technical query.
    """
    query = state["current_query"]

    with logfire.span("Knowledge Retrieval"):
        logfire.ingo(f"Searching Qdrant for {query}")
        raw_result = search_enterprise_knowledge(query=query, limit=15)
        logfire.info(f"Fetched {len(raw_result)} candidates from vector DB")

        doc_content = [doc["content"] for doc in raw_result]

        with logfire.span("Semantic Reranking"):
            ranked_content = rank_documents(query, doc_content, top_no=5)
            logfire.info("Reranking completed, kept top 5 most relevant chunk")

        formatted_doc = [f"CONTENT: {doc}" for doc in ranked_content]

    return {
        "documents": formatted_doc,
        "status": f"Found Technial context",
        "plan": state["plan"] + ["Context Retrieved"]
    }