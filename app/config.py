"""Configuration management using pydantic-settings."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environment
    env: str = Field(default="dev", alias="ENV")
    seed: int = Field(default=42, alias="SEED")

    # Auth
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

    # Stores
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    sqlite_url: str = Field(default="sqlite:///./data/permrag.db", alias="SQLITE_URL")

    # Embeddings
    embed_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBED_MODEL")

    # LLM Settings
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")

    # Provider-specific configurations
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="qwen/qwen3.8-27b", alias="GROQ_MODEL")

    glm_api_key: str = Field(default="", alias="GLM_API_KEY")
    glm_model: str = Field(default="glm-4-flash", alias="GLM_MODEL")

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="meta-llama/llama-3.3-70b-instruct:free", alias="OPENROUTER_MODEL")

    # SSL verification (set to False to bypass corporate/antivirus untrusted root certificates)
    ssl_verify: bool = Field(default=False, alias="SSL_VERIFY")

    @property
    def effective_model(self) -> str:
        """Resolve the active model name based on provider and explicit overrides."""
        if self.llm_model:
            return self.llm_model
        provider = self.llm_provider.lower().strip()
        if provider == "groq":
            return self.groq_model
        elif provider in ("glm", "zhipu"):
            return self.glm_model
        elif provider == "openrouter":
            return self.openrouter_model
        return self.llm_model or "default"

    @property
    def effective_api_key(self) -> str:
        """Resolve the active API key based on provider and explicit overrides."""
        if self.llm_api_key:
            return self.llm_api_key
        provider = self.llm_provider.lower().strip()
        if provider == "groq":
            return self.groq_api_key
        elif provider in ("glm", "zhipu"):
            return self.glm_api_key
        elif provider == "openrouter":
            return self.openrouter_api_key
        return ""

    # Retrieval
    dense_top_k: int = Field(default=30, alias="DENSE_TOP_K")
    rerank_top_k: int = Field(default=6, alias="RERANK_TOP_K")
    max_context_tokens: int = Field(default=3000, alias="MAX_CONTEXT_TOKENS")
    rerank_min_score: float = Field(default=0.0, alias="RERANK_MIN_SCORE")

    def validate_prod(self) -> None:
        """Ensure production environment has secure settings."""
        if self.env == "prod":
            if self.jwt_secret == "change-me-to-a-secure-32-byte-minimum-secret-key":
                raise ValueError("JWT_SECRET must be changed in production")


settings = Settings()
settings.validate_prod()
