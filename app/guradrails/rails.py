import logfire
from langchain_groq import ChatGroq
from nemoguardrails import RailsConfig, LLMRails

from app.config import settings
from app.guradrails.colang_rules import (
    COLANG_CONTENT,
    YAML_CONTENT,
    TECHNICAL_KEYWORDS,
    DEFAULT_REFUSAL_MESSAGE,
    DIALOG_RAIL_FLOW_NAMES,
)

_rails: LLMRails | None = None

def initialize_rails() -> None:
    global _rails

    guard_llm = ChatGroq(
        api_key=settings.GROQ_FALLBACK_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0
    )

    config = RailsConfig.from_content(
        colang_content=COLANG_CONTENT,
        yaml_content=YAML_CONTENT
    )

    _rails = LLMRails(config, llm=guard_llm)
    logfire.info("🛡️ NeMo Guardrails initialised (llama-3.1-8b-instant).")

def guard(message: str) -> tuple[bool, str | None]:
    if _rails is None:
        logfire.warning("⚠️ Guardrails not initialised — skipping gate.")
        return False, None

    with logfire.span("🛡️ Guardrails Check"):
        res = _rails.generate(
            messages=[{"role": "user", "content": message}],
            options={"log": {"activated_rails": True}},
        )

        # messages-based generate() returns res.response as a list of message dicts
        response = res.response
        if isinstance(response, list) and response:
            content = response[-1].get("content", "")
        else:
            content = str(response)

        activated_names = {rail.name for rail in (res.log.activated_rails if res.log else [])}
        matched_flow = activated_names & DIALOG_RAIL_FLOW_NAMES

        if matched_flow:
            logfire.info(f"🛡️ Guardrails fired | flow={matched_flow} | query='{message[:80]}'")
            return True, content

        # No canonical Colang flow matched (jailbreak/greeting/capabilities/farewell/off-topic
        # examples) — fall back to a deterministic keyword gate so unseen off-topic phrasings
        # don't silently leak through to the RAG agent.
        if not any(keyword in message.lower() for keyword in TECHNICAL_KEYWORDS):
            logfire.info(f"🛡️ Guardrails fired | keyword gate | query='{message[:80]}'")
            return True, DEFAULT_REFUSAL_MESSAGE

        logfire.info("✅ Guardrails passed.")
        return False, None