"""Multi-Provider AI Runtime reading API keys from .env."""
import json, os, re, time
from typing import Any, Dict, List, Optional
try:
    import requests
except ImportError:
    requests = None

from ingestion.config import load_dotenv_file, resolve_agent_endpoints, ProviderEndpoint
from ingestion.models import AIResponse

class AIRuntime:
    def __init__(self, env_path: str = ".env") -> None:
        load_dotenv_file(env_path=env_path, override=False)
        self.timeout_sec = float(os.environ.get("AGRIAGENT_LLM_TIMEOUT_SEC", "30"))
        self.max_retries = int(os.environ.get("AGRIAGENT_LLM_MAX_RETRIES", "2"))

    @staticmethod
    def _extract_json_payload(text: str) -> Any:
        cleaned = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fence:
            cleaned = fence.group(1).strip()
        return json.loads(cleaned)

    def _invoke_endpoint(self, endpoint: ProviderEndpoint, system_prompt: str, user_prompt: str) -> AIResponse:
        if requests is None:
            raise RuntimeError("The 'requests' library is required for AI API calls.")
        url = f"{endpoint.base_url}/chat/completions"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if endpoint.api_key:
            headers["Authorization"] = f"Bearer {endpoint.api_key}"
        if endpoint.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/kunj3690/agriagent-assam"
            headers["X-Title"] = "AgriAgent-Assam"
        body = {
            "model": endpoint.model,
            "temperature": 0.0,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        }
        last_err: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=self.timeout_sec)
                latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(min(2.0 ** attempt, 4.0))
                    last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    continue
                resp.raise_for_status()
                payload = resp.json()
                content = payload["choices"][0]["message"]["content"]
                tokens = int(payload.get("usage", {}).get("total_tokens", 0))
                return AIResponse(parsed_json=self._extract_json_payload(content), raw_text=content, provider=endpoint.provider, model_id=endpoint.model, tokens_used=tokens, latency_ms=latency_ms, used_fallback=False)
            except Exception as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                if attempt < self.max_retries:
                    time.sleep(min(2.0 ** attempt, 4.0))
        raise RuntimeError(f"Provider '{endpoint.provider}' ({endpoint.model}) failed: {last_err}")

    def call_json(self, agent_name: str, system_prompt: str, user_prompt: str) -> AIResponse:
        endpoints = resolve_agent_endpoints(agent_name)
        if not endpoints:
            return AIResponse(parsed_json=None, raw_text="", provider="none", model_id="deterministic_fallback", tokens_used=0, latency_ms=0.0, used_fallback=True, error="No API keys configured in .env or environment.")
        errors: List[str] = []
        for ep in endpoints:
            try:
                return self._invoke_endpoint(ep, system_prompt, user_prompt)
            except Exception as exc:
                errors.append(str(exc))
        return AIResponse(parsed_json=None, raw_text="", provider="none", model_id="deterministic_fallback", tokens_used=0, latency_ms=0.0, used_fallback=True, error=" | ".join(errors))
