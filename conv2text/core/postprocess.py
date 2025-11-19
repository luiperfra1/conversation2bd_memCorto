# conv2text/core/postprocess.py
from __future__ import annotations
import re
from .rules import DEFAULT_MAX_SENTENCES, MIN_WORDS, MAX_WORDS

def cleanup_summary(text: str) -> str:
    """
    Limpieza conservadora del texto generado:
    - Quita 'Resumen:' si aparece
    - Normaliza espacios
    - Asegura puntos finales en frases
    """
    t = (text or "").strip()
    t = re.sub(r"^(resumen\s*:\s*)", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"[ \t]+", " ", t)

    # Fragmenta en frases por punto
    parts = [p.strip() for p in re.split(r"\.\s*", t) if p.strip()]
    norm = []
    for p in parts:
        p = p.strip("•-*–— ")  # viñetas accidentales
        if not p:
            continue
        if not p.endswith("."):
            p += "."
        norm.append(p)
    return " ".join(norm)

def enforce_limits(text: str, max_sentences: int = DEFAULT_MAX_SENTENCES) -> str:
    """
    - Limita el número de frases
    - Descarta frases demasiado cortas/largas
    """
    sentences = [s.strip() for s in re.split(r"(?<=\.)\s+", text) if s.strip()]
    pruned = []
    for s in sentences:
        n_words = len(s.strip(".").split())
        if n_words < MIN_WORDS or n_words > MAX_WORDS:
            continue
        pruned.append(s)
        if len(pruned) >= max_sentences:
            break
    return " ".join(pruned)
