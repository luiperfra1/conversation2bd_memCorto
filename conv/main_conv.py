from __future__ import annotations
from typing import Dict, Any

from .engine import start_conversation, conversation_turn

ConvState = Dict[str, Any]


def main() -> None:
    print("=== Conversador conv/ (escribe 'salir' para terminar) ===")

    # 1) Inicializamos la conversación en el engine
    greeting, state = start_conversation()
    print(f"Bot: {greeting}")

    # 2) Bucle principal
    while True:
        try:
            user_input = input("\nTú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"salir", "exit", "quit"}:
            print("Adiós.")
            break

        reply, state, paquetito = conversation_turn(
            user_input=user_input,
            state=state,
        )

        # Si hay paquetito (a partir del 2º turno), lo mostramos.
        if paquetito is not None:
            print("\n--- Último paquetito ---")
            print(paquetito)
            print("------------------------")

            # Aquí es donde luego podrás hacer:
            # send_to_conv2text(paquetito)

        print(f"\nBot: {reply}")


if __name__ == "__main__":
    main()
