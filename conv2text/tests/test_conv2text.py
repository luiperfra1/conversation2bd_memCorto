# conv2text/tests/test_conv2text.py
from __future__ import annotations
import time
import os

from conv2text.engine import summarize_conversation
from conv2text.texts import ALL_TEXTS

_SQLITE_DB_PATH = "./data/users/demo.sqlite"


# === Reset de la tabla de log antes de los tests (vía utils/sql_log.py) ===
def _reset_log_table(sqlite_db_path: str = _SQLITE_DB_PATH) -> None:
    """
    Limpia SOLO los registros de la tabla 'log' usando la API oficial:
    ensure_sql_log_table + clear_log. No toca otras tablas.
    """
    try:
        from triplets2bd.utils.sqlite_client import SqliteClient
        from utils.sql_log import ensure_sql_log_table, clear_log

        db = SqliteClient(sqlite_db_path)
        ensure_sql_log_table(db.conn)
        n = clear_log(db.conn)  # devuelve filas afectadas
        db.close()
        print(f"[LOG] Tabla 'log' limpiada ({n} filas).")
    except Exception as e:
        print(f"[LOG] No se pudo limpiar la tabla de log: {e}")


# === Generación del informe final ===
def _generate_report(sqlite_db_path: str = _SQLITE_DB_PATH) -> None:
    try:
        from utils.make_sqlite_report import make_content_only_report
    except Exception:
        # fallback si tu módulo está en otra ruta (según tu repo)
        from utils.make_sqlite_report import make_content_only_report

    try:
        out_path = "data/users/demo_report.txt"
        sample_limit = 15
        make_content_only_report(sqlite_db_path, out_path, sample_limit)
        print(f"[REPORT] Informe generado en: {os.path.abspath(out_path)}")
    except Exception as e:
        print(f"[REPORT] No se pudo generar el informe: {e}")


# === TEST PRINCIPAL ===
def run_all_tests(max_sentences: int = 10, temperature: float = 0.0):
    # Reset del log antes de iniciar
    _reset_log_table(_SQLITE_DB_PATH)

    print("=== TEST: conv2text → summarize_conversation ===")
    print(f"Total de textos a procesar: {len(ALL_TEXTS)}")
    print(f"Parámetros: max_sentences={max_sentences}, temperature={temperature}\n")

    total_time = 0.0
    success = 0

    for key, text in ALL_TEXTS.items():
        print(f"─── [{key}] Iniciando resumen... ───")
        start_time = time.perf_counter()
        try:
            summary = summarize_conversation(
                conversation_text=text,
                max_sentences=max_sentences,
                temperature=temperature,
            )
            elapsed = time.perf_counter() - start_time
            total_time += elapsed
            success += 1
            print(f"Conversación:\n {text}\n")
            print(f"Tiempo: {elapsed:.2f}s")
            print(f"Resumen obtenido:\n{summary.strip()}\n")

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            print(f"[ERROR en {key}] ({elapsed:.2f}s): {e}\n")

    avg_time = total_time / success if success > 0 else 0.0
    print("=== RESULTADOS GLOBALES ===")
    print(f"Casos ejecutados: {success}/{len(ALL_TEXTS)}")
    print(f"Tiempo total: {total_time:.2f}s")
    print(f"Tiempo medio por texto: {avg_time:.2f}s")

    # Generar informe al finalizar
    _generate_report(_SQLITE_DB_PATH)


if __name__ == "__main__":
    run_all_tests(max_sentences=10, temperature=0.0)
