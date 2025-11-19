# utils/sql_log.py
from __future__ import annotations
import time
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------
# Utilidades de tiempo/ids
# ---------------------------------------------------------------------

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{time.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"

# ---------------------------------------------------------------------
# Creación + migración de la tabla LOG (sin columna triplet)
# ---------------------------------------------------------------------

def ensure_sql_log_table(conn) -> None:
    """
    Esquema objetivo (sin 'triplet'):
      id, ts, level, message, reason, run_id, stage, metadata
    """
    # 1) Crear si no existe (con el esquema objetivo)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS log (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       TEXT NOT NULL,
            level    TEXT NOT NULL,
            message  TEXT NOT NULL,
            reason   TEXT,
            run_id   TEXT,
            stage    TEXT,
            metadata TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_log_run_id   ON log(run_id);
        CREATE INDEX IF NOT EXISTS idx_log_stage_ts ON log(stage, ts);
        """
    )
    # 2) Migraciones de columnas (añadir si faltan)
    _migrate_add_missing_columns(conn)
    # 3) Migración destructiva pero segura: si existe 'triplet', reconstruir la tabla sin esa columna
    _migrate_remove_triplet_if_present(conn)
    conn.commit()

def _table_columns(conn, table: str) -> Dict[str, Dict[str, Any]]:
    cur = conn.execute(f"PRAGMA table_info({table});")
    cols = {}
    for cid, name, coltype, notnull, dflt, pk in cur.fetchall():
        cols[name] = {"type": coltype, "notnull": bool(notnull), "default": dflt, "pk": bool(pk)}
    return cols

def _migrate_add_missing_columns(conn) -> None:
    cols = _table_columns(conn, "log")
    wanted = {
        "ts": "TEXT",
        "level": "TEXT",
        "message": "TEXT",
        "reason": "TEXT",
        "run_id": "TEXT",
        "stage": "TEXT",
        "metadata": "TEXT",
    }
    for col, ctype in wanted.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE log ADD COLUMN {col} {ctype};")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_log_run_id   ON log(run_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_log_stage_ts ON log(stage, ts);")

def _migrate_remove_triplet_if_present(conn) -> None:
    """
    Si la tabla 'log' tiene la columna obsoleta 'triplet', reconstruye la tabla sin ella.
    Procedimiento estándar en SQLite: crear tabla nueva, copiar columnas, renombrar.
    """
    cols = _table_columns(conn, "log")
    if "triplet" not in cols:
        return  # Nada que hacer

    # Crear tabla temporal con el esquema objetivo
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS log_new (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       TEXT NOT NULL,
            level    TEXT NOT NULL,
            message  TEXT NOT NULL,
            reason   TEXT,
            run_id   TEXT,
            stage    TEXT,
            metadata TEXT
        );
        """
    )

    # Determinar columnas a copiar (intersección sin 'triplet')
    copy_cols = [c for c in cols.keys() if c in {"id","ts","level","message","reason","run_id","stage","metadata"}]
    if "id" not in copy_cols:
        # Si por alguna razón no existiese id (no debería), no copiamos id
        copy_cols = [c for c in copy_cols if c != "id"]
    col_list = ", ".join(copy_cols)

    # Copiar datos
    # Si faltan columnas destino, SQLite pondrá NULL
    conn.execute(f"INSERT INTO log_new ({col_list}) SELECT {col_list} FROM log;")

    # Sustituir tablas
    conn.executescript(
        """
        DROP TABLE log;
        ALTER TABLE log_new RENAME TO log;
        CREATE INDEX IF NOT EXISTS idx_log_run_id   ON log(run_id);
        CREATE INDEX IF NOT EXISTS idx_log_stage_ts ON log(stage, ts);
        """
    )

# ---------------------------------------------------------------------
# API de logging (sin 'triplet' — el objeto de fallo va en metadata)
# ---------------------------------------------------------------------

def start_run(conn, metadata: Optional[Dict[str, Any]] = None, run_id: Optional[str] = None) -> str:
    """
    Crea (o usa) un run_id y registra el inicio.
    """
    ensure_sql_log_table(conn)
    rid = run_id or new_run_id()
    log_event(
        conn=conn,
        run_id=rid,
        stage="start",
        level="INFO",
        message="run started",
        metadata=metadata,
    )
    return rid

def end_run(conn, run_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    ensure_sql_log_table(conn)
    log_event(
        conn=conn,
        run_id=run_id,
        stage="end",
        level="INFO",
        message="run finished",
        metadata=metadata,
    )

def log_event(
    conn,
    *,
    level: str,
    message: str,
    run_id: Optional[str] = None,
    stage: Optional[str] = None,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Inserta un evento genérico.
    - run_id: identificador de la ejecución.
    - stage: fase del pipeline (p.ej. 'text2triplet', 'triplet2sql', 'execute_sql', 'summarize').
    - reason: explicación del evento o del fallo (si aplica).
    - metadata: dict serializado a JSON. Si hay un objeto que ha fallado, inclúyelo aquí.
    """
    ensure_sql_log_table(conn)
    ts = _now_iso()
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
    conn.execute(
        """
        INSERT INTO log (ts, level, message, reason, run_id, stage, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (ts, level, message, reason, run_id, stage, metadata_json),
    )
    conn.commit()

def log_failure(
    conn,
    *,
    run_id: Optional[str],
    stage: str,
    reason: str,
    failed_object: Any,
    level: str = "WARN",
    message: str = "Unidad fallida",
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Atajo para registrar un fallo con el objeto problemático en metadata.
    `failed_object` puede ser texto, tripleta, dict, etc.
    """
    meta = {"failed_object": failed_object}
    if extra_metadata:
        meta.update(extra_metadata)
    log_event(
        conn=conn,
        run_id=run_id,
        stage=stage,
        level=level,
        message=message,
        reason=reason,
        metadata=meta,
    )

def insert_leftovers_log(
    conn,
    leftovers: List[Tuple[Any, str]],
    *,
    run_id: Optional[str] = None,
    stage: str = "parse",
    level: str = "WARN",
    message: str = "Unidad descartada",
    base_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Inserta en bloque unidades descartadas. Cada elemento es (failed_object, reason).
    El objeto de fallo se guarda en metadata.
    """
    if not leftovers:
        return
    ensure_sql_log_table(conn)
    ts = _now_iso()

    rows = []
    for failed_object, reason in leftovers:
        meta = {"failed_object": failed_object}
        if base_metadata:
            meta.update(base_metadata)
        rows.append((
            ts, level, message, reason, run_id, stage, json.dumps(meta, ensure_ascii=False)
        ))

    conn.executemany(
        """
        INSERT INTO log (ts, level, message, reason, run_id, stage, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    conn.commit()

# ---------------------------------------------------------------------
# Limpieza opcional (manteniendo la tabla)
# ---------------------------------------------------------------------

def clear_log(conn, older_than_iso: Optional[str] = None) -> int:
    """
    Borra registros (no la tabla). Si se pasa older_than_iso (YYYY-MM-DDTHH:MM:SS),
    borra solo los anteriores a esa fecha. Devuelve filas afectadas.
    """
    ensure_sql_log_table(conn)
    if older_than_iso:
        cur = conn.execute("DELETE FROM log WHERE ts < ?;", (older_than_iso,))
    else:
        cur = conn.execute("DELETE FROM log;")
    conn.commit()
    return cur.rowcount
