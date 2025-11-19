# conv2text/pipeline.py
from __future__ import annotations
from typing import Optional
import time

from .io.parsers import detect_user_tag
from .llm.summarizer_text import LLMTextSummarizer
from .core.postprocess import cleanup_summary, enforce_limits

# --- Logging opcional (best-effort, no rompe si no existe) -------------
# Se intentan usar las mismas utilidades que en tu stack.
# Si no están disponibles en tu proyecto actual, todo queda en no-op.
_RUN_LOGGER_AVAILABLE = False
def _now_ts() -> str:
    import datetime as _dt
    return _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

try:
    # Variante genérica que comentaste: log con columnas (ts, level, message, run_id, stage, reason, metadata)
    from triplets2bd.utils.sqlite_client import SqliteClient as _SqliteClient
    from utils.sql_log import ensure_sql_log_table as _ensure_table  # crea tabla si no existe
    try:
        # Si tienes una función genérica de evento:
        from utils.sql_log import log_event as _log_event  # (conn, level, message, run_id, stage, reason, metadata)
        def _emit(level:str, message:str, *, run_id:str, stage:str, reason:str="", metadata=None):
            _log_event(_LOG_CONN.conn, level=level, message=message,
                       run_id=run_id, stage=stage, reason=reason, metadata=metadata or {})
        _RUN_LOGGER_AVAILABLE = True
    except Exception:
        # Backups por compatibilidad: si no hay log_event, hacemos un INSERT manual mínimo.
        def _emit(level:str, message:str, *, run_id:str, stage:str, reason:str="", metadata=None):
            try:
                # Intento genérico de inserción si conoces el esquema:
                # Ajusta la sentencia a tu tabla real si difiere.
                _LOG_CONN.conn.execute(
                    "INSERT INTO log (ts, level, message, run_id, stage, reason, metadata) VALUES (?, ?, ?, ?, ?, ?, ?);",
                    (_now_ts(), level, message, run_id, stage, reason, str(metadata or {})),
                )
                _LOG_CONN.conn.commit()
            except Exception:
                pass
        _RUN_LOGGER_AVAILABLE = True

    # Crea una conexión global perezosa para esta unidad
    _LOG_CONN = _SqliteClient("./data/users/demo.sqlite")
    _ensure_table(_LOG_CONN.conn)

    def _new_run_id() -> str:
        # Id simple y trazable sin depender de librerías extra
        import uuid
        return f"conv2text-{uuid.uuid4().hex[:12]}"

except Exception:
    # No hay infra de log; definimos no-ops.
    _LOG_CONN = None
    def _emit(*args, **kwargs):  # no-op
        return
    def _new_run_id() -> str:
        return "no-log"

# ----------------------------------------------------------------------


def summarize_conversation(
    conversation_text: str,
    max_sentences: int = 10,
    temperature: float = 0.0,
    target_user_tag: Optional[str] = None,
) -> str:
    """
    Orquesta el flujo: (opcional) detecta user_<nombre>, llama al LLM y aplica postproceso.
    Devuelve SOLO el texto resumen final (frases breves con sujeto explícito).

    IMPORTANTE: el comportamiento original se mantiene intacto.
    El logging es best-effort y no altera el resultado.
    """
    run_id = _new_run_id() if _RUN_LOGGER_AVAILABLE else "no-log"
    t0 = time.time()

    # (1) Detección opcional de user tag (mismo que antes)
    _ = target_user_tag or detect_user_tag(conversation_text)

    # (2) LLM (mismo que antes)
    summarizer = LLMTextSummarizer(temperature=temperature)
    t_llm0 = time.time()
    raw = summarizer.run(conversation_text)
    t_llm1 = time.time()

    # (3) Postproceso (mismo que antes)
    cleaned = cleanup_summary(raw)

    # Para métricas: contamos frases simples por puntos (aproximado, no afecta salida)
    def _count_sentences(txt: str) -> int:
        return sum(1 for s in txt.split(".") if s.strip())

    before_len = _count_sentences(cleaned)
    final = enforce_limits(cleaned, max_sentences=max_sentences)
    after_len = _count_sentences(final)

    # --- Logging best-effort (no cambia el resultado) ------------------
    try:
        # Solo emitimos si el canal está disponible
        if _RUN_LOGGER_AVAILABLE:
            total_time = round(time.time() - t0, 3)
            llm_time = round(t_llm1 - t_llm0, 3)

            # WARN si hubo recorte por límite
            if after_len < before_len:
                _emit(
                    "WARN",
                    "summary truncated by max_sentences",
                    run_id=run_id,
                    stage="postprocess_enforce_limits",
                    reason="limit_applied",
                    metadata={
                        "max_sentences": max_sentences,
                        "before": before_len,
                        "after": after_len,
                        "llm_time_s": llm_time,
                        "total_time_s": total_time,
                        "temperature": temperature,
                    },
                )

            # WARN si quedó vacío
            if not final.strip():
                _emit(
                    "WARN",
                    "empty summary after postprocess",
                    run_id=run_id,
                    stage="end",
                    reason="empty_output",
                    metadata={
                        "input_preview": conversation_text[:200],
                        "llm_time_s": llm_time,
                        "total_time_s": total_time,
                        "temperature": temperature,
                    },
                )


    except Exception:
        # Nunca interrumpimos el flujo por el log
        pass

    return final
