import os 
import logfire
from dotenv import load_dotenv

load_dotenv()
logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))

from fastapi import FastAPI
from fastapi.responses import Response
from app.agents.graph import rag_agent

from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Enterprise Agentic AI RAG")

class QueryRequest(BaseModel):
    q: str
    thread_id: Optional[str] = "default_user"

@app.get("/")
def home():
    return {"message": "Enterprise RAG is Live"}

@app.get("/graph")
def get_graph_image():
    """
    Return the Mermaid of the agent's workflow
    """
    try:
        png_bytes = rag_agent.get_graph().draw_mermaid_png()
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        return {"error": f"Failed to Generate Graph: {e}"}

@app.post("/query")
def query(request: QueryRequest):
    """
    Execute the LangGraph RAG with the POST request
    """
    q = request.q
    thread_id = request.thread_id

    initial_state = {
        "messages": [{"role": "user", "content": q}],
        "current_query": q,
        "documents": [],
        "plan": ["Start"],
        "status": "Initializing Graph..."
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        final_output = rag_agent(initial_state, config=config)

        return {
            "question": q,
            "answer": final_output.get("final_answer"),
            "thought_process": final_output.get("plan"),
            "status": final_output.get("status"),
            "source": final_output.get("documents", [])
        }

    except Exception as e:
        logfire.error(f"Executing Backend Fails: {e}")
        return {
            "question": q,
            "answer": "I apologize, there is an internal error while processing your request, Please try later",
            "though_process": ["Encountered error during execution"],
            "status": "error",
            "source": []
        }