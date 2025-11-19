# conv2text/llm/llm_client.py
from __future__ import annotations
import os
import json
import requests
from typing import List, Dict, Optional

from dotenv import load_dotenv
load_dotenv()


def _normalize_base_url(base: Optional[str]) -> str:
    """
    Acepta:
      - None                        -> "https://api.openai.com"
      - "https://api.openai.com"    -> "https://api.openai.com"
      - "https://api.openai.com/v1" -> "https://api.openai.com"
      - "http://localhost:11434"    -> "http://localhost:11434"
      - "http://localhost:11434/v1" -> "http://localhost:11434"
    """
    if not base or base.strip() == "":
        return "https://api.openai.com"
    base = base.strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base

def _normalize_model_name(name: str | None) -> str:
    if not name or name.strip() == "":
        return "gpt-4o-mini"
    name = name.strip()
    # Permite prefijos tipo "openai/<model>"
    return name.split("openai/", 1)[-1] if name.startswith("openai/") else name

class LLMClient:
    """
    Cliente OpenAI-compatible (/v1/chat/completions) con tolerancia a base URLs y auth opcional.
    Variables de entorno:
      - OPENAI_API_BASE (opcional; ej: https://api.openai.com o http://localhost:11434)
      - OPENAI_API_KEY  (si el servidor requiere auth)
      - MODEL_CONV2TEXT / MODEL_TRIPLETAS_CYPHER / MODEL_KG_GEN (cualquier orden de preferencia)
    """
    def __init__(
        self,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
    ):
        env_base = os.getenv("OPENAI_API_BASE")
        env_key = os.getenv("OPENAI_API_KEY")
        env_model = (
            os.getenv("MODEL_CONV2TEXT")
            or os.getenv("MODEL_TRIPLETAS_CYPHER")
            or os.getenv("MODEL_KG_GEN")
        )

        self.base = _normalize_base_url(api_base or env_base)
        self.api_key = api_key or env_key
        self.model = _normalize_model_name(model or env_model or "gpt-4o-mini")
        self.timeout = timeout

        self.endpoint = f"{self.base}/v1/chat/completions"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.0) -> str:
        headers = {"Content-Type": "application/json"}
        # Solo añade Authorization si hay key
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        try:
            resp = requests.post(self.endpoint, headers=headers, data=json.dumps(payload), timeout=self.timeout)
            # Si hay error, muestra el cuerpo para depurar (401, 404, etc.)
            if resp.status_code >= 400:
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = resp.text
                raise RuntimeError(
                    f"[LLM] HTTP {resp.status_code} en {self.endpoint}\n"
                    f"Base: {self.base}\nModelo: {self.model}\n"
                    f"Detalle: {err_body}"
                )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"[LLM] Error en chat: {e}")
