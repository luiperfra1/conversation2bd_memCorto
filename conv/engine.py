from __future__ import annotations
from typing import List, Dict, Tuple, Optional, Any
import time

from .llm_client import ConvClient
from .utils.name_extractor import extract_name

Message = Dict[str, str]
ConvState = Dict[str, Any]

DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente conversacional diseñado para acompañar a personas mayores "
    "que viven solas. "
    "Hablas siempre en español, con un tono cálido, respetuoso y fácil de entender. "
    "Tu objetivo es que la conversación resulte amable y reconfortante. "
    "Responde de forma clara y breve, salvo que el usuario pida más detalle. "
    "Adapta tu lenguaje para que sea accesible y no técnico. "
    "Muestra paciencia, interés genuino por la persona y mantén un ritmo pausado. "
    "Evita frases bruscas, evita interrumpir ideas del usuario y nunca des diagnósticos médicos. "
    "Tu prioridad es crear compañía, escuchar y conversar de manera natural."
)


DEFAULT_GREETING = "Hola, ¿cómo te llamas?"


def chat_turn(
    user_input: str,
    history: Optional[List[Message]] = None,
    system_prompt: Optional[str] = None,
    client: Optional[ConvClient] = None,
) -> Tuple[str, List[Message]]:
    """
    Turno de conversación 'bajo nivel':
    - Recibe el input del usuario.
    - Recibe/history previa en formato OpenAI.
    - Llama al LLM y devuelve (reply, new_history).

    NOTA: no sabe nada de nombres ni paquetitos.
    """
    if client is None:
        client = ConvClient()

    history = history or []

    messages: List[Message] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    start = time.time()
    reply = client.chat(messages)
    end = time.time()
    elapsed = end - start
    print(f"[conv] Tiempo de respuesta LLM: {elapsed:.3f} s")

    new_history = history + [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": reply},
    ]

    return reply, new_history


# ================================
#   API DE ALTO NIVEL (CON ESTADO)
# ================================

def start_conversation(
    system_prompt: Optional[str] = None,
) -> Tuple[str, ConvState]:
    """
    Inicializa una conversación.

    Devuelve:
    - greeting: texto inicial del LLM (fijo) -> "Hola, ¿cómo te llamas?"
    - state: diccionario de estado interno de la conversación
    """
    greeting = DEFAULT_GREETING
    state: ConvState = {
        "history": [
            {"role": "assistant", "content": greeting}
        ],
        "username": "usuario",            # se rellenará con el nombre real
        "first_turn": True,               # hasta que el usuario responda al nombre
        "last_llm_message": greeting,     # último mensaje del LLM
        "system_prompt": system_prompt or DEFAULT_SYSTEM_PROMPT,
    }
    return greeting, state


def conversation_turn(
    user_input: str,
    state: ConvState,
    client: Optional[ConvClient] = None,
) -> Tuple[str, ConvState, Optional[str]]:
    """
    Turno de conversación 'alto nivel' CON estado.

    - Gestiona:
        * detección de nombre en el primer turno
        * construcción del paquetito:
            "LLM: <último mensaje del LLM>\nuser_<nombre>: <user_input>"
        * llamada a chat_turn y actualización de history

    Devuelve:
    - reply: respuesta del LLM
    - state: estado actualizado
    - paquetito: str con el último par LLM+user, o None si no aplica
    """
    if client is None:
        client = ConvClient()

    history: List[Message] = state.get("history", [])
    username: str = state.get("username", "usuario")
    first_turn: bool = state.get("first_turn", True)
    last_llm_message: Optional[str] = state.get("last_llm_message")
    system_prompt: str = state.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

    paquetito: Optional[str] = None

    # 1) Primer turno: el usuario responde al saludo con su nombre
    if first_turn:
        detected = extract_name(user_input)
        username = detected or "usuario"
        state["username"] = username
        state["first_turn"] = False
        print(f"[conv] Nombre detectado: {username}")

        # Llamamos al LLM con el propio texto del usuario
        reply, new_history = chat_turn(
            user_input=user_input,
            history=history,
            system_prompt=system_prompt,
            client=client,
        )
        state["history"] = new_history
        state["last_llm_message"] = reply

        # NO devolvemos paquetito en este turno (solo renombrado)
        return reply, state, None

    # 2) Turnos posteriores: construimos paquetito usando el último mensaje del LLM
    if last_llm_message is not None:
        paquetito = f"LLM: {last_llm_message}\nuser_{username}: {user_input}"

    # Llamada normal al LLM
    reply, new_history = chat_turn(
        user_input=user_input,
        history=history,
        system_prompt=system_prompt,
        client=client,
    )
    state["history"] = new_history
    state["last_llm_message"] = reply

    return reply, state, paquetito
