# eval_roundtrip_scores.py
from __future__ import annotations

import csv
import os
import ast
from typing import List, Dict, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

# ========================== CONFIGURACIÓN ===========================

INPUT_CSV = "outputs/roundtrip_from_pairsNone_realistas.csv"
OUTPUT_CSV = "outputs/roundtrip_from_pairsNone_realistas_scored.csv"

CSV_DELIMITER = ";"           # el que estás usando
EMB_MODEL_NAME = "all-MiniLM-L6-v2"   # modelo ligero y estándar

# ===================================================================


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return float(np.dot(a, b) / denom)


def unescape_newlines(text: str) -> str:
    """
    En tu CSV guardaste las conversaciones como:
      'LLM: ...\\nuser_x: ...'
    Esto las vuelve a:
      'LLM: ...\nuser_x: ...'
    """
    return text.replace("\\n", "\n")


def load_rows(path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
        for row in reader:
            rows.append(row)
    print(f"[info] Cargadas {len(rows)} filas desde {path}")
    return rows


# ========= Helpers para separar LLM / user y tokenizar ==================


def extract_user_utterance(conv: str) -> str:
    """
    Dada una conversación tipo:
      LLM: ...
      user_x: ...
    devuelve SOLO el contenido tras 'user_x:'.
    Si hubiera varias líneas de usuario, las concatena.
    """
    user_parts: List[str] = []
    for line in conv.splitlines():
        line = line.strip()
        if line.startswith("user_") and ":" in line:
            # user_x: texto...
            _, rest = line.split(":", 1)
            user_parts.append(rest.strip())
    return " ".join(user_parts)


def simple_tokenize(text: str) -> List[str]:
    # Tokenización muy básica, suficiente para Jaccard
    text = text.lower()
    for ch in [",", ".", "?", "!", ";", ":", "(", ")", "\"", "'"]:
        text = text.replace(ch, " ")
    tokens = [t for t in text.split() if t]
    return tokens


def jaccard(a_tokens: List[str], b_tokens: List[str]) -> float:
    set_a = set(a_tokens)
    set_b = set(b_tokens)
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    inter = set_a & set_b
    if not union:
        return 0.0
    return len(inter) / len(union)


# ========= Helpers para evaluar cobertura de slots desde sextetas ========

def normalize_text_for_match(text: str) -> str:
    """
    Normalización suave para comprobación de cobertura:
    lower, sin signos de puntuación básicos.
    """
    text = text.lower()
    for ch in [",", ".", "?", "!", ";", ":", "(", ")", "\"", "'"]:
        text = text.replace(ch, " ")
    text = " ".join(text.split())
    return text


def slot_in_text(slot_value: str, text_norm: str) -> bool:
    """
    Comprueba si slot_value aparece de forma aproximada en text_norm.
    - lower
    - ignora espacios duplicados
    - trata casos tipo 'three times per week' vs 'three times a week'
      de forma naïve, buscando subconjuntos de tokens.
    """
    if not slot_value or slot_value.lower() == "unknown":
        return False

    slot = normalize_text_for_match(slot_value)
    if not slot:
        return False

    # Búsqueda exacta primero
    if slot in text_norm:
        return True

    # Búsqueda por tokens (muy simple)
    slot_tokens = slot.split()
    text_tokens = text_norm.split()
    set_slot = set(slot_tokens)
    set_text = set(text_tokens)
    # cobertura parcial: al menos la mitad de tokens del slot aparecen
    if not set_slot:
        return False
    inter = set_slot & set_text
    return len(inter) >= max(1, len(set_slot) // 2)


def evaluate_slot_coverage(
    sextets_str: str,
    regenerated_user_text: str,
) -> Dict[str, float]:
    """
    Dada la columna sextets_pred (string) y la respuesta regenerada del usuario,
    calcula métricas de cobertura de slots:

      - verb_covered (0/1)
      - pred_covered (0/1)
      - freq_covered (0/1 si frecuencia != 'unknown')
      - cond_covered (0/1 si condición != 'unknown')
      - slot_coverage: media sobre slots relevantes

    Nota: si hay varias sextetas, colapsamos en "alguna sexteta lo contiene".
    Para las pruebas actuales (1 sexteta) esto es trivial.
    """
    try:
        sextets = ast.literal_eval(sextets_str)
    except Exception as e:
        print(f"[warn] No se pudo parsear sextets_pred='{sextets_str}': {e}")
        return {
            "verb_covered": 0.0,
            "pred_covered": 0.0,
            "freq_covered": 0.0,
            "cond_covered": 0.0,
            "slot_coverage": 0.0,
        }

    if not isinstance(sextets, (list, tuple)):
        sextets = [sextets]

    text_norm = normalize_text_for_match(regenerated_user_text)

    any_verb = False
    any_pred = False
    any_freq = False
    any_cond = False

    freq_slots_present = False
    cond_slots_present = False

    for sext in sextets:
        if not isinstance(sext, (list, tuple)) or len(sext) != 6:
            continue
        _, verb, pred, freq, cond, _ = sext

        # verbo
        if slot_in_text(str(verb), text_norm):
            any_verb = True

        # predicado
        if slot_in_text(str(pred), text_norm):
            any_pred = True

        # frecuencia
        if str(freq).lower() != "unknown":
            freq_slots_present = True
            if slot_in_text(str(freq), text_norm):
                any_freq = True

        # condición
        if str(cond).lower() != "unknown":
            cond_slots_present = True
            if slot_in_text(str(cond), text_norm):
                any_cond = True

    # Cálculo de slot_coverage:
    # contamos slots relevantes (freq/cond solo si no son 'unknown')
    vals = [1.0 if any_verb else 0.0, 1.0 if any_pred else 0.0]
    if freq_slots_present:
        vals.append(1.0 if any_freq else 0.0)
    if cond_slots_present:
        vals.append(1.0 if any_cond else 0.0)

    slot_coverage = float(sum(vals) / len(vals)) if vals else 0.0

    return {
        "verb_covered": 1.0 if any_verb else 0.0,
        "pred_covered": 1.0 if any_pred else 0.0,
        "freq_covered": 1.0 if (freq_slots_present and any_freq) else 0.0,
        "cond_covered": 1.0 if (cond_slots_present and any_cond) else 0.0,
        "slot_coverage": slot_coverage,
    }


def main():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    print(f"[info] Cargando modelo de embeddings: {EMB_MODEL_NAME}")
    model = SentenceTransformer(EMB_MODEL_NAME)

    rows = load_rows(INPUT_CSV)

    # Preparamos batch de textos completos y solo usuario
    orig_conv_texts: List[str] = []
    regen_conv_texts: List[str] = []
    orig_user_texts: List[str] = []
    regen_user_texts: List[str] = []

    for row in rows:
        orig_conv = unescape_newlines(row["original_conversation"])
        regen_conv = unescape_newlines(row["regenerated_conversation"])

        orig_user = extract_user_utterance(orig_conv)
        regen_user = extract_user_utterance(regen_conv)

        orig_conv_texts.append(orig_conv)
        regen_conv_texts.append(regen_conv)
        orig_user_texts.append(orig_user)
        regen_user_texts.append(regen_user)

    print("[info] Calculando embeddings para conversaciones originales...")
    emb_orig_conv = model.encode(
        orig_conv_texts, convert_to_numpy=True, show_progress_bar=True
    )

    print("[info] Calculando embeddings para conversaciones regeneradas...")
    emb_regen_conv = model.encode(
        regen_conv_texts, convert_to_numpy=True, show_progress_bar=True
    )

    print("[info] Calculando embeddings para respuestas de usuario originales...")
    emb_orig_user = model.encode(
        orig_user_texts, convert_to_numpy=True, show_progress_bar=True
    )

    print("[info] Calculando embeddings para respuestas de usuario regeneradas...")
    emb_regen_user = model.encode(
        regen_user_texts, convert_to_numpy=True, show_progress_bar=True
    )

    print("[info] Calculando métricas y construyendo filas de salida...")

    scored_rows: List[Dict[str, str]] = []

    for i, row in enumerate(rows):
        orig_conv = orig_conv_texts[i]
        regen_conv = regen_conv_texts[i]
        orig_user = orig_user_texts[i]
        regen_user = regen_user_texts[i]

        # 1) Similitud semántica
        sim_conv = cosine_sim(emb_orig_conv[i], emb_regen_conv[i])
        sim_user = cosine_sim(emb_orig_user[i], emb_regen_user[i])

        # 2) Jaccard sobre la respuesta del usuario
        jac_user = jaccard(
            simple_tokenize(orig_user),
            simple_tokenize(regen_user),
        )

        # 3) Cobertura estructural desde sextetas_pred
        slot_metrics = evaluate_slot_coverage(
            sextets_str=row.get("sextets_pred", ""),
            regenerated_user_text=regen_user,
        )

        scored_row: Dict[str, str] = {
            "idx": row["idx"],
            "user_id": row["user_id"],
            "num_sextets_pred": row.get("num_sextets_pred", ""),
            # semántica
            "sim_conv": f"{sim_conv:.4f}",
            "sim_user": f"{sim_user:.4f}",
            # léxico
            "jaccard_user": f"{jac_user:.4f}",
            # longitudes
            "len_original_conv": str(len(orig_conv)),
            "len_regen_conv": str(len(regen_conv)),
            "len_original_user": str(len(orig_user)),
            "len_regen_user": str(len(regen_user)),
            # estructura
            "verb_covered": f"{slot_metrics['verb_covered']:.4f}",
            "pred_covered": f"{slot_metrics['pred_covered']:.4f}",
            "freq_covered": f"{slot_metrics['freq_covered']:.4f}",
            "cond_covered": f"{slot_metrics['cond_covered']:.4f}",
            "slot_coverage": f"{slot_metrics['slot_coverage']:.4f}",
            # textos (con \n escapado para CSV)
            "original_conversation": orig_conv.replace("\n", "\\n"),
            "regenerated_conversation": regen_conv.replace("\n", "\\n"),
        }

        scored_rows.append(scored_row)

    fieldnames = [
        "idx",
        "user_id",
        "num_sextets_pred",
        # semántica
        "sim_conv",
        "sim_user",
        # léxico
        "jaccard_user",
        # longitudes
        "len_original_conv",
        "len_regen_conv",
        "len_original_user",
        "len_regen_user",
        # estructura
        "verb_covered",
        "pred_covered",
        "freq_covered",
        "cond_covered",
        "slot_coverage",
        # textos
        "original_conversation",
        "regenerated_conversation",
    ]

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()
        for r in scored_rows:
            writer.writerow(r)

    print(f"[done] Resultados con puntuaciones guardados en: {OUTPUT_CSV}")

    # ================== Resumen global por consola =====================

    sims_conv = [float(r["sim_conv"]) for r in scored_rows]
    sims_user = [float(r["sim_user"]) for r in scored_rows]
    jaccs = [float(r["jaccard_user"]) for r in scored_rows]
    coverages = [float(r["slot_coverage"]) for r in scored_rows]

    def summary(name: str, vals: List[float]) -> None:
        if not vals:
            print(f"[info] {name}: sin datos")
            return
        print(
            f"[info] {name}: media={np.mean(vals):.4f}, "
            f"std={np.std(vals):.44f}, "
            f"min={np.min(vals):.4f}, "
            f"max={np.max(vals):.4f}"
        )

    summary("sim_conv", sims_conv)
    summary("sim_user", sims_user)
    summary("jaccard_user", jaccs)
    summary("slot_coverage", coverages)


if __name__ == "__main__":
    main()
