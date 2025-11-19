from __future__ import annotations
from typing import Dict, Any, Optional

import os
import threading
import queue

import streamlit as st

# --- Conversador ---
from conv.engine import start_conversation, conversation_turn, ConvState

# --- Pipeline principal (SIN resets ni prints, escribe en pipelines/pipeline.txt) ---
from utils.processing_pipeline import CONFIG as PIPE_CFG, main as run_pipeline

# --- Utils para resetear dominios y logs (solo aquí) ---
from utils.reset import reset_domain_sqlite, reset_domain_neo4j
from utils.sql_log import ensure_sql_log_table, clear_log
from triplets2bd.utils.sqlite_client import SqliteClient


def _reset_all_at_start(sqlite_db_path: str, cfg: Dict[str, Any], debug: bool = False) -> None:
    """
    Resetea log + dominio SQLite y Neo4j (si hay credenciales).
    Pensado para ejecutarse SOLO una vez al inicio de la sesión de la app.
    """
    # --- Reset / limpieza de LOG en SQLite ---
    try:
        db = SqliteClient(sqlite_db_path)
        ensure_sql_log_table(db.conn)
        cleared = clear_log(db.conn)
        db.close()
        if debug:
            st.write(f"[reset] LOG: limpiadas {cleared} filas.")
    except Exception as e:
        if debug:
            st.write(f"[reset] Aviso: no se pudo limpiar la tabla 'log' ({e}).")

    # --- Reset dominio SQLite ---
    try:
        ok_sql = reset_domain_sqlite(sqlite_db_path)
        if debug:
            st.write(f"[reset] Dominio SQLite: {'OK' if ok_sql else 'NO-OP/FAIL'}")
    except Exception as e:
        if debug:
            st.write(f"[reset] Aviso: fallo reseteando dominio SQLite ({e}).")

    # --- Reset dominio Neo4j ---
    try:
        uri = cfg.get("neo4j_uri") or os.getenv("NEO4J_URI")
        user = cfg.get("neo4j_user") or os.getenv("NEO4J_USER")
        pwd = cfg.get("neo4j_password") or os.getenv("NEO4J_PASSWORD")

        if uri and user and pwd:
            ok_neo = reset_domain_neo4j(uri=uri, user=user, password=pwd)
            if debug:
                st.write(f"[reset] Dominio Neo4j: {'OK' if ok_neo else 'NO-OP/FAIL'}")
        else:
            if debug:
                st.write("[reset] Neo4j: credenciales no definidas.")
    except Exception as e:
        if debug:
            st.write(f"[reset] Aviso: fallo reseteando dominio Neo4j ({e!r}).")


def _run_pipeline_with_text(texto: str, debug: bool = False) -> None:
    """
    Recibe el paquetito del conversador y lanza el pipeline usando ese texto como entrada.
    NO resetea nada (el reset se hace fuera, al iniciar la sesión).
    """
    PIPE_CFG["TEXT_KEY"] = None
    PIPE_CFG["TEXT_RAW"] = texto

    # Importante: esto es BLOQUEANTE, por eso lo llamamos desde un hilo aparte.
    if debug:
        print("=== Enviando paquetito al PIPELINE ===")

    run_pipeline()

    if debug:
        print("=== PIPELINE completado ===")


class ConversationPipelineApp:
    """
    Envoltorio orientado a interfaz gráfica:

    - Gestiona el estado de la conversación (conv.engine).
    - En cada turno de usuario genera la respuesta del bot.
    - Si hay 'paquetito', lo envía a processing_pipeline (que loguea en pipelines/pipeline.txt)
      mediante una cola procesada en segundo plano.
    """

    def __init__(self, *, do_reset: bool = True, debug: bool = False) -> None:
        """
        :param do_reset: si True, resetea SQLite + Neo4j + log al iniciar la sesión.
        :param debug: si True, muestra algunos mensajes (logs en consola / algunos en UI).
        """
        self.debug = debug
        self.state: Optional[ConvState] = None
        self._greeting: Optional[str] = None

        # --- Cola y worker de pipeline ---
        self._pipeline_queue: queue.Queue[str] = queue.Queue()
        self._start_pipeline_worker()

        if do_reset:
            sqlite_path = PIPE_CFG.get("sqlite_db_path", "./data/users/demo.sqlite")
            _reset_all_at_start(sqlite_path, PIPE_CFG, debug=self.debug)

        # Inicializamos conversación
        greeting, state = start_conversation()
        self._greeting = greeting
        self.state = state

    def _start_pipeline_worker(self) -> None:
        """
        Lanza un hilo en segundo plano que consume la cola de textos
        y ejecuta el pipeline de forma secuencial (pero no bloquea la conversación).
        """
        def worker() -> None:
            while True:
                texto = self._pipeline_queue.get()  # bloquea hasta recibir algo
                try:
                    _run_pipeline_with_text(texto, debug=self.debug)
                except Exception as e:
                    # Mejor usar print y no st.write en hilos secundarios
                    print(f"[pipeline_worker] Error procesando paquetito: {e!r}")
                finally:
                    self._pipeline_queue.task_done()

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        if self.debug:
            print("[pipeline_worker] Hilo de pipeline iniciado.")

    def enqueue_pipeline(self, texto: str) -> None:
        """
        Mete un nuevo texto en la cola para que lo procese el worker.
        """
        if self.debug:
            print("[pipeline] Encolando nuevo paquetito.")
        self._pipeline_queue.put(texto)

    @property
    def initial_message(self) -> str:
        """
        Mensaje inicial del bot para mostrar en la interfaz.
        """
        return self._greeting or "Hola."

    def handle_user_message(self, user_input: str) -> Dict[str, Any]:
        """
        Procesa un turno de usuario.

        :param user_input: texto escrito por la persona en la interfaz.
        :return: diccionario con:
                 - 'reply': respuesta del bot
                 - 'paquetito': último paquetito LLM+usuario (o None)
        """
        if self.state is None:
            greeting, state = start_conversation()
            self._greeting = greeting
            self.state = state

        reply, new_state, paquetito = conversation_turn(
            user_input=user_input,
            state=self.state,
        )
        self.state = new_state

        # Si hay paquetito (a partir del 2º turno), lo mandamos al pipeline en SEGUNDO PLANO
        if paquetito is not None:
            if self.debug:
                st.write("---- Paquetito generado ----")
                st.code(paquetito)

            # En lugar de ejecutar el pipeline aquí (bloqueante), lo encolamos
            self.enqueue_pipeline(paquetito)

        return {
            "reply": reply,
            "paquetito": paquetito,
        }


# =========================
#   UI STREAMLIT
# =========================

def main() -> None:
    st.set_page_config(page_title="Conversación → Tripletas → BD", page_icon="🧠")

    st.title("🧠 Conversación → Tripletas → BD")
    st.caption(
        "Asistente conversacional para personas mayores + pipeline silencioso que escribe en `./pipelines/pipeline.txt`."
    )

    # Sidebar
    with st.sidebar:
        st.header("Opciones")
        debug = st.checkbox("Modo debug (mostrar resets/estado pipeline)", value=False)

        if st.button("Reiniciar conversación y resetear BD"):
            # Forzamos reinicio completo
            st.session_state.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("**Log del pipeline**:")
        st.code("./pipelines/pipeline.txt", language="bash")

    # Inicializar app y estado en sesión
    if "conv_app" not in st.session_state:
        st.session_state.conv_app = ConversationPipelineApp(do_reset=True, debug=debug)
        st.session_state.messages = [
            {"role": "assistant", "content": st.session_state.conv_app.initial_message}
        ]
    else:
        # Actualizar flag debug en la instancia existente
        st.session_state.conv_app.debug = debug

    # Mostrar historial de mensajes
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Entrada del usuario
    user_input = st.chat_input("Escribe tu mensaje")

    if user_input:
        app: ConversationPipelineApp = st.session_state.conv_app

        # Añadir mensaje del usuario al historial
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Procesar turno
        result = app.handle_user_message(user_input)
        reply = result["reply"]

        # Añadir respuesta del bot
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Forzar rerender con el nuevo estado
        st.rerun()


if __name__ == "__main__":
    main()
