# conv2text/io/parsers.py
from __future__ import annotations
import re
from typing import Optional

USER_TAG_RE = re.compile(r"^\s*user_([a-z0-9_]+)\s*:", re.IGNORECASE | re.MULTILINE)

def detect_user_tag(conversation_text: str) -> Optional[str]:
    """
    Devuelve el primer 'user_<nombre>' encontrado en la conversación o None.
    """
    m = USER_TAG_RE.search(conversation_text or "")
    if not m:
        return None
    return f"user_{m.group(1).lower()}"
