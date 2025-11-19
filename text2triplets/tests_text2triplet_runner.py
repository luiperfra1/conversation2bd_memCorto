# tests_text2triplet_runner.py
# Ejecuta baterías de pruebas para text2triplet.run_kg sin pytest.
from __future__ import annotations

import time
from typing import List, Tuple, Dict, Any

# Importaciones tolerantes (package vs script)
try:
    # Si está en un paquete (p.ej. python -m pkg.tests_text2triplet_runner)
    from .text2triplet import run_kg, KGConfig, DEFAULT_CONTEXT, _normalize_triplets
except Exception:
    # Import absoluto (p.ej. python tests_text2triplet_runner.py)
    from text2triplet import run_kg, KGConfig, DEFAULT_CONTEXT, _normalize_triplets  # type: ignore


Triplet = Tuple[str, str, str]
CORE_RELS = {"realiza", "padece", "toma", "conoce"}


def _as_set(tris: List[Triplet]) -> set[Triplet]:
    return set(tris)


def _pretty(tris: List[Triplet]) -> str:
    if not tris:
        return "(ninguna)"
    return "\n".join(f"({s}, {r}, {o})" for s, r, o in tris)


def _metrics(expected: set[Triplet], got: set[Triplet]) -> Dict[str, float]:
    tp = len(expected & got)
    fp = len(got - expected)
    fn = len(expected - got)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1}


def _normalize_expected(expected_human: List[Triplet]) -> List[Triplet]:
    """Normaliza usando el mismo pipeline interno para comparar en igualdad."""
    return _normalize_triplets(expected_human)  # type: ignore


def _looks_like_name(s: str) -> bool:
    """Heurística simple: empieza con mayúscula y no es una palabra de actividad/síntoma típica."""
    if not s or not s[0].isalpha() or not s[0].isupper():
        return False
    blacklist = {
        "caminar", "correr", "yoga", "pasear", "pilates", "ciclismo", "natación",
        "insomnio", "cefalea", "migrañas", "mareos", "dolor lumbar", "dolor cervical",
        "dolor de espalda"
    }
    return s.lower() not in blacklist


def _lint_expected_subjects(expected: List[Triplet], case_name: str) -> None:
    """Avisa si algún sujeto de relaciones núcleo no parece un nombre propio."""
    for s, r, o in expected:
        if r in CORE_RELS and not _looks_like_name(s):
            print(f"[LINT] Caso '{case_name}': el sujeto '{s}' en relación '{r}' "
                  f"no parece nombre propio. Revisa el texto esperado.")


def run_case(
    name: str,
    text: str,
    expected_human: List[Triplet],
    *,
    context: str = DEFAULT_CONTEXT,
    cfg: KGConfig | None = None,
    drop_invalid: bool = True,
    print_details: bool = True,
) -> Dict[str, Any]:
    """Ejecuta un caso y devuelve dict con métricas y detalles."""
    _lint_expected_subjects(expected_human, name)

    # Normalizamos expected con la misma lógica interna
    expected_norm = _normalize_expected(expected_human)
    expected_set = _as_set(expected_norm)

    t0 = time.time()
    got = run_kg(
        input_text=text,
        context=context,
        cfg=cfg,
        drop_invalid=drop_invalid,
        print_triplets=False,  # silenciamos el volcado interno
    )
    dt = time.time() - t0
    got_set = _as_set(got)

    metrics = _metrics(expected_set, got_set)
    failed = list(expected_set - got_set)
    extra = list(got_set - expected_set)

    if print_details:
        print(f"\n=== CASO: {name} ===")
        print(f"Texto: {text}")
        print(f"Tiempo: {dt:.2f}s")
        print("\nEsperado (normalizado):")
        print(_pretty(sorted(expected_set)))
        print("\nObtenido:")
        print(_pretty(sorted(got_set)))
        if failed:
            print("\nFaltan (FN):")
            print(_pretty(sorted(failed)))
        if extra:
            print("\nSobrantes (FP):")
            print(_pretty(sorted(extra)))
        print("\nMétricas: "
              f"precision={metrics['precision']:.2f}, recall={metrics['recall']:.2f}, f1={metrics['f1']:.2f}")

    return {
        "name": name,
        "text": text,
        "time": dt,
        "expected": sorted(expected_set),
        "got": sorted(got_set),
        "missing": sorted(failed),
        "extra": sorted(extra),
        "metrics": metrics,
    }


def run_all_tests(model_override: str | None = None) -> Dict[str, Any]:
    """Ejecuta la batería de pruebas. Devuelve resumen con nota (0–10)."""
    cfg = KGConfig(model=model_override) if model_override else None

    cases: List[Dict[str, Any]] = []

    # --- C (narrativo rico, sujeto con nombre en todas las oraciones) ---
    cases.append(run_case(
        "C1 - Juan: rutina + síntoma con inicio/gravedad + medicación contextual",
        ("Resumen: Juan realiza caminar cada mañana antes de trabajar y Juan realiza yoga dos veces por semana. "
         "Desde el 01/03/2024 Juan padece dolor de rodilla de gravedad moderada. "
         "Cuando aparece el dolor, Juan toma ibuprofeno cuando duele."),
        expected_human=[
            ("Juan", "realiza", "caminar"),
            ("caminar", "frecuencia", "diaria"),
            ("Juan", "realiza", "yoga"),
            ("yoga", "frecuencia", "varias_por_semana"),
            ("Juan", "padece", "dolor de rodilla"),
            ("dolor de rodilla", "inicio", "01/03/2024"),
            ("dolor de rodilla", "gravedad", "moderada"),
            ("Juan", "toma", "ibuprofeno"),
            ("ibuprofeno", "se toma", "cuando duele"),
        ],
        cfg=cfg
    ))

    # --- B (mixtos, frecuentes) ---
    cases.append(run_case(
        "B1 - María: actividad + síntoma con gravedad",
        "María realiza caminar diariamente y María padece dolor lumbar moderado.",
        expected_human=[
            ("María", "realiza", "caminar"),
            ("caminar", "frecuencia", "diaria"),
            ("María", "padece", "dolor lumbar"),
            ("dolor lumbar", "gravedad", "moderada"),
        ],
        cfg=cfg
    ))

    cases.append(run_case(
        "B2 - Carlos: medicación con indicación + actividad con frecuencia",
        "Carlos toma ibuprofeno cuando duele y Carlos realiza yoga varias veces por semana.",
        expected_human=[
            ("Carlos", "toma", "ibuprofeno"),
            ("ibuprofeno", "se toma", "cuando duele"),
            ("Carlos", "realiza", "yoga"),
            ("yoga", "frecuencia", "varias_por_semana"),
            # La categoría de actividad puede no estar en el texto; la omitimos para no sesgar recall.
        ],
        cfg=cfg
    ))

    cases.append(run_case(
        "B3 - José: combinación completa con medicación pautada",
        "José padece insomnio y José toma paracetamol cada 8 horas. José realiza correr semanalmente.",
        expected_human=[
            ("José", "padece", "insomnio"),
            ("José", "toma", "paracetamol"),
            ("paracetamol", "se toma", "cada 8 horas"),
            ("José", "realiza", "correr"),
            ("correr", "frecuencia", "semanal"),
        ],
        cfg=cfg
    ))

    # --- A (básicos) ---
    cases.append(run_case(
        "A1 - Luis: síntoma simple",
        "Luis padece insomnio.",
        expected_human=[
            ("Luis", "padece", "insomnio"),
        ],
        cfg=cfg
    ))

    cases.append(run_case(
        "A2 - Marcos: actividad simple",
        "Marcos realiza yoga.",
        expected_human=[
            ("Marcos", "realiza", "yoga"),
        ],
        cfg=cfg
    ))

    # --- D (edge cases con nombre explícito para no confundir al extractor) ---
    cases.append(run_case(
        "D1 - Juan: negación explícita de medicación",
        "Juan no toma ninguna medicación actualmente.",
        expected_human=[
            # Debe ser vacío
        ],
        cfg=cfg
    ))

    cases.append(run_case(
        "D2 - Juan: recomendación/hipótesis (no hecho real)",
        "El médico le recomendó a Juan tomar ibuprofeno si aparece dolor. Pero el no lo va a tomar",
        expected_human=[
            # No debe generar 'Juan toma ibuprofeno'
        ],
        cfg=cfg
    ))

    cases.append(run_case(
        "D3 - María: fecha inválida en propiedad (se conserva el hecho principal)",
        "María padece cefalea desde el 2024/13/40.",
        expected_human=[
            # La fecha es inválida y debe descartarse. Se mantiene solo el hecho del síntoma.
            ("María", "padece", "cefalea"),
        ],
        cfg=cfg
    ))

    # --- Resumen ---
    f1s = [c["metrics"]["f1"] for c in cases]
    mean_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    nota = round(mean_f1 * 10, 2)

    print("\n=== RESUMEN GLOBAL ===")
    for c in cases:
        name = c["name"]
        f1 = c["metrics"]["f1"]
        print(f"- {name}: F1={f1:.2f}")
    print(f"\nNota global (0-10): {nota:.2f}")

    return {"nota": nota, "mean_f1": mean_f1, "cases": cases}


if __name__ == "__main__":
    # Permite override rápido por variable de entorno si hiciera falta
    import os
    model = os.environ.get("KG_TEST_MODEL", None)
    run_all_tests(model_override=model)
