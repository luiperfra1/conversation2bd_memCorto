# test_roundtrip_from_pairs.py
from __future__ import annotations

import ast
import os
import csv
from typing import List, Tuple, Optional

from text2triplets.text2triplet import run_kg, KGConfig
from text2triplets.triplet2text import (
    Triplet2TextConfig,
    generate_dialog_from_sextets,
)

# =============================================================================
# ========================== CONFIGURACIÓN FIJA ===============================
# =============================================================================

INPUT_PATH = "test_consin_resumidor/conversacion_sextetas_pairs_realistas.txt"


MAX_LINES = None      # None = procesar todo
LANG = "en"             # "en" o "es"

# ------------------ Configuración text2triplet (extractor) -------------------

KG_MODEL = None         # None = usa el de settings por defecto
KG_TEMPERATURE = None  # None = usa el de KGConfig por defecto


OUTPUT_PATH = f"outputs/roundtrip_from_pairs{MAX_LINES}_realistas.csv"
SQLITE_DB_PATH = "./data/users/roundtrip_from_pairs.sqlite"

# ------------------ Configuración triplet2text (generador) -------------------

T2T_MODEL = None        # None = usa settings.MODEL_KG_GEN o "gpt-4o-mini"
T2T_TEMPERATURE = 0.4
T2T_LANG = LANG

# =============================================================================
# =============================================================================


# Tipo de sexteta que devuelve run_kg
Sextet = Tuple[str, str, str, str, str, str]


def load_conversation_texts(
    path: str,
    max_lines: Optional[int] = None,
) -> List[str]:
    """
    Lee el archivo conversacion_sextetas_pairs.txt y devuelve SOLO
    el texto de entrada (LLM + user) de cada línea.
    """
    conversations: List[str] = []

    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                pair = ast.literal_eval(line)
            except Exception:
                print(f"[WARN] No pude parsear la línea {i}, se omite.")
                continue

            if not isinstance(pair, tuple) or len(pair) < 1:
                print(f"[WARN] Línea {i} no es un par válido, se omite.")
                continue

            conv_text = pair[0]
            if not isinstance(conv_text, str):
                print(f"[WARN] Primer elemento de la línea {i} no es str, se omite.")
                continue

            conversations.append(conv_text)

            if max_lines is not None and len(conversations) >= max_lines:
                break

    print(f"[info] Cargadas {len(conversations)} conversaciones desde {path}")
    return conversations


def extract_user_id(conv_text: str) -> str:
    for line in conv_text.splitlines():
        line = line.strip()
        if line.startswith("user_") and ":" in line:
            return line.split(":", 1)[0].strip()
    return "unknown_user"


def run_roundtrip_for_conversation(
    conv_text: str,
    *,
    kg_cfg: Optional[KGConfig] = None,
    t2t_cfg: Optional[Triplet2TextConfig] = None,
) -> tuple[list[Sextet], str]:

    # 1) Extraer sextetas a partir de la conversación completa
    sextets_pred: List[Sextet] = run_kg(
        input_text=conv_text,
        cfg=kg_cfg,
        print_triplets=False,
        reset_log=False,
        sqlite_db_path=SQLITE_DB_PATH,
        generate_report=False,
    )

    # 2) Generar el diálogo inverso desde las sextetas predichas
    dialog_blocks = generate_dialog_from_sextets(sextets_pred, cfg=t2t_cfg)
    conv_regenerated = "\n\n".join(dialog_blocks) if dialog_blocks else ""

    return sextets_pred, conv_regenerated


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    conversations = load_conversation_texts(INPUT_PATH, max_lines=MAX_LINES)

    # ----------------- Inicialización de configuraciones ----------------------

    kg_cfg = KGConfig()
    if KG_MODEL is not None:
        kg_cfg.model = KG_MODEL
    if KG_TEMPERATURE is not None:
        kg_cfg.temperature = KG_TEMPERATURE

    t2t_cfg = Triplet2TextConfig(
        model=T2T_MODEL if T2T_MODEL is not None else Triplet2TextConfig().model,
        temperature=T2T_TEMPERATURE,
        lang=T2T_LANG,
    )

    # ------------------------------ Loop principal ----------------------------

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.writer(f_out, delimiter=";")
        writer.writerow(
            [
                "idx",
                "user_id",
                "original_conversation",
                "num_sextets_pred",
                "sextets_pred",
                "regenerated_conversation",
            ]
        )

        for idx, conv_text in enumerate(conversations, start=1):
            print(f"[info] Procesando conversación {idx}/{len(conversations)}")

            user_id = extract_user_id(conv_text)

            sextets_pred, conv_regenerated = run_roundtrip_for_conversation(
                conv_text,
                kg_cfg=kg_cfg,
                t2t_cfg=t2t_cfg,
            )

            writer.writerow(
                [
                    idx,
                    user_id,
                    conv_text.replace("\n", "\\n"),
                    len(sextets_pred),
                    repr(sextets_pred),
                    conv_regenerated.replace("\n", "\\n"),
                ]
            )

    print(f"\n[done] Resultados guardados en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
