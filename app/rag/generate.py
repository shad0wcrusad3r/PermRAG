"""LLM generation with retries and fallback."""
import logging
from typing import Dict, Any
import httpx
from openai import OpenAI, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

# Inject system root certificates so Windows corporate/antivirus/proxy certs are trusted
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass


class LLMClient:
    """LLM client with multi-provider support and SSL resilience."""

    def __init__(self):
        self.provider = settings.llm_provider.lower().strip()
        self.model = settings.effective_model
        api_key = settings.effective_api_key

        if self.provider == "groq":
            if not api_key:
                raise ValueError("GROQ_API_KEY is required for groq provider")
            base_url = settings.llm_base_url or "https://api.groq.com/openai/v1"
        elif self.provider in ("glm", "zhipu"):
            if not api_key:
                raise ValueError("GLM_API_KEY is required for GLM/Zhipu provider")
            base_url = settings.llm_base_url or "https://open.bigmodel.cn/api/paas/v4"
        elif self.provider == "openrouter":
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY is required for OpenRouter provider")
            base_url = settings.llm_base_url or "https://openrouter.ai/api/v1"
        elif self.provider == "siliconflow":
            if not api_key:
                raise ValueError("LLM_API_KEY is required for SiliconFlow provider")
            base_url = settings.llm_base_url or "https://api.siliconflow.cn/v1"
        elif self.provider == "ollama":
            base_url = settings.llm_base_url or "http://localhost:11434/v1"
            api_key = api_key or "ollama"
        elif self.provider in ("openai", "custom"):
            base_url = settings.llm_base_url or "https://api.openai.com/v1"
            if not api_key:
                raise ValueError("LLM_API_KEY is required for custom/openai provider")
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

        self.base_url = base_url
        self.api_key = api_key
        self._init_client(verify=settings.ssl_verify)

    def _init_client(self, verify: bool = True):
        http_client = httpx.Client(
            verify=verify,
            timeout=httpx.Timeout(60.0, connect=15.0),
        )
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((Exception,))
    )
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate completion with retries and automatic SSL fallback."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=500,
            )
            return response.choices[0].message.content
        except APIConnectionError as e:
            # If an SSL certificate trust failure occurred, auto-fallback to unverified client
            err_msg = str(e).lower()
            if "certificate" in err_msg or "trust provider" in err_msg or "connect" in err_msg:
                logger.warning("SSL/Connection failure detected (%s). Retrying with verify=False fallback...", e)
                self._init_client(verify=False)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0,
                    max_tokens=500,
                )
                return response.choices[0].message.content
            raise


# Global singleton
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
