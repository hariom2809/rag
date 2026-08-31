from app.agents.state import AgentState
from app.config import settings
from langchain_groq import ChatGroq
import logfire


llm  = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model=settings.GROQ_MODEL,
    temperature=0
)


def planner_node(state: AgentState):
    """
    Planner node Determines whether the search is needed based on ENTIRE conversation
    """
    history = ""
    for msg in state["messages"][:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
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
    1. If the latest message is a greeting (hi, hello) or a question that can be answer using ONLY the conversation history above (e.g. What is my name), respond this with 'CONVERSATIONAL'.
    2. If it is a technical question about Kubernetes, Intel, or Networking that require fresh documentation, output a refined search query.

    output only 'CONVERSATIONAL' or the search query.
    """

    with logfire.span("Planner decision"):
        decision = llm.invoke(prompt).content.strip()
        logfire.info(f"Intent Identified: {decision}")

    if decision == "CONVERSATIONAL":
        return {
            "current_query": "CONVERSATIONAL",
            "status": "Handling conversationally (using history)...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: skipped"]
        }

    return {
        "current_query": decision,
        "status": f"Technical search needed, searching for {decision}",
        "plan": ["Intent: Technical", f"Search for Term: {decision}"]
    }