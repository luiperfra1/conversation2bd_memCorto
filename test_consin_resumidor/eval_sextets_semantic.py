# eval_sextets_semantic.py
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

# Opcional: spaCy para similitud semántica
try:
    import spacy
    NLP = spacy.load("en_core_web_md")
    print("[info] spaCy en_core_web_md cargado para similitud semántica.")
except Exception:
    NLP = None
    print("[warn] No se pudo cargar spaCy en_core_web_md. Se usará una similitud más básica.")


# CONFIGURACIÓN
ABLATION_FILE = "test_consin_resumidor/outputs/ablation_conv2text_vs_full.txt"

# pesos por campo en la sexteta (sujeto, verbo, objeto, frecuencia, condición, probabilidad)
WEIGHTS = {
    "subject": 0.15,
    "verb": 0.2,
    "object": 0.2,
    "frequency": 0.2,
    "condition": 0.25,
    # probabilidad la podríamos ignorar o usar con poco peso
    "probability": 0.0,
}
def clean_prob(p):
    """
    Normaliza el campo probabilidad:
      - si ya es float/int → lo deja tal cual (float)
      - si es string tipo '1.0: ....' → se queda solo con el número inicial
      - si no encuentra número → devuelve 0.0
    """
    if isinstance(p, (int, float)):
        return float(p)

    s = str(p).strip()
    m = re.match(r"^([0-9]*\.?[0-9]+)", s)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return 0.0
    return 0.0

@dataclass
class CaseResults:
    case_id: str
    gold: List[Tuple]
    pred_summary: List[Tuple]
    pred_raw: List[Tuple]


# ==========================
#  UTILIDADES DE TEXTO
# ==========================

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = s.strip().lower()
    s = s.replace('"', "").replace("'", "")
    # normalizaciones ligeras para condiciones
    s = s.replace("i'm", "am")
    s = s.replace("when am", "when")
    s = s.replace("feeling ", "")
    s = s.replace("experiencing ", "")
    s = s.replace("having ", "")
    s = s.replace("when i have", "when")
    s = s.replace("when i am", "when")
    s = s.replace("arriving home early", "if arrive home early")
    s = s.replace("when arrive home early", "if arrive home early")
    s = s.replace("when tired", "when tired")
    s = s.replace("when stressed", "when stressed")
    s = s.replace("when sick", "when sick")
    s = s.replace("when headache", "when headache")
    s = s.replace("if i arrive home early", "if arrive home early")
    # espacios múltiples
    s = re.sub(r"\s+", " ", s)
    return s


def semantic_sim(a: str, b: str) -> float:
    """
    Similitud semántica entre dos trozos de texto.
    Usa spaCy si está disponible; si no, usa un fallback simple.
    """
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)

    if not a_norm and not b_norm:
        return 1.0
    if not a_norm or not b_norm:
        return 0.0

    # igualdad exacta tras normalización
    if a_norm == b_norm:
        return 1.0

    # Si hay NLP, usamos embeddings
    if NLP is not None:
        doc1 = NLP(a_norm)
        doc2 = NLP(b_norm)
        return float(doc1.similarity(doc2))

    # Fallback simple: intersección de palabras
    set1 = set(a_norm.split())
    set2 = set(b_norm.split())
    if not set1 or not set2:
        return 0.0
    inter = len(set1 & set2)
    union = len(set1 | set2)
    return inter / union


# ==========================
#  PARSEO DEL FICHERO ABLATION
# ==========================

def parse_ablation_file(path: str) -> List[CaseResults]:
    """
    Lee el fichero de ablation y extrae:
      - GOLD
      - PRED_SUMMARY (text2triplets con resumen)
      - PRED_RAW (text2triplets con conversación completa)
    para cada CASO.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encuentra el fichero de ablation: {path}")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cases: List[CaseResults] = []

    current_case_id: Optional[str] = None
    section: Optional[str] = None  # "summary", "raw", "gold"
    pred_summary: List[Tuple] = []
    pred_raw: List[Tuple] = []
    gold: List[Tuple] = []

    def flush_case():
        nonlocal current_case_id, pred_summary, pred_raw, gold, cases
        if current_case_id is not None:
            cases.append(
                CaseResults(
                    case_id=current_case_id,
                    gold=list(gold),
                    pred_summary=list(pred_summary),
                    pred_raw=list(pred_raw),
                )
            )
        current_case_id = None
        pred_summary = []
        pred_raw = []
        gold = []

    for line in lines:
        line_stripped = line.strip()

        # Inicio de caso
        if line_stripped.startswith("CASO: "):
            # guardar el caso anterior
            flush_case()
            current_case_id = line_stripped.split("CASO: ")[1].strip()
            section = None
            continue

        # Secciones
        if line_stripped.startswith("[text2triplets] RESULTADOS usando RESUMEN conv2text"):
            section = "summary"
            continue
        if line_stripped.startswith("[text2triplets] RESULTADOS usando CONVERSACIÓN completa"):
            section = "raw"
            continue
        if line_stripped.startswith("[GOLD]"):
            section = "gold"
            continue

        # Líneas con sextetas: "01. ('user', 'verb', ...)"
        if re.match(r"^\d+\.\s*\(", line_stripped):
            if section is None:
                continue
            # extraer la parte de la tupla después del "01. "
            try:
                _, tuple_part = line_stripped.split(".", 1)
                tuple_part = tuple_part.strip()
                # esperamos formato: (subj, verb, obj, freq, cond, prob)
                sextet = ast.literal_eval(tuple_part)
                if isinstance(sextet, tuple) and len(sextet) >= 6:
                    subj, verb, obj, freq, cond, prob = sextet[:6]
                    prob_clean = clean_prob(prob)
                    sextet_clean = (subj, verb, obj, freq, cond, prob_clean)
                else:
                    sextet_clean = sextet  # por si acaso, no rompe

                if section == "summary":
                    pred_summary.append(sextet_clean)
                elif section == "raw":
                    pred_raw.append(sextet_clean)
                elif section == "gold":
                    gold.append(sextet_clean)
            except Exception:
                continue

    # flush final
    flush_case()

    return cases


# ==========================
#  SCORING DE SEXTETAS
# ==========================

def score_sextet(gold: Tuple, pred: Tuple) -> float:
    """
    Calcula una puntuación [0,1] entre una sexteta gold y una predicha,
    usando similitud semántica campo a campo.
    Formato esperado:
      (subject, verb, object, frequency, condition, probability)
    """
    # seguridad
    if len(gold) < 6 or len(pred) < 6:
        return 0.0

    g_subj, g_verb, g_obj, g_freq, g_cond, g_prob = gold
    p_subj, p_verb, p_obj, p_freq, p_cond, p_prob = pred

    scores = {}

    scores["subject"] = 1.0 if normalize_text(g_subj) == normalize_text(p_subj) else semantic_sim(g_subj, p_subj)
    scores["verb"] = semantic_sim(g_verb, p_verb)
    scores["object"] = semantic_sim(g_obj, p_obj)
    scores["frequency"] = semantic_sim(g_freq, p_freq)
    scores["condition"] = semantic_sim(g_cond, p_cond)
    # probabilidad: podrías usar algo tipo 1 - |g_prob - p_prob|, pero muchas veces
    # viene como texto, así que lo ignoramos (peso 0).
    scores["probability"] = 1.0  # neutro; peso casi cero

    num = 0.0
    den = 0.0
    for field, w in WEIGHTS.items():
        num += w * scores[field]
        den += w

    if den == 0.0:
        return 0.0
    return num / den


def best_alignment_score(gold_list: List[Tuple], pred_list: List[Tuple]) -> float:
    """
    Calcula una puntuación media max-match:
      para cada gold, coge el pred que más se le parece.
    Es simple pero razonable dado que tienes pocas sextetas por caso.
    """
    if not gold_list and not pred_list:
        return 1.0
    if not gold_list or not pred_list:
        return 0.0

    total = 0.0
    for g in gold_list:
        best = 0.0
        for p in pred_list:
            s = score_sextet(g, p)
            if s > best:
                best = s
        total += best

    return total / len(gold_list)


# ==========================
#  MAIN
# ==========================

# ==========================
#  MAIN
# ==========================

def format_sextet_list(name: str, sextets: List[Tuple]) -> str:
    if not sextets:
        return f"{name}: (vacío)"
    lines = [f"{name}:"]
    for i, s in enumerate(sextets, start=1):
        lines.append(f"  {i:02d}. {s}")
    return "\n".join(lines)

def main():
    cases = parse_ablation_file(ABLATION_FILE)
    if not cases:
        print("[error] No se han encontrado casos para evaluar.")
        return

    print(f"[info] Casos encontrados: {len(cases)}")

    scores_summary = []
    scores_raw = []

    for c in cases:
        s_sum = best_alignment_score(c.gold, c.pred_summary)
        s_raw = best_alignment_score(c.gold, c.pred_raw)

        scores_summary.append(s_sum)
        scores_raw.append(s_raw)

        print("=" * 80)
        print(f"CASE: {c.case_id}")
        print(f"  - Score (using SUMMARY): {s_sum:.3f}")
        print(f"  - Score (using RAW conv): {s_raw:.3f}")
        print(f"  - #gold={len(c.gold)} | #pred_summary={len(c.pred_summary)} | #pred_raw={len(c.pred_raw)}")

        # Imprimir sextetas con la prob ya limpiada
        print(format_sextet_list("  GOLD", c.gold))
        print(format_sextet_list("  PRED_SUMMARY", c.pred_summary))
        print(format_sextet_list("  PRED_RAW", c.pred_raw))
        print()  # línea en blanco

    # Resumen global
    def avg(lst: List[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    print("\n" + "=" * 80)
    print("RESUMEN GLOBAL")
    print(f"  - Media score SUMMARY: {avg(scores_summary):.3f}")
    print(f"  - Media score RAW:      {avg(scores_raw):.3f}")


if __name__ == "__main__":
    main()

