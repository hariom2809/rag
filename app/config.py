import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Gemini
    GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY")

    # Qdrant
    QDRANT_URL          = os.getenv("QDRANT_CLUSTER_ENDPOINT")
    QDRANT_API_KEY      = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION   = "enterprise-rag"

    # Groq
    GROQ_API_KEY            = os.getenv("GROQ_API_KEY")
    GROQ_FALLBACK_API_KEY   = os.getenv("GROQ_FALLBACK_API_KEY")
    GROQ_MODEL              = os.getenv("GROQ_MODEL")

settings = Settings()