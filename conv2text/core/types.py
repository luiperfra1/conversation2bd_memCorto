# conv2text/core/types.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Turn:
    role: str   # "LLM" o "user_<nombre>"
    text: str
