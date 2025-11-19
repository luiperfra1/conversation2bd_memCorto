from __future__ import annotations
from typing import Dict, Any

import os

# --- Conversador ---
from conv.engine import start_conversation, conversation_turn

# --- Pipeline principal (SIN resets ni prints) ---
from utils.processing_pipeline import CONFIG, main as run_pipeline

# --- Utils para resetear dominios y logs (solo aquí) ---
from utils.reset import reset_domain_sqlite, reset_domain_neo4j
from utils.sql_log import ensure_sql_log_table, clear_log
from triplets2bd.utils.sqlite_client import SqliteClient


ConvState = Dict[str, Any]


def _reset_all_at_start(sqlite_db_path: str, cfg: Dict[str, Any]) -> None:
    """
    Resetea log + dominio SQLite y Neo4j (si hay credenciales).
    Esto solo se ejecuta cuando se lanza pipeline_conv,
    el pipeline normal ya NO resetea nada.
    """
    # --- Reset / limpieza de LOG en SQLite ---
    try:
        db = SqliteClient(sqlite_db_path)
        ensure_sql_log_table(db.conn)
        cleared = clear_log(db.conn)
        db.close()
        print(f"[reset] LOG: limpiadas {cleared} filas.")
    except Exception as e:
        print(f"[reset] Aviso: no se pudo limpiar la tabla 'log' ({e}).")

    # --- Reset dominio SQLite ---
    try:
        ok_sql = reset_domain_sqlite(sqlite_db_path)
        print(f"[reset] Dominio SQLite: {'OK' if ok_sql else 'NO-OP/FAIL'}")
    except Exception as e:
        print(f"[reset] Aviso: fallo reseteando dominio SQLite ({e}).")

    # --- Reset dominio Neo4j ---
    try:
        uri = cfg.get("neo4j_uri") or os.getenv("NEO4J_URI")
        user = cfg.get("neo4j_user") or os.getenv("NEO4J_USER")
        pwd = cfg.get("neo4j_password") or os.getenv("NEO4J_PASSWORD")

        if uri and user and pwd:
            ok_neo = reset_domain_neo4j(uri=uri, user=user, password=pwd)
            print(f"[reset] Dominio Neo4j: {'OK' if ok_neo else 'NO-OP/FAIL'}")
        else:
            print("[reset] Neo4j: credenciales no definidas.")
    except Exception as e:
        print(f"[reset] Aviso: fallo reseteando dominio Neo4j ({e!r}).")


def run_pipeline_with_text(texto: str) -> None:
    """
    Recibe el paquetito del conversador
    y lanza el pipeline usando ese texto como entrada.
    NO resetea nada (el reset se hizo al inicio del script).
    """
    # Forzar a que pipeline use directamente este texto
    CONFIG["TEXT_KEY"] = None
    CONFIG["TEXT_RAW"] = texto

    print("\n=== Enviando paquetito al PIPELINE ===")
    run_pipeline()
    print("=== PIPELINE completado ===\n")


def main() -> None:
    print("=== Conversador + Pipeline (escribe 'salir' para terminar) ===")

    # Reset de BD + logs SOLO al ejecutar este script
    _reset_all_at_start(CONFIG["sqlite_db_path"], CONFIG)

    # Inicializamos conversación
    greeting, state = start_conversation()
    print(f"Bot: {greeting}")

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

        # Turno del conversador
        reply, state, paquetito = conversation_turn(
            user_input=user_input,
            state=state,
        )

        # Si hay paquetito (a partir del segundo turno)
        if paquetito is not None:
            print("\n--- Último paquetito ---")
            print(paquetito)
            print("------------------------")

            # Enviar el paquetito al pipeline
            run_pipeline_with_text(paquetito)

        print(f"\nBot: {reply}")


if __name__ == "__main__":
    main()
