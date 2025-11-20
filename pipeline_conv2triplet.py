# pipeline_conv2triplet.py
from __future__ import annotations

import time
from typing import Dict, Any, List, Tuple, Optional

# --- Textos de entrada (conversaciones) ---
try:
    # Debe existir conv2text/texts_en.py con ALL_TEXTS = {"TEXT1": "...", ...}
    from conv2text.texts_en import ALL_TEXTS
except Exception:
    ALL_TEXTS: Dict[str, str] = {}
    print("[warn] No se pudo importar conv2text.texts_en.ALL_TEXTS. Usando diccionario vacío.")

# --- Capa conv2text (resumen de conversación) ---
try:
    from conv2text.engine import summarize_conversation
except Exception:
    summarize_conversation = None
    print("[warn] No se pudo importar conv2text.engine.summarize_conversation. conv2text desactivado.")

# --- Capa text2triplets (extracción de tripletas/sextetas) ---
try:
    from text2triplets.text2triplet import run_kg, KGConfig, SEXTET_PROMPT_EN
except Exception:
    run_kg = None
    KGConfig = None
    SEXTET_PROMPT_EN = None
    print("[warn] No se pudo importar text2triplets.text2triplet. Extracción desactivada.")


Triplet = Tuple[str, str, str]  # Solo para typing, aunque ahora sean sextetas.


CONFIG: Dict[str, Any] = {
    # Clave del texto a usar:
    #  - "TEXT1", "TEXT2", etc. (de conv2text/texts_en.py)
    #  - "ALL_TEXTS" → recorre todos los textos del diccionario
    "TEXT_KEY": "TEXT1",

    # --- conv2text ---
    "use_conv2text": True,
    "conv_summary_max_sentences": 10,
    "conv_summary_temperature": 0.0,

    # --- text2triplets ---
    "extractor_model": None,        # p.ej. "openai/qwen2.5:32b" si quieres forzar modelo
    "drop_invalid": True,
    "sqlite_db_path": "./data/users/demo.sqlite",  # se usa solo para los logs internos de text2triplets
    "reset_log": False,             # no reseteamos logs desde aquí

    # Prints
    "print_conv_summary": True,
}


def _run_conv2text(
    conversation_text: str,
    max_sentences: int,
    temperature: float,
) -> Dict[str, Any]:
    """
    Envuelve summarize_conversation para medir tiempos y devolver el resumen.
    """
    out = {"summary": None, "conv_llm_s": 0.0, "conv_total_s": 0.0}

    if not summarize_conversation:
        print("[conv2text] summarize_conversation no disponible. Se salta conv2text.")
        return out

    try:
        start_total = time.perf_counter()
        start_llm = time.perf_counter()

        summary = summarize_conversation(
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


def _run_text2triplets(
    text: str,
    model: Optional[str],
    drop_invalid: bool,
    sqlite_db_path: str,
    reset_log: bool,
) -> List[Triplet]:
    """
    Llama a text2triplets.run_kg con el prompt de sextetas.
    Imprime las tripletas/sextetas porque usamos print_triplets=True.
    """
    if not run_kg or not SEXTET_PROMPT_EN:
        print("[text2triplets] run_kg o SEXTET_PROMPT_EN no disponibles. Se omite extracción.")
        return []

    cfg_obj = KGConfig(model=model) if model and KGConfig else None

    triplets = run_kg(
        input_text=text,
        context=SEXTET_PROMPT_EN,
        cfg=cfg_obj,
        drop_invalid=drop_invalid,
        print_triplets=True,      # IMPORTANTE: que imprima las tripletas/sextetas
        sqlite_db_path=sqlite_db_path,
        reset_log=reset_log,
    )
    return triplets or []


def _get_text_keys_to_process(all_texts: Dict[str, str], selected_key: Optional[str]) -> List[str]:
    """
    Devuelve la lista de claves a procesar en función del valor de TEXT_KEY.
    """
    if not all_texts:
        print("[pipeline] ALL_TEXTS está vacío. No hay textos que procesar.")
        return []

    if not selected_key or selected_key.upper() == "ALL_TEXTS":
        # Recorremos todas las claves en orden de inserción
        return list(all_texts.keys())

    if selected_key not in all_texts:
        print(f"[pipeline] Clave TEXT_KEY='{selected_key}' no encontrada en ALL_TEXTS.")
        print(f"[pipeline] Claves disponibles: {list(all_texts.keys())}")
        return []

    return [selected_key]


def main() -> None:
    cfg = CONFIG
    selected_key = cfg.get("TEXT_KEY")

    print("=== PIPELINE conv2text → text2triplets ===")
    print(f"TEXT_KEY={selected_key!r}")
    print(f"use_conv2text={cfg.get('use_conv2text', True)}")

    keys_to_process = _get_text_keys_to_process(ALL_TEXTS, selected_key)
    if not keys_to_process:
        return

    t_start_global = time.perf_counter()

    for idx, key in enumerate(keys_to_process, start=1):
        raw_text = ALL_TEXTS[key]

        print("\n" + "=" * 80)
        print(f"[{idx}/{len(keys_to_process)}] TEXTO: {key}")
        print("-" * 80)
        print(raw_text)
        print("-" * 80)

        text_for_extractor = raw_text

        # --- Paso 1: conv2text (resumen) ---
        conv_llm_s = conv_total_s = 0.0
        if cfg.get("use_conv2text", True):
            conv_out = _run_conv2text(
                conversation_text=raw_text,
                max_sentences=cfg.get("conv_summary_max_sentences", 10),
                temperature=cfg.get("conv_summary_temperature", 0.0),
            )
            summary_txt = conv_out.get("summary")
            conv_llm_s = conv_out.get("conv_llm_s", 0.0)
            conv_total_s = conv_out.get("conv_total_s", 0.0)

            if not summary_txt:
                print("[conv2text] Resumen vacío. Se salta text2triplets para este texto.")
                continue

            text_for_extractor = summary_txt

            if cfg.get("print_conv_summary", True):
                print("\n[conv2text] RESUMEN OBTENIDO:")
                print(summary_txt)
                print(f"\n[conv2text] Tiempos: LLM={conv_llm_s:.3f}s | bloque={conv_total_s:.3f}s")

        else:
            print("[conv2text] Desactivado. Se usará la conversación original como entrada al extractor.")

        # --- Paso 2: text2triplets (extracción) ---
        print("\n[text2triplets] Extrayendo tripletas/sextetas a partir del texto de entrada...")
        t_extract_start = time.perf_counter()
        triplets = _run_text2triplets(
            text=text_for_extractor,
            model=cfg.get("extractor_model"),
            drop_invalid=cfg.get("drop_invalid", True),
            sqlite_db_path=cfg.get("sqlite_db_path", "./data/users/demo.sqlite"),
            reset_log=cfg.get("reset_log", False),
        )
        t_extract = time.perf_counter() - t_extract_start
        print(f"\n[text2triplets] Extracción completada en {t_extract:.3f}s "
              f"({len(triplets)} elementos devueltos)\n")

    total_global = time.perf_counter() - t_start_global
    print("\n=== FIN PIPELINE conv2text → text2triplets ===")
    print(f"Tiempo total: {total_global:.3f}s")


if __name__ == "__main__":
    main()
