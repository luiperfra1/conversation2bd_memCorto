# pipeline.py
from __future__ import annotations
import os
import time
from typing import List, Tuple, Optional

from triplets2bd.engine import run_triplets_to_bd
from triplets2bd.utils.types import EngineOptions
from utils.reset import reset_domain_sqlite, reset_domain_neo4j
from utils.sql_log import ensure_sql_log_table, clear_log

try:
    from text2triplets.texts import ALL_TEXTS
except Exception:
    ALL_TEXTS = {}

try:
    from conv2text.engine import summarize_conversation as summarize_conv_text
except Exception:
    summarize_conv_text = None

Triplet = Tuple[str, str, str]

CONFIG = {
    "source": "text",
    "TEXT_KEY": None,
    "TEXT_RAW": """
LLM: ¿Que haces?
user_ernesto: A ver, es cierto lo que dices, pero ten en cuenta que yo juego al futbol los fines de semana y me gusta leer libros de ciencia ficción.
""",
    "print_conv_summary": True,
    "conv_summary_max_sentences": 10,
    "conv_summary_temperature": 0.0,
    "use_conv2text_for_extractor": True,
    "extractor_mode": "llm",
    "extractor_model": None,
    "drop_invalid": True,
    "backend": "sql",
    "bd_mode": "deterministic",
    "reset": True,
    "sqlite_db_path": "./data/users/demo.sqlite",
    "neo4j_uri": None,
    "neo4j_user": None,
    "neo4j_password": None,
    "neo4j_database": None,
    "triplets_json_str": None,
    "triplets_file_path": None,
}


def _load_from_overrides(json_str: Optional[str], file_path: Optional[str]) -> Optional[List[Triplet]]:
    if json_str:
        from triplets2bd.utils.io import load_triplets_from_json_str
        return load_triplets_from_json_str(json_str)
    if file_path:
        from triplets2bd.utils.io import load_triplets_from_file
        return load_triplets_from_file(file_path)
    return None


def _extract_triplets(
    text: str,
    extractor: str,
    model: Optional[str],
    drop_invalid: bool,
    print_triplets: bool,
    sqlite_db_path: str,
) -> List[Triplet]:
    if extractor == "kggen":
        from text2triplets.kg_base import run_kg, KGConfig, DEFAULT_CONTEXT
    else:
        from text2triplets.text2triplet import run_kg, KGConfig, SEXTET_PROMPT_EN
    cfg = KGConfig(model=model) if model else None
    return run_kg(
        input_text=text,
        context=SEXTET_PROMPT_EN,
        cfg=cfg,
        drop_invalid=drop_invalid,
        print_triplets=print_triplets,
        sqlite_db_path=sqlite_db_path,
        reset_log=False,
    )


def _maybe_conv2text(conversation_text: str, max_sentences: int, temperature: float) -> dict:
    out = {"summary": None, "conv_llm_s": 0.0, "conv_total_s": 0.0}
    if not summarize_conv_text:
        return out
    try:
        start_total = time.perf_counter()
        start_llm = time.perf_counter()
        summary = summarize_conv_text(
            conversation_text=conversation_text,
            max_sentences=max_sentences,
            temperature=temperature,
        )
        out["conv_llm_s"] = time.perf_counter() - start_llm
        out["conv_total_s"] = time.perf_counter() - start_total
        out["summary"] = (summary or "").strip() or None
    except Exception as e:
        print(f"[conv2text] Aviso: no se pudo generar el resumen ({e}).")
    return out


def _reset_all_at_start(sqlite_db_path: str, cfg: dict) -> None:
    try:
        from triplets2bd.utils.sqlite_client import SqliteClient
        db = SqliteClient(sqlite_db_path)
        ensure_sql_log_table(db.conn)
        cleared = clear_log(db.conn)
        db.close()
        print(f"[reset] LOG: limpiadas {cleared} filas.")
    except Exception as e:
        print(f"[reset] Aviso: no se pudo limpiar la tabla 'log' ({e}).")

    try:
        ok_sql = reset_domain_sqlite(sqlite_db_path)
        print(f"[reset] Dominio SQLite: {'OK' if ok_sql else 'NO-OP/FAIL'}")
    except Exception as e:
        print(f"[reset] Aviso: fallo reseteando dominio SQLite ({e}).")

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


def main():
    cfg = CONFIG
    print("=== PIPELINE: Texto Resumen → Tripletas → BD ===")
    print(f"Fuente={cfg['source']} | extractor={cfg['extractor_mode']} | backend={cfg['backend']} | modo BD={cfg['bd_mode']} | reset={'sí' if cfg['reset'] else 'no'}")

    t_start_total = time.perf_counter()
    load_time_s = conv_llm_time_s = conv_total_time_s = extract_time_s = inject_time_s = 0.0

    if cfg.get("reset", False):
        _reset_all_at_start(cfg["sqlite_db_path"], cfg)

    conversation = cfg["TEXT_RAW"] if not cfg["TEXT_KEY"] else ALL_TEXTS.get(cfg["TEXT_KEY"], cfg["TEXT_RAW"])
    print("\nEntrada: TEXT_RAW:\n", conversation)

    t0 = time.perf_counter()
    conv2text_out = _maybe_conv2text(
        conversation_text=conversation,
        max_sentences=cfg.get("conv_summary_max_sentences", 10),
        temperature=cfg.get("conv_summary_temperature", 0.0),
    )
    conv_llm_time_s = conv2text_out.get("conv_llm_s", 0.0)
    conv_total_time_s = conv2text_out.get("conv_total_s", 0.0)
    summary_txt = conv2text_out.get("summary")

    if cfg.get("use_conv2text_for_extractor", True):
        if not summary_txt:
            print("\n[conv2text] Resumen vacío. Se detiene el pipeline.")
            return
        text_for_extractor = summary_txt
        if cfg.get("print_conv_summary", True):
            print("\n[conv2text] El extractor usará el RESUMEN como entrada.")
    else:
        text_for_extractor = conversation
        if cfg.get("print_conv_summary", True):
            print("\n[conv2text] El extractor usará la CONVERSACIÓN como entrada.")

    t0 = time.perf_counter()
    triplets_in = _extract_triplets(
        text=text_for_extractor,
        extractor=cfg["extractor_mode"],
        model=cfg["extractor_model"],
        drop_invalid=cfg["drop_invalid"],
        print_triplets=True,
        sqlite_db_path=cfg["sqlite_db_path"],
    )
    extract_time_s = time.perf_counter() - t0
    print(f"\nExtracción completada en {extract_time_s:.2f}s")

    opts = EngineOptions(
        backend=cfg["backend"],
        mode=cfg["bd_mode"],
        reset=False,
        sqlite_db_path=cfg["sqlite_db_path"],
        reset_log=False,
    )

    print("\nInyectando en la BD…")
    t0 = time.perf_counter()
    res = run_triplets_to_bd(triplets_in, opts)
    inject_time_s = time.perf_counter() - t0

    print("\n=== RESULTADO BD ===")
    print(f"Backend={res.backend} | modo={res.mode} | reset={'sí' if res.reset else 'no'} "
        f"| run_id={getattr(res, 'run_id', None)} | ejecutadas={res.executed_statements} "
        f"| tiempo={inject_time_s:.2f}s")

    # --- NUEVO BLOQUE: mostrar scripts ejecutados ---
    if getattr(res, "det_script", None):
        print("\n─── Script determinista ejecutado ───")
        print(res.det_script.strip())

    if getattr(res, "llm_script", None):
        print("\n─── Script LLM (adicional) ───")
        print(res.llm_script.strip())

    if getattr(res, "leftovers", None):
        print("\n─── Tripletas sobrantes (no ejecutadas) ───")
        for (s, v, o), reason in res.leftovers:
            print(f"({s}, {v}, {o}) -> {reason}")
    # -----------------------------------------------

    total_time_s = time.perf_counter() - t_start_total
    print("\n=== TIEMPOS PIPELINE ===")
    print(f"conv2text (LLM):       {conv_llm_time_s:.3f} s")
    print(f"conv2text (bloque):    {conv_total_time_s:.3f} s")
    print(f"text2triplet:          {extract_time_s:.3f} s")
    print(f"Inyección BD:          {inject_time_s:.3f} s")
    print(f"TOTAL:                 {total_time_s:.3f} s")



if __name__ == "__main__":
    main()
