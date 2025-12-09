# pipeline_conv2triplet_ablation.py
from __future__ import annotations

import os
import time
import ast
from typing import Dict, Any, List, Tuple, Optional

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


Triplet = Any  # Lo dejamos genérico porque ahora realmente son sextetas/dicts/etc.


CONFIG: Dict[str, Any] = {
    # --- conv2text ---
    "use_conv2text": True,
    "conv_summary_max_sentences": 10,
    "conv_summary_temperature": 0.0,

    # --- text2triplets ---
    "extractor_model": None,        # p.ej. "openai/qwen2.5:32b" si quieres forzar modelo
    "drop_invalid": True,
    "sqlite_db_path": "./data/users/demo.sqlite",  # se usa solo para los logs internos de text2triplets
    "reset_log": False,             # no reseteamos logs desde aquí

    # --- input: fichero (conversación, sexteta) ---
    # Cada línea del fichero debe ser algo del estilo:
    # ("LLM: ...\nuser_x: ...", ("user_x", "verb", "obj", "freq", "cond", "prob"))
    "pairs_file_path": "test_consin_resumidor/conversacion_sextetas_pairs_enormes.txt",
    "max_cases": 3,  # p.ej. 100 si quieres limitar, o None para todos

    # --- output ---
    "output_dir": "./test_consin_resumidor/outputs",
    "output_filename": "ablation_conv2text_vs_full.txt",

    # Prints
    "print_conv_summary_console": True,
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
    Devuelve la lista de elementos tal y como la emita run_kg (dicts, tuplas, etc.).
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
        print_triplets=False,      # aquí NO imprimimos, solo devolvemos
        sqlite_db_path=sqlite_db_path,
        reset_log=reset_log,
    )
    return triplets or []


def _format_triplets_for_txt(triplets: List[Triplet]) -> str:
    """
    Devuelve una representación legible de la lista de tripletas/sextetas para el txt.
    """
    if not triplets:
        return "(sin resultados)"

    lines = []
    for i, t in enumerate(triplets, start=1):
        # Usamos repr() para ver bien dicts/tuplas.
        lines.append(f"{i:02d}. {repr(t)}")
    return "\n".join(lines)


def _load_pairs_as_cases(
    pairs_file_path: str,
    max_cases: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Carga el fichero de pares (conversación, sexteta) y lo convierte
    a un diccionario tipo KG_TEST_CASES:
        {
          "CASE_001": {
              "description": "",
              "conversation": "<texto>",
              "expected_triplets": [sexteta],
          },
          ...
        }
    """
    if not os.path.exists(pairs_file_path):
        print(f"[load_pairs] Fichero no encontrado: {pairs_file_path}")
        return {}

    cases: Dict[str, Dict[str, Any]] = {}
    with open(pairs_file_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            if max_cases is not None and idx > max_cases:
                break

            line = line.strip()
            if not line:
                continue

            try:
                # Esperamos algo como: ("LLM:...\nuser_x:...", ("user_x","verb",...))
                pair = ast.literal_eval(line)
                if not isinstance(pair, tuple) or len(pair) != 2:
                    print(f"[load_pairs] Línea {idx} no es un par válido, se ignora.")
                    continue

                conversation, sextet = pair
                case_id = f"CASE_{idx:03d}"

                cases[case_id] = {
                    "description": "",
                    "conversation": conversation,
                    "expected_triplets": [sextet],
                }

            except Exception as e:
                print(f"[load_pairs] Error parseando línea {idx}: {e}")
                continue

    if not cases:
        print("[load_pairs] No se pudo cargar ningún caso válido desde el fichero.")

    return cases


def _run_single_case(case_id: str, data: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    """
    Ejecuta un caso de prueba:
      - conv2text (si está disponible y activado)
      - extracción con resumen
      - extracción sin resumen
    y devuelve un bloque de texto formateado para el archivo de salida.
    """
    description = data.get("description", "")
    conversation = data.get("conversation", "")
    expected_triplets: List[Triplet] = data.get("expected_triplets", [])

    if not conversation:
        return f"[{case_id}] ERROR: conversación vacía.\n"

    block_lines: List[str] = []
    block_lines.append("=" * 100)
    block_lines.append(f"CASO: {case_id}")
    block_lines.append("-" * 100)
    if description:
        block_lines.append(f"Descripción: {description}")
        block_lines.append("-" * 100)

    block_lines.append("[CONVERSATION]")
    block_lines.append(conversation)
    block_lines.append("")

    # --- Paso 1: conv2text (resumen) ---
    summary_txt = None
    conv_llm_s = conv_total_s = 0.0

    if cfg.get("use_conv2text", True):
        conv_out = _run_conv2text(
            conversation_text=conversation,
            max_sentences=cfg.get("conv_summary_max_sentences", 10),
            temperature=cfg.get("conv_summary_temperature", 0.0),
        )
        summary_txt = conv_out.get("summary")
        conv_llm_s = conv_out.get("conv_llm_s", 0.0)
        conv_total_s = conv_out.get("conv_total_s", 0.0)

        if cfg.get("print_conv_summary_console", True) and summary_txt:
            print(f"[{case_id}] Resumen conv2text obtenido:")
            print(summary_txt)

        block_lines.append("[conv2text] RESUMEN")
        if summary_txt:
            block_lines.append(summary_txt)
            block_lines.append(f"[conv2text] Tiempos: LLM={conv_llm_s:.3f}s | bloque={conv_total_s:.3f}s")
        else:
            block_lines.append("(no se pudo generar resumen o quedó vacío)")
        block_lines.append("")

    else:
        block_lines.append("[conv2text] Desactivado en CONFIG. No se genera resumen.")
        block_lines.append("")

    # --- Paso 2A: extracción CON resumen (si existe) ---
    triplets_with_summary: List[Triplet] = []
    t_with_summary_s = 0.0

    if summary_txt:
        print(f"[{case_id}] Extrayendo tripletas a partir del RESUMEN...")
        t0 = time.perf_counter()
        triplets_with_summary = _run_text2triplets(
            text=summary_txt,
            model=cfg.get("extractor_model"),
            drop_invalid=cfg.get("drop_invalid", True),
            sqlite_db_path=cfg.get("sqlite_db_path", "./data/users/demo.sqlite"),
            reset_log=cfg.get("reset_log", False),
        )
        t_with_summary_s = time.perf_counter() - t0

        block_lines.append("[text2triplets] RESULTADOS usando RESUMEN conv2text")
        block_lines.append(f"Tiempo extracción: {t_with_summary_s:.3f}s")
        block_lines.append(_format_triplets_for_txt(triplets_with_summary))
        block_lines.append("")
    else:
        block_lines.append("[text2triplets] No se ejecuta variante con resumen (no hay resumen disponible).")
        block_lines.append("")

    # --- Paso 2B: extracción SIN resumen (texto original) ---
    print(f"[{case_id}] Extrayendo tripletas a partir de la CONVERSACIÓN completa...")
    triplets_raw: List[Triplet] = []
    t_raw_s = 0.0
    t0 = time.perf_counter()
    triplets_raw = _run_text2triplets(
        text=conversation,
        model=cfg.get("extractor_model"),
        drop_invalid=cfg.get("drop_invalid", True),
        sqlite_db_path=cfg.get("sqlite_db_path", "./data/users/demo.sqlite"),
        reset_log=False,  # aquí normalmente no queremos resetear entre variantes
    )
    t_raw_s = time.perf_counter() - t0

    block_lines.append("[text2triplets] RESULTADOS usando CONVERSACIÓN completa (sin conv2text)")
    block_lines.append(f"Tiempo extracción: {t_raw_s:.3f}s")
    block_lines.append(_format_triplets_for_txt(triplets_raw))
    block_lines.append("")

    # --- Tripletas esperadas (gold) ---
    block_lines.append("[GOLD] TRIPLETAS/SEXTETAS ESPERADAS")
    block_lines.append(_format_triplets_for_txt(expected_triplets))
    block_lines.append("")

    # Opcional: mini comparación muy básica por longitud (no entramos en F1 aquí).
    block_lines.append("[COMPARACIÓN RÁPIDA] (solo tamaños)")
    block_lines.append(
        f"- #gold={len(expected_triplets)} | "
        f"#with_summary={len(triplets_with_summary)} | "
        f"#raw={len(triplets_raw)}"
    )
    block_lines.append("")

    return "\n".join(block_lines)


def main() -> None:
    cfg = CONFIG

    cases = _load_pairs_as_cases(
        pairs_file_path=cfg.get("pairs_file_path", "./data/testing/conversacion_sextetas_pairs.txt"),
        max_cases=cfg.get("max_cases"),
    )

    if not cases:
        print("[pipeline] No se cargaron casos desde el fichero de pares. Nada que procesar.")
        return

    os.makedirs(cfg.get("output_dir", "./outputs"), exist_ok=True)
    output_path = os.path.join(cfg["output_dir"], cfg["output_filename"])

    print("=== PIPELINE ABLATION conv2text vs CONVERSACIÓN DIRECTA ===")
    print(f"Casos de prueba: {list(cases.keys())}")
    print(f"Archivo de salida: {output_path}")

    t_start_global = time.perf_counter()

    blocks: List[str] = []
    for case_id, data in cases.items():
        print("\n" + "=" * 80)
        print(f"Procesando caso: {case_id}")
        print("=" * 80)
        block_txt = _run_single_case(case_id, data, cfg)
        blocks.append(block_txt)

    total_global = time.perf_counter() - t_start_global

    # Guardar todo en el TXT
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks))
        f.write("\n")
        f.write("=" * 100 + "\n")
        f.write(f"FIN PIPELINE ABLATION. Tiempo total: {total_global:.3f}s\n")

    print("\n=== FIN PIPELINE ABLATION conv2text vs CONVERSACIÓN DIRECTA ===")
    print(f"Tiempo total: {total_global:.3f}s")
    print(f"Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()
