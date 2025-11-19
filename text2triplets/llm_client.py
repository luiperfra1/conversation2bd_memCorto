# llm_client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
import os

def _normalize_model_name(name: str) -> str:
    # Permite valores tipo "openai/qwen2.5:14b" o "qwen2.5:14b"
    return name.split("openai/", 1)[-1] if name.startswith("openai/") else name

def _normalize_base_url(base: Optional[str]) -> str:
    """
    Acepta valores como:
      - None                       -> "https://api.openai.com"
      - "https://api.openai.com"   -> "https://api.openai.com"
      - "http://localhost:11434"   -> "http://localhost:11434"
      - "http://localhost:11434/v1"-> "http://localhost:11434"
    y devuelve la base SIN /v1 final, para que el cliente añada /v1/chat/completions.
    """
    if not base or base.strip() == "":
        return "https://api.openai.com"
    base = base.strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]  # quita el sufijo /v1
    return base


@dataclass(frozen=True)
class LLMConfig:
    api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    base_url: Optional[str] = os.getenv("OPENAI_API_BASE")  # opcional
    model: str = os.getenv("MODEL_KG_GEN", "") or "gpt-4o-mini"  # valor por defecto razonable
    temperature: float = 0.0
    timeout: int = 60  # segundos


class LLMClient:
    """
    Cliente mínimo para endpoints OpenAI-compatibles (no requiere el SDK oficial).
    Usa /v1/chat/completions.
    """

    def __init__(self, cfg: LLMConfig | None = None) -> None:
        self.cfg = cfg or LLMConfig()
        self.base_url = _normalize_base_url(self.cfg.base_url)
        self.endpoint = f"{self.base_url}/v1/chat/completions"

        if not self.cfg.api_key:
            # Muchos servidores "compatibles" (p.ej. Ollama local) ignoran el API key,
            # pero mantenemos el check con mensaje claro.
            # Si necesitas permitir vacío sin warning, comenta esta línea.
            print("[llm_client] Aviso: OPENAI_API_KEY no está definido; si tu servidor no lo requiere, ignora este aviso.")

    

    def chat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> str:
        model_name = _normalize_model_name(self.cfg.model)
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": self.cfg.temperature if temperature is None else temperature,
            "stream": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.cfg.api_key or 'none'}",
        }
        try:
            resp = requests.post(self.endpoint, json=payload, headers=headers, timeout=self.cfg.timeout)
            resp.raise_for_status()
            data = resp.json()
            # Formato OpenAI: choices[0].message.content
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if not isinstance(content, str):
                content = str(content)
            return content
        except Exception as e:
            raise RuntimeError(f"[llm_client] Error en chat: {e}")

    # API equivalente a tu KGGen.generate() para no tocar más llamadas en tu código
    def generate(self, *, input_data: str, context: str) -> str:
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": input_data},
        ]
        return self.chat(messages)
