import os
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "KubeOps-Aegis Autonomous SRE Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # LLM Settings
    LLM_PROVIDER: Literal["openai", "gemini", "anthropic", "ollama", "mock"] = "mock"
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.1
    
    # Kubernetes Settings
    KUBE_IN_CLUSTER: bool = False
    KUBECONFIG_PATH: Optional[str] = None
    MOCK_K8S: bool = True  # Allows offline / demo execution out of the box
    
    # Prometheus Settings
    PROMETHEUS_URL: str = "http://localhost:9090"
    
    # GitOps & ArgoCD Settings
    GITOPS_REPO_PATH: str = "./gitops"
    GITOPS_REPO_URL: Optional[str] = "https://github.com/Sundeep-Hiremat/cloudnative-ai-ops"
    GITHUB_TOKEN: Optional[str] = None
    TARGET_BRANCH: str = "main"
    AUTO_APPROVE_PR: bool = False
    
    # Human in the Loop (HITL)
    ENABLE_HITL: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
