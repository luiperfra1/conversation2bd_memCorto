# pipeline.py
from __future__ import annotations

import os
import time
from typing import List, Tuple, Optional, Dict, Any

from triplets2bd.engine import run_triplets_to_bd
from triplets2bd.utils.types import EngineOptions

try:
    from text2triplets.texts import ALL_TEXTS
except Exception:
    ALL_TEXTS = {}

try:
    from conv2text.engine import summarize_conversation as summarize_conv_text
except Exception:
    summarize_conv_text = None


Triplet = Tuple[str, str, str]

PIPELINE_LOG_PATH = "./pipelines/pipeline.txt"


# =========================
# CONFIGURACIÓN PIPELINE
# =========================
CONFIG: Dict[str, Any] = {
    "source": "text",

    # Selección de texto
    "TEXT_KEY": None,
    "TEXT_RAW": """
LLM: ¿Sigues alguna rutina de ejercicio o alimentación?
user_ernesto: Intento comer sano entre semana, aunque los fines de semana suelo comer fuera. Practico yoga una vez a la semana y a veces salgo en bici con un amigo los domingos, pero no siempre.
He pensado en apuntarme a natación, aunque me cuesta organizarme.
""",

    # Conv → texto resumen
    "print_conv_summary": True,
    "conv_summary_max_sentences": 10,
    "conv_summary_temperature": 0.0,
    "use_conv2text_for_extractor": True,

    # Extractor de tripletas
    "extractor_mode": "llm",
    "extractor_model": None,
    "drop_invalid": True,

    # Backend de inyección
    "backend": "sql",
    "bd_mode": "deterministic",
    "reset": False,  # ESTE FLAG YA NO SE USA AQUÍ

    # SQLite
    "sqlite_db_path": "./data/users/demo.sqlite",

    # Neo4j (no se usan aquí, pero se dejan por compatibilidad)
    "neo4j_uri": None,
    "neo4j_user": None,
    "neo4j_password": None,
    "neo4j_database": None,

    # Alternativas de entrada por tripletas (no usadas en este flujo)
    "triplets_json_str": None,
    "triplets_file_path": None,
}


# =========================
# HELPERS
# =========================
def _load_from_overrides(
    json_str: Optional[str],
    file_path: Optional[str],
) -> Optional[List[Triplet]]:
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
        from text2triplets.text2triplet import run_kg, KGConfig, DEFAULT_CONTEXT

    cfg = KGConfig(model=model) if model else None

    return run_kg(
        input_text=text,
        context=DEFAULT_CONTEXT,
        cfg=cfg,
        drop_invalid=drop_invalid,
        print_triplets=print_triplets,
        sqlite_db_path=sqlite_db_path,
        reset_log=False,
    )


def _maybe_conv2text(
    conversation_text: str,
    max_sentences: int,
    temperature: float,
    log,
) -> Dict[str, Any]:
    """
    Genera un resumen con conv2text (si está disponible) y lo deja en el log.
    """
    out: Dict[str, Any] = {
        "summary": None,
        "conv_llm_s": 0.0,
        "conv_total_s": 0.0,
    }

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

        if out["summary"]:
            log("\n--- RESUMEN CONV2TEXT ---")
            log(out["summary"])
            log("-------------------------")

    except Exception as e:
        log(f"[conv2text] Aviso: no se pudo generar el resumen ({e}).")

    return out


def _get_conversation_text(cfg: Dict[str, Any]) -> str:
    if cfg["TEXT_KEY"]:
        return ALL_TEXTS.get(cfg["TEXT_KEY"], cfg["TEXT_RAW"])
    return cfg["TEXT_RAW"]


def _flush_pipeline_log(lines: List[str]) -> None:
    """
    Reglas:
    - Si NO existe la carpeta ./pipelines → se crea.
    - Si NO existe pipeline.txt → se crea vacío.
    - Si SÍ existe pipeline.txt → se borra y se vuelve a crear limpio.
    - Después de esa limpieza, siempre se escribe en modo append.
    """

    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"

    # 1. Asegurar existencia de carpeta
    log_dir = os.path.dirname(PIPELINE_LOG_PATH)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 2. Si el archivo existe → BORRARLO
    if os.path.exists(PIPELINE_LOG_PATH):
        os.remove(PIPELINE_LOG_PATH)

    # 3. Crear el archivo limpio y escribir en modo append
    with open(PIPELINE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(text)




# =========================
# MAIN
# =========================
def main() -> None:
    cfg = CONFIG

    log_lines: List[str] = []

    def log(msg: str) -> None:
        log_lines.append(str(msg))

    log("=== PIPELINE: Texto Resumen → Tripletas → BD ===")
    log(
        f"Fuente={cfg['source']} | extractor={cfg['extractor_mode']} | backend={cfg['backend']} | "
        f"modo BD={cfg['bd_mode']} | reset={'sí' if cfg.get('reset') else 'no'}"
    )

    t_start_total = time.perf_counter()

    load_time_s = 0.0  # reservado por si en el futuro se añade carga desde disco/red
    conv_llm_time_s = 0.0
    conv_total_time_s = 0.0
    extract_time_s = 0.0
    inject_time_s = 0.0

    # --- 1) Obtener conversación de entrada ---
    conversation = _get_conversation_text(cfg)
    log("\nEntrada: TEXT_RAW:\n")
    log(conversation)

    # --- 2) conv2text: obtener resumen (si está disponible) ---
    conv2text_out = _maybe_conv2text(
        conversation_text=conversation,
        max_sentences=cfg.get("conv_summary_max_sentences", 10),
        temperature=cfg.get("conv_summary_temperature", 0.0),
        log=log,
    )

    conv_llm_time_s = conv2text_out.get("conv_llm_s", 0.0)
    conv_total_time_s = conv2text_out.get("conv_total_s", 0.0)
    summary_txt = conv2text_out.get("summary")

    # --- 3) Elegir texto de entrada para el extractor ---
    if cfg.get("use_conv2text_for_extractor", True):
        if not summary_txt:
            log("\n[conv2text] Resumen vacío. Se detiene el pipeline.")
            _flush_pipeline_log(log_lines)
            return

        text_for_extractor = summary_txt

        if cfg.get("print_conv_summary", True):
            log("\n[conv2text] El extractor usará el RESUMEN como entrada.")
    else:
        text_for_extractor = conversation

        if cfg.get("print_conv_summary", True):
            log("\n[conv2text] El extractor usará la CONVERSACIÓN como entrada.")

    # Bloque equivalente a lo que antes veías por pantalla:
    log("\n=== TEXTO DE ENTRADA PARA EXTRACTOR ===")
    log(text_for_extractor)
    log("========================================")

    # --- 4) text2triplet: extracción de tripletas ---
    t0 = time.perf_counter()
    triplets_in = _extract_triplets(
        text=text_for_extractor,
        extractor=cfg["extractor_mode"],
        model=cfg["extractor_model"],
        drop_invalid=cfg["drop_invalid"],
        print_triplets=True,  # no queremos prints en consola
        sqlite_db_path=cfg["sqlite_db_path"],
    )
    extract_time_s = time.perf_counter() - t0
    log(f"\nExtracción completada en {extract_time_s:.2f}s")

    # --- 5) Inyección en BD (triplets2bd) ---
    opts = EngineOptions(
        backend=cfg["backend"],
        mode=cfg["bd_mode"],
        reset=False,           # el reset ya no se hace aquí
        sqlite_db_path=cfg["sqlite_db_path"],
        reset_log=False,       # el log se gestiona fuera (en pipeline_conv)
    )

    log("\nInyectando en la BD…")
    t0 = time.perf_counter()
    res = run_triplets_to_bd(triplets_in, opts)
    inject_time_s = time.perf_counter() - t0

    log("\n=== RESULTADO BD ===")
    log(
        f"Backend={res.backend} | modo={res.mode} | reset={'sí' if res.reset else 'no'} "
        f"| run_id={getattr(res, 'run_id', None)} | ejecutadas={res.executed_statements} "
        f"| tiempo={inject_time_s:.2f}s"
    )

    # --- Mostrar scripts ejecutados (si existen) ---
    if getattr(res, "det_script", None):
        log("\n─── Script determinista ejecutado ───")
        log(res.det_script.strip())

    if getattr(res, "llm_script", None):
        log("\n─── Script LLM (adicional) ───")
        log(res.llm_script.strip())

    if getattr(res, "leftovers", None):
        log("\n─── Tripletas sobrantes (no ejecutadas) ───")
        for (s, v, o), reason in res.leftovers:
            log(f"({s}, {v}, {o}) -> {reason}")

    # --- 6) Resumen de tiempos ---
    total_time_s = time.perf_counter() - t_start_total

    log("\n=== TIEMPOS PIPELINE ===")
    log(f"conv2text (LLM):       {conv_llm_time_s:.3f} s")
    log(f"conv2text (bloque):    {conv_total_time_s:.3f} s")
    log(f"text2triplet:          {extract_time_s:.3f} s")
    log(f"Inyección BD:          {inject_time_s:.3f} s")
    log(f"TOTAL:                 {total_time_s:.3f} s")

    _flush_pipeline_log(log_lines)


if __name__ == "__main__":
    main()
