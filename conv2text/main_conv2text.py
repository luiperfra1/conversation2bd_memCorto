# conv2text/main_conv2text.py
from __future__ import annotations
import argparse
import sys
import time

from .engine import summarize_conversation
from .io.files import read_text_file, write_text_file
from .texts import ALL_TEXTS


def _read_input(path: str | None) -> str:
    if path and path != "-":
        return read_text_file(path)
    return sys.stdin.read()


def _reset_log_table(sqlite_db_path: str, do_reset: bool) -> None:
    """
    Limpia SOLO la tabla 'log' usando la API oficial (utils/sql_log.py).
    Si do_reset=False o faltan dependencias, no hace nada.
    """
    if not do_reset:
        return
    try:
        from triplets2bd.utils.sqlite_client import SqliteClient
        from utils.sql_log import ensure_sql_log_table, clear_log

        db = SqliteClient(sqlite_db_path)
        ensure_sql_log_table(db.conn)
        deleted = clear_log(db.conn)  # si tu clear_log devuelve un recuento
        db.close()
        sys.stderr.write(f"[conv2text] Log reseteado en '{sqlite_db_path}' ({deleted} filas eliminadas).\n")
    except Exception as e:
        sys.stderr.write(f"[conv2text] Aviso: no se pudo resetear la tabla 'log' ({e}).\n")


def _generate_report(sqlite_db_path: str, out_path: str, sample_limit: int) -> None:
    """
    Genera un informe de contenido SQLite (muestras por tabla).
    """
        # según tu proyecto puede estar en utils/make_sqlite_report o en triplets2bd/utils/...
    from utils.make_sqlite_report import make_content_only_report


    try:
        make_content_only_report(sqlite_db_path, out_path, sample_limit)
    except Exception as e:
        sys.stderr.write(f"[conv2text] Aviso: no se pudo generar el informe ({e}).\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Conv2Text: resume conversaciones (LLM) en frases breves con sujeto explícito."
    )
    parser.add_argument("--in", dest="inpath", default="-",
                        help="Ruta del archivo de conversación (o '-' para stdin). Ignorado si usas --text-key.")
    parser.add_argument("--out", dest="outpath", default=None,
                        help="Ruta de salida del resumen (opcional). Si no, imprime en consola.")
    parser.add_argument("--max", dest="max_sentences", type=int, default=10,
                        help="Máximo de frases del resumen.")
    parser.add_argument("--temp", dest="temperature", type=float, default=0.0,
                        help="Temperatura del LLM (0.0 por defecto).")
    parser.add_argument("--text-key", dest="text_key", default="TEXT1",
                        help="Clave de ejemplo: TEXT1, TEXT2, ... (usa conv2text/texts.py). Por defecto: TEXT1")
    parser.add_argument("--list-texts", action="store_true",
                        help="Lista las claves disponibles y termina.")

    # === Flags de logging (estilo main_kg.py) ===
    parser.add_argument("--sqlite-db", dest="sqlite_db", default="./data/users/demo.sqlite",
                        help="Ruta a la base de datos SQLite para el log.")
    parser.add_argument("--no-reset-log", dest="no_reset_log", action="store_true",
                        help="No limpiar la tabla 'log' al inicio (por defecto se limpia).")

    # === Flags de reporte ===
    parser.add_argument("--generate-report", dest="generate_report", action="store_true",
                        help="Genera un informe del contenido SQLite al finalizar.")
    parser.add_argument("--report-out", dest="report_out", default="data/users/demo_report.txt",
                        help="Ruta del informe (por defecto: data/users/conv2text_report.txt).")
    parser.add_argument("--report-limit", dest="report_limit", type=int, default=15,
                        help="Filas de muestra por tabla en el informe (por defecto: 15).")

    args = parser.parse_args()

    if args.list_texts:
        keys = sorted(ALL_TEXTS.keys(), key=lambda k: (len(k), k))
        sys.stdout.write("Textos disponibles:\n")
        for k in keys:
            sys.stdout.write(f"- {k}\n")
        return

    # Reset opcional de log (solo tabla 'log')
    _reset_log_table(args.sqlite_db, do_reset=not args.no_reset_log)

    start_total = time.perf_counter()

    start_load = time.perf_counter()
    if args.text_key:
        if args.text_key not in ALL_TEXTS:
            sys.stderr.write(f"[conv2text] Clave no encontrada: {args.text_key}\n")
            sys.stderr.write("Usa --list-texts para ver opciones.\n")
            sys.exit(1)
        conversation = ALL_TEXTS[args.text_key]
    else:
        # Esto solo ocurrirá si el usuario pasa explícitamente --text-key "" (vacío)
        conversation = _read_input(args.inpath)
    load_time = time.perf_counter() - start_load

    start_llm = time.perf_counter()
    summary = summarize_conversation(
        conversation_text=conversation,
        max_sentences=args.max_sentences,
        temperature=args.temperature,
    )
    llm_time = time.perf_counter() - start_llm

    total_time = time.perf_counter() - start_total

    # Si hay --out, guardamos solo resumen
    if args.outpath:
        write_text_file(args.outpath, summary + ("\n" if not summary.endswith("\n") else ""))
    else:
        # Si no hay --out → imprimir conversación + resumen + tiempos
        print("--- CONVERSACIÓN ---")
        print(conversation.strip())
        print("\n--- RESUMEN ---")
        print(summary.strip())

        print("\n--- TIEMPOS ---")
        print(f"Carga del texto: {load_time:.3f} s")
        print(f"LLM: {llm_time:.3f} s")
        print(f"Total: {total_time:.3f} s")

    # Generar informe al finalizar (si se pide)
    if args.generate_report:
        _generate_report(args.sqlite_db, args.report_out, args.report_limit)


if __name__ == "__main__":
    main()
