from __future__ import annotations
from typing import List, Dict, Any

import os
import json
import requests

try:
    # Cliente oficial OpenAI v1
    from openai import OpenAI
except ImportError:
    OpenAI = None  # se manejará en runtime

from utils.config import settings


Message = Dict[str, str]  # {"role": "...", "content": "..."}


class ConvClient:
    """
    Cliente mínimo para conversación:
    - backend="OPENAI": usa API OpenAI-compatible (LlamUS, local...)
    - backend="OLLAMA": llama al endpoint OLLAMA_URL (/api/chat)
    """

    def __init__(self, model: str | None = None) -> None:
        self.backend = settings.LLAMUS_BACKEND
        self.model = model or settings.MODEL_CONV

        if self.backend == "OPENAI":
            if OpenAI is None:
                raise RuntimeError(
                    "El paquete 'openai' no está instalado. "
                    "Instala con: pip install openai"
                )
            self.client = OpenAI(
                base_url=settings.OPENAI_API_BASE,
                api_key=settings.OPENAI_API_KEY,
            )
        elif self.backend == "OLLAMA":
            if not settings.OLLAMA_URL:
                raise ValueError("OLLAMA_URL no está definido en el entorno.")
            self.client = None  # usamos requests
        else:
            raise ValueError(f"Backend LLM no soportado: {self.backend}")

    # --------------------------------------
    # Interfaz pública
    # --------------------------------------
    def chat(self, messages: List[Message]) -> str:
        """
        Envía una lista de mensajes estilo OpenAI:
        [
          {"role": "system", "content": "..."},
          {"role": "user", "content": "..."},
          {"role": "assistant", "content": "..."},
          ...
        ]
        y devuelve SOLO el texto de la respuesta del assistant.
        """
        if self.backend == "OPENAI":
            return self._chat_openai(messages)
        elif self.backend == "OLLAMA":
            return self._chat_ollama(messages)
        else:
            raise RuntimeError("Backend no configurado correctamente.")

    # --------------------------------------
    # Implementaciones internas
    # --------------------------------------
    def _chat_openai(self, messages: List[Message]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,  # puedes tunearlo luego
        )
        return resp.choices[0].message.content

    def _chat_ollama(self, messages: List[Message]) -> str:
        # OLLAMA_URL típico: https://.../api/chat
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        r = requests.post(settings.ollama_url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()

        # Formato estándar de Ollama /api/chat:
        # { "message": {"role": "assistant", "content": "..."}, ... }
        if "message" in data and isinstance(data["message"], dict):
            return data["message"].get("content", "")

        # Por si tu adapter devuelve algo estilo OpenAI
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]

        # Si no reconocemos la respuesta, la devolvemos raw para debug
        return json.dumps(data, ensure_ascii=False, indent=2)
