"""Zero-dependency .env loader and multi-provider API configuration resolver."""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

PROVIDER_DEFAULTS: Dict[str, Dict[str, str]] = {
    "groq": {"api_key_env": "GROQ_API_KEY", "base_url_env": "GROQ_BASE_URL", "default_base_url": "https://api.groq.com/openai/v1", "model_env": "GROQ_DEFAULT_MODEL", "default_model": "openai/gpt-oss-120b"},
    "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "base_url_env": "OPENROUTER_BASE_URL", "default_base_url": "https://openrouter.ai/api/v1", "model_env": "OPENROUTER_DEFAULT_MODEL", "default_model": "qwen/qwen-2.5-72b-instruct"},
    "gemini": {"api_key_env": "GEMINI_API_KEY", "base_url_env": "GEMINI_BASE_URL", "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model_env": "GEMINI_DEFAULT_MODEL", "default_model": "gemini-2.5-flash"},
    "openai": {"api_key_env": "OPENAI_API_KEY", "base_url_env": "OPENAI_BASE_URL", "default_base_url": "https://api.openai.com/v1", "model_env": "OPENAI_DEFAULT_MODEL", "default_model": "gpt-4o-mini"},
    "together": {"api_key_env": "TOGETHER_API_KEY", "base_url_env": "TOGETHER_BASE_URL", "default_base_url": "https://api.together.xyz/v1", "model_env": "TOGETHER_DEFAULT_MODEL", "default_model": "Qwen/Qwen2.5-72B-Instruct-Turbo"},
    "ollama": {"api_key_env": "OLLAMA_API_KEY", "base_url_env": "OLLAMA_BASE_URL", "default_base_url": "http://localhost:11434/v1", "model_env": "OLLAMA_DEFAULT_MODEL", "default_model": "qwen2.5:7b"},
    "custom": {"api_key_env": "AGRIAGENT_LLM_API_KEY", "base_url_env": "AGRIAGENT_LLM_API_URL", "default_base_url": "", "model_env": "AGRIAGENT_CUSTOM_MODEL", "default_model": "Qwen/Qwen2.5-7B-Instruct"},
}

AGENT_ENV_PREFIX: Dict[str, str] = {
    "agent1_classifier": "AGENT1",
    "agent2_ingestion": "AGENT2",
    "agent2b_live_gis": "AGENT2B",
    "agent3_task": "AGENT3",
}

def load_dotenv_file(env_path: str = ".env", override: bool = False) -> Dict[str, str]:
    loaded: Dict[str, str] = {}
    if not os.path.isfile(env_path):
        return loaded
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
                val = val[1:-1]
            if key and (override or key not in os.environ):
                os.environ[key] = val
                loaded[key] = val
    return loaded

@dataclass(frozen=True)
class ProviderEndpoint:
    provider: str
    base_url: str
    api_key: str
    model: str

def resolve_provider_endpoint(provider: str, model_override: Optional[str] = None) -> Optional[ProviderEndpoint]:
    p = provider.strip().lower()
    spec = PROVIDER_DEFAULTS.get(p)
    if not spec:
        return None
    base_url = os.environ.get(spec["base_url_env"], "").strip() or spec["default_base_url"]
    api_key = os.environ.get(spec["api_key_env"], "").strip()
    model = (model_override or "").strip() or os.environ.get(spec["model_env"], "").strip() or os.environ.get("AGRIAGENT_DEFAULT_MODEL", "").strip() or spec["default_model"]
    if p == "ollama":
        return ProviderEndpoint(provider=p, base_url=base_url.rstrip("/"), api_key=api_key or "ollama", model=model) if base_url else None
    if p == "custom":
        return ProviderEndpoint(provider=p, base_url=base_url.rstrip("/"), api_key=api_key, model=model) if base_url else None
    if not api_key or not base_url:
        return None
    return ProviderEndpoint(provider=p, base_url=base_url.rstrip("/"), api_key=api_key, model=model)

def resolve_agent_endpoints(agent_name: str) -> List[ProviderEndpoint]:
    prefix = AGENT_ENV_PREFIX.get(agent_name, "")
    agent_provider = os.environ.get(f"{prefix}_PROVIDER", "").strip().lower() if prefix else ""
    agent_model = os.environ.get(f"{prefix}_MODEL", "").strip() if prefix else ""
    primary = agent_provider or os.environ.get("AGRIAGENT_LLM_PROVIDER", "groq").strip().lower()
    failover = [p.strip().lower() for p in os.environ.get("AGRIAGENT_FAILOVER_PROVIDERS", "groq,openrouter,gemini,openai").split(",") if p.strip()]
    ordered = []
    for p in [primary] + failover:
        if p and p not in ordered:
            ordered.append(p)
    endpoints = []
    for idx, p in enumerate(ordered):
        ep = resolve_provider_endpoint(p, model_override=agent_model if (idx == 0 and agent_model) else None)
        if ep is not None:
            endpoints.append(ep)
    return endpoints
