import json
import logging
from typing import Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel
from agent.app.core.config import settings

logger = logging.getLogger("kubeops.llm")

def get_llm() -> Optional[BaseChatModel]:
    """Returns the configured LangChain ChatModel or None if in mock mode."""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=settings.LLM_TEMPERATURE,
            google_api_key=settings.GEMINI_API_KEY
        )
    elif provider == "anthropic":
        from langchain_community.chat_models import ChatAnthropic
        return ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            temperature=settings.LLM_TEMPERATURE,
            anthropic_api_key=settings.ANTHROPIC_API_KEY
        )
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE
        )
    else:
        logger.info("Using built-in Mock/Deterministic Intelligent LLM Engine for offline execution.")
        return None
