import logfire
from langchain_groq import ChatGroq
from nemoguardrails import RailsConfig, LLMRails

from app.config import settings
from app.guradrails.colang_rules import COLANG_CONTENT, YAML_CONTENT, RAIL_INDICATORS

_rails: LLMRails | None = None

def initialize_rails() -> None:
    global _rails

    guard_rails = ChatGroq(
        api_key=settings.GROQ_FALLBACK_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0
    )

    config = RailsConfig.from_content(
        colang_content=COLANG_CONTENT,
        yaml_content=YAML_CONTENT
    )

    _rails = LLMRails(config, llm=guard_rails)
    logfire.info(f"NeMo Guardrails Initialized {settings.GROQ_MODEL}")

def guard(message: str) -> tuple[bool, str | None]:
    if _rails is None:
        logfire.warning("Guardrails not Initailized, skipping gate")
        return False, None

    with logfire.span("Guardrails Check"):
        result = _rails.generate(messages=[{"role": "user", "content": message}])

        content = result.get("content", "") if isinstance(result, dict) else str(result)
        fired = any(indicator in content for indicator in RAIL_INDICATORS)

        if fired:
            logfire.info(f"Guardrails fired | query {message[:80]}")
            return True, content

        logfire.info("Guardrails passed")
        return False, None