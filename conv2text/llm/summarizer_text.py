# conv2text/llm/summarizer_text.py
from __future__ import annotations
from typing import List, Dict
from .llm_client import LLMClient
from .prompts import *

def _build_messages(conversation_text: str, max_sentences: int = 10):
    user_prompt = (
        f"{build_instruction(max_sentences)}\n\n"
        f"--- CONVERSACIÓN ---\n{conversation_text.strip()}\n--- FIN ---"
    )
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

class LLMTextSummarizer:
    """
    Devuelve únicamente el texto-resumen final en frases breves con sujeto explícito.
    """
    def __init__(self, client: LLMClient | None = None, temperature: float = 0.0):
        self.client = client or LLMClient()
        self.temperature = temperature

    def run(self, conversation_text: str) -> str:
        messages = _build_messages(conversation_text)
        return self.client.chat(messages, temperature=self.temperature)
