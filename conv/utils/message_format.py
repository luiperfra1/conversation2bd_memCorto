from __future__ import annotations
from typing import List, Dict

Message = Dict[str, str]


def history_to_pairs_text(
    history: List[Message],
    username: str = "usuario",
    skip_intro_pair: bool = True,
) -> str:
    """
    Convierte el historial en paquetitos de la forma:

        LLM: ...
        user_<nombre>: ...

    agrupando SIEMPRE pares (assistant → user).

    Si skip_intro_pair=True, se salta el primer par
    (pensado para el saludo inicial y detección de nombre).
    """
    user_tag = f"user_{username}"
    blocks = []

    # Índice desde el que empezamos a buscar pares
    # Se asume que el primer par (0,1) es:
    #   0: assistant -> "Hola, ¿cómo te llamas?"
    #   1: user      -> "Me llamo X"
    # y no se quiere incluir.
    start_idx = 2 if skip_intro_pair else 0

    i = start_idx
    n = len(history)

    while i < n - 1:
        msg_a = history[i]
        msg_b = history[i + 1]

        role_a = msg_a.get("role")
        role_b = msg_b.get("role")
        content_a = (msg_a.get("content") or "").strip()
        content_b = (msg_b.get("content") or "").strip()

        # Buscamos pares assistant → user
        if role_a == "assistant" and role_b == "user" and content_a and content_b:
            block = f"LLM: {content_a}\n{user_tag}: {content_b}"
            blocks.append(block)
            i += 2  # saltamos al siguiente posible par
        else:
            i += 1  # avanzamos 1 si no hay par bien formado

    return "\n\n".join(blocks)
