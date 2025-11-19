# main_kg.py
from __future__ import annotations
import argparse
import time


def main():
    print("Iniciando ejecución…")
    t_import = time.time()

    # Preparse: decidir qué importar según el modo
    parser_pre = argparse.ArgumentParser(add_help=False)
    parser_pre.add_argument("--mode", choices=["llm", "kggen"], default="llm")
    args_pre, _ = parser_pre.parse_known_args()
    mode = args_pre.mode

    # Lazy import según modo
    if mode == "kggen":
        from .kg_base import run_kg, KGConfig, DEFAULT_CONTEXT
        mode_used = "KG-BASE (OpenAI-compatible)"
        supports_logging_flags = False
        supports_report = False
    else:
        from .text2triplet import run_kg, KGConfig, DEFAULT_CONTEXT
        mode_used = "LLM (text2triplet)"
        supports_logging_flags = True    # usa SQLite + reset_log
        supports_report = True           # puede generar informe

    from .texts import ALL_TEXTS

    print(f"Dependencias cargadas en {time.time() - t_import:.2f}s")
    print(f"Modo seleccionado: {mode_used}\n")

    # Parser principal
    parser = argparse.ArgumentParser(
        description="Extrae tripletas con un LLM (modo 'llm') o con el extractor compatible KG-Base (modo 'kggen')."
    )
    parser.add_argument("--mode", choices=["llm", "kggen"], default=mode,
                        help="Modo de extracción: llm (por defecto) o kggen.")
    parser.add_argument("--text", default="TEXT1",
                        help="Nombre del texto (por defecto: TEXT1). Opciones: " + ", ".join(ALL_TEXTS.keys()))
    parser.add_argument("--model", default=None,
                        help="Sobrescribe el modelo (si no, usa el del .env/KGConfig).")
    parser.add_argument("--context", default=DEFAULT_CONTEXT,
                        help="Contexto/ontología a aplicar.")
    parser.add_argument("--no-drop", action="store_true",
                        help="No descartar tripletas inválidas (se mostrarán igual).")

    # Flags de logging/SQLite
    parser.add_argument("--sqlite-db", default="./data/users/demo.sqlite",
                        help="Ruta a la base de datos SQLite para log/contenido.")
    parser.add_argument("--no-reset-log", action="store_true",
                        help="No limpiar los registros de la tabla de log al inicio (por defecto se limpian).")

    # Flags de report
    parser.add_argument("--generate-report", action="store_true",
                        help="Genera un informe del contenido SQLite al finalizar.")
    parser.add_argument("--report-path", default=None,
                        help="Ruta opcional para guardar el informe. Si no se indica, se genera automáticamente junto al .sqlite.")
    parser.add_argument("--report-sample-limit", type=int, default=15,
                        help="Número de filas a mostrar por tabla en el informe (por defecto: 15).")

    args = parser.parse_args()

    if args.text not in ALL_TEXTS:
        raise SystemExit(f"Texto '{args.text}' no encontrado. Opciones: {', '.join(ALL_TEXTS.keys())}")

    selected_text = ALL_TEXTS[args.text]
    cfg = KGConfig(model=args.model) if args.model else None

    print("=== INICIANDO EXTRACCIÓN ===")
    print(f"Texto: {args.text} | Modo: {args.mode} ")
    print("\nGenerando tripletas...\n")

    t0 = time.time()

    # kwargs básicos
    common_kwargs = dict(
        input_text=selected_text,
        context=args.context,
        cfg=cfg,
        drop_invalid=not args.no_drop,
        print_triplets=True,
    )

    # Añadir control de log si se soporta
    if supports_logging_flags:
        common_kwargs.update(
            sqlite_db_path=args.sqlite_db,
            reset_log=not args.no_reset_log,
        )

    # Añadir opciones de report si se soporta
    if supports_report:
        common_kwargs.update(
            generate_report=args.generate_report,
            report_path=args.report_path,
            report_sample_limit=args.report_sample_limit,
        )

    triplets = run_kg(**common_kwargs)

    print(f"Tiempo total: {time.time() - t0:.2f}s")
    print("=== PROCESO COMPLETADO ===")


if __name__ == "__main__":
    main()
