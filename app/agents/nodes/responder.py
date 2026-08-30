import logfire
from app.config import settings
from langchain_groq import ChatGroq
from app.agents.state import AgentState

llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model=settings.GROQ_MODEL
)

def generate_node(state: AgentState):
    """
    Synthesize a response useing both Documentation context AND Conversational History.
    """
    query = state["current_query"]

    history_str = ""
    for msg in state["messages"][:-1]:
        role = "user" if state["role"] == "user" else "Assistant"
        history_str += f"{role}: {state["content"]}\n"

        user_msg = state["messages"][-1]["content"] if state["messages"] else ""

        if query == "CONVERSATIONAL":
            logfire.info("Generating conversational response using memoery")
            prompt = f"""
            You are a helpful friendly and Enterprise AI Assistant.
            Answer the user's latest message using the CONVERSATIONAL HISTORY below.

            CONVERSATIONAL HISTORY:
            {history_str}

            LATEST MESSAGE:
            "{user_msg}"
            """
        else:
            logfire.ingo("Generating Technical RAG response")
            max_content_cahrs = 25000
            full_context = ""

            for doc in state["documents"]:
                if len(full_context) + len(doc) < max_content_cahrs:
                    full_context += doc + "\n\n"
                else:
                    logfire.warning("Could not truncate to GROQ TPM limits")
                    break

            prompt= f"""
            You are a Senior Technical Architect.
            Answer the question usign the TECHNICAL CONTEXT provided.

            TECHNICAL CONTEXT: 
            {full_context}

            CONVERSATIONAL HISTORY:
            {history_str}

            USER QUESTION:
            "{user_msg}"
            """
        with logfire.span("LLM Synthesis"):
            try:
                content = llm.invoke(prompt).content
                logfire.ingo("Response Synthesise by LLM")

                return {
                    "final_answer": content,
                    "status": "Response generated",
                    "plan": state["plan"],
                    "message": [{"role": "assistant", "content": content}]
                }

            except Exception as e:
                logfire.error(f"LLM Generation Failed: {e}")
                raise e