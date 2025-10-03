import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ats.db")
    default_llm_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")

settings = Settings()
