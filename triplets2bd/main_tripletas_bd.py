# triplets2bd/main_tripletas_bd.py
from __future__ import annotations
import argparse
import time
from typing import Optional

from .utils.types import EngineOptions
from .engine import run_triplets_to_bd
from .utils.io import load_triplets_from_file, load_triplets_from_json_str
from .tripletas_demo import *

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Tripletas → Cypher/SQL (CLI)")
    p.add_argument("--bd", choices=["neo4j", "sql"], default="sql")

    group = p.add_mutually_exclusive_group()
    group.add_argument("--llm", action="store_true", help="Solo LLM")
    group.add_argument("--no-llm", action="store_true", help="Determinista puro")

    p.add_argument("--no-reset", action="store_true", help="No resetear la BD")
    p.add_argument(
        "--no-reset-log",
        action="store_true",
        help="No limpiar los registros de la tabla de log al inicio (por defecto se limpian)"
    )
    p.add_argument("--sqlite-db", default="./data/users/demo.sqlite")

    p.add_argument("--triplets-json", type=str, help="Tripletas como JSON string")
    p.add_argument("--triplets-file", type=str, help="Ruta a fichero con tripletas")

    args = p.parse_args()

    mode = "llm" if args.llm else ("deterministic" if args.no_llm else "hybrid")
    triplets = (
        load_triplets_from_json_str(args.triplets_json) if args.triplets_json else
        load_triplets_from_file(args.triplets_file) if args.triplets_file else
        RAW_TRIPLES_DEMO6
    )

    opts = EngineOptions(
        backend=args.bd,
        mode=mode,
        reset=not args.no_reset,
        reset_log=not args.no_reset_log,   # <- por defecto True, se desactiva con --no-reset-log
        sqlite_db_path=args.sqlite_db,
    )

    start = time.perf_counter()
    res = run_triplets_to_bd(triplets, opts)
    elapsed = time.perf_counter() - start

    print(
        f"Backend={res.backend} | modo={res.mode} | "
        f"reset_bd={'sí' if res.reset else 'no'} | "
        f"reset_log={'sí' if opts.reset_log else 'no'} | "
        f"run_id={res.run_id} | ejecutadas={res.executed_statements} | "
        f"tiempo={elapsed:.2f}s"
    )

    if res.det_script:
        print("\n─── Script determinista ───\n" + res.det_script)
    if res.llm_script:
        print("\n─── Script LLM ───\n" + res.llm_script)
    if res.leftovers:
        print("\n─── Sobrantes (no ejecutados determinista) ───")
        for (s, v, o), reason in res.leftovers:
            print(f"({s}, {v}, {o}) -> {reason}")
