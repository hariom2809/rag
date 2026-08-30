from app.agents.state import AgentState
from app.config import settings
from langchain_groq import ChatGroq
import logfire


llm  = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model=settings.GROQ_MODEL
)


def planner_node(state: AgentState):
    """
    Planner node Determines whether the search is needed based on ENTIRE conversation
    """
    history = ""
    for msg in state["messages"][:-1]:
        role = "user" if msg["role"] == "user" else "Assistant"
        history += f"{role}: {msg['content']}\n"

    user_message = state["messages"][-1]["content"] if state["messages"] else ""

    prompt = f"""
    You are an Intelligent Assistant Planner.
    Analyze the conversation history and latest user message.

    CONVERSATION HISTORY:
    {history}

    LATEST USER MESSAGE:
    "{user_message}"

    TASK:
    1. If the latest message is a greeting (hi, hello) or a question that cna be answered using ONLY the conversation history about (e.g. What is my name), respond this with 'CONVERSATIONAL'.
    2. If it is a technical question about Kubernetes, Intel, or Networking that require fresh documentation, output a refered search query.

    output only 'CONVERSATIONAL' or the search query.
    """

    with logfire.span("Planner Descision"):
        descision = llm.invoke(prompt).content.strip()
        logfire.info(f"Intent Identified: {descision}")

    if descision == "CONVERSATIONAL":
        return {
            "current_query": "CONVERSATIONAL",
            "status": "Handling conversationally (using history)...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: skipped"]
        }

    return {
        "current_query": descision,
        "status": f"Technical search needed, searching for {descision}",
        "plan": ["Intent: Technical", f"Search for Term: {descision}"]
    }