# text2triplet.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple, Iterable
import time
import unicodedata
import re
from datetime import datetime
from utils.make_sqlite_report import make_content_only_report


from utils.config import settings
from triplets2bd.utils.sqlite_client import SqliteClient
from .llm_client import LLMClient, LLMConfig
# Usa tu constants.py como fuente de verdad
from utils.constants import (
    ALLOWED_REL,          # {"padece", "toma", "realiza"}
    ALLOWED_PROP,         # {"categoria", "frecuencia", "gravedad", "inicio", "fin", "se toma", "periodicidad"}
    PROPERTY_VERBS,       # mapeo a nombre normalizado + tipo ("date"/"node")
    RELATION_VERBS,       # {"toma": "persona_toma_medicacion", ...} (para referencia)
    _DATE_FORMATS,        # formatos a intentar
)

# --- Logging (siempre SQLite; solo fallos) ---
from utils.sql_log import (
    ensure_sql_log_table,
    insert_leftovers_log,  # para registrar descartadas (WARN)
    clear_log,             # limpieza de registros (no borra la tabla)
    log_event,             # para registrar errores (ERROR)
    new_run_id,            # generar run_id en memoria
)

# ---- Prompt MEJORADO con formato JSON ----
DEFAULT_CONTEXT = """Eres un extractor de tripletas en ESPAÑOL. Devuelve EXCLUSIVAMENTE tuplas de Python de tres cadenas: ("sujeto", "relación", "objeto"), UNA por línea, sin texto extra.

# ESQUEMA DE NODOS (referencia)
- persona(nombre completo, edad)
- sintoma(nombre común)
- actividad(nombre común)
- medicacion(nombre comercial o genérico)

# RELACIONES ENTRE NODOS (SOLO ESTAS)
- ("<Persona>", "edad", "<edad en formato 'NN años'>")
- ("<Persona>", "realiza", "<Nombre Actividad>")
- ("<Persona>", "padece", "<Nombre Síntoma>")
- ("<Persona>", "toma", "<Nombre Medicación>")

# PROPIEDADES PERMITIDAS (SOLO ESTAS)
- Síntoma: ("<Nombre Síntoma>", "categoria", "<valor>"),
           ("<Nombre Síntoma>", "frecuencia", "<valor>"),
           ("<Nombre Síntoma>", "inicio", "<dd/mm/aaaa>"),
           ("<Nombre Síntoma>", "fin", "<dd/mm/aaaa>"),
           ("<Nombre Síntoma>", "gravedad", "<valor>")
- Actividad: ("<Nombre Actividad>", "categoria", "<valor>"),
             ("<Nombre Actividad>", "frecuencia", "<valor>")
- Medicación: ("<Nombre Medicación>", "se toma", "<periodicidad/indicacion>")

# REGLAS ESTRICTAS
- Formato EXACTO: ("Texto", "texto", "Texto"), con comillas dobles; sin comas finales ni comentarios.
- Respeta mayúsculas, tildes y nombres tal como aparecen en el texto (no conviertas a minúsculas).
- Fechas en formato dd/mm/aaaa si existen.
- Edad SIEMPRE como "<NN> años".
- Para propiedades usa el NOMBRE de la entidad como sujeto (p. ej., "mareos", "yoga", "ibuprofeno").
- NO inventes entidades, NO repitas tripletas, NO incluyas propiedades "nombre".
- SOLO genera las relaciones y propiedades listadas arriba solo si el texto las menciona.
- No inventes categoria o frencuencia si no están en el texto.

# EJEMPLOS VÁLIDOS
("Ana García", "edad", "45 años")
("Ana García", "realiza", "yoga")
("yoga", "frecuencia", "varias_por_semana")
("mareos", "inicio", "15/01/2023")
("mareos", "gravedad", "moderada")
("Ana García", "toma", "ibuprofeno")
("ibuprofeno", "se toma", "cuando duele")

# EJEMPLO NEGATIVO (NO INVENTAR)
Texto: "Juan realiza X"
No devuelvas: ("X", "categoria", "X"), no está en el texto la categoria pues eso con todo.

Devuelve SOLO las tripletas, una por línea, en el formato mostrado.
""".strip()

@dataclass(frozen=True)
class KGConfig:
    model: str = settings.MODEL_KG_GEN or "gpt-4o-mini"
    temperature: float = 0.0
    api_key: Optional[str] = settings.OPENAI_API_KEY
    api_base: Optional[str] = settings.OPENAI_API_BASE

def _make_kg(cfg: KGConfig) -> LLMClient:
    print(f"[text2triplet] Inicializando LLMClient con model='{cfg.model}', temp={cfg.temperature}")
    llm_cfg = LLMConfig(
        api_key=cfg.api_key,
        base_url=cfg.api_base,
        model=cfg.model,
        temperature=cfg.temperature,
    )
    kg = LLMClient(llm_cfg)
    return kg

# --------- Utilidades de normalización ----------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _clean_text(s: str) -> str:
    s2 = _strip_accents(str(s)).strip().lower()
    return " ".join(s2.split())


def _norm_relation(r: str) -> str:
    r2 = _clean_text(r)
    if r2 in ALLOWED_REL or r2 in ALLOWED_PROP:
        return r2
    if r2.endswith("r"):
        base = r2[:-1]
        if base in ALLOWED_REL or base in ALLOWED_PROP:
            return base
    return r2

def _parse_date(s: str) -> Optional[str]:
    txt = _clean_text(s)
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(txt, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

# Extrae tripletas de la respuesta del LLM con varias tolerancias (código, texto, etc.)
_TUPLE_RE = re.compile(
    r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
)

def _extract_triplets_from_llm_response(response_text: str) -> List[Tuple[str, str, str]]:
    triplets: List[Tuple[str, str, str]] = []

    if not response_text:
        return triplets

    # Elimina fences si vienen
    cleaned = response_text.strip()
    cleaned = re.sub(r"^```(?:python|txt|json)?\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)

    # Busca tuplas del tipo ("a","b","c")
    for m in _TUPLE_RE.finditer(cleaned):
        s, r, o = m.groups()
        s_clean = _clean_text(s)
        r_clean = _norm_relation(r)
        o_clean = _clean_text(o)

        # Normalización de propiedades
        if r_clean in PROPERTY_VERBS:
            norm_name, ptype = PROPERTY_VERBS[r_clean]
            r_clean = norm_name
            if ptype == "date":
                parsed = _parse_date(o_clean)
                if parsed:
                    o_clean = parsed

        triplets.append((s_clean, r_clean, o_clean))

    return triplets

def _call_llm_directly(
    kg: LLMClient,
    input_text: str,
    context: str,
    *,
    log_conn=None,
    run_id: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    try:
        response_text = kg.generate(
            input_data=f"Texto: {input_text}\n\nExtrae las tripletas:",
            context=context,
        )
        triplets = _extract_triplets_from_llm_response(response_text)
        return triplets
    except Exception as e:
        # Logueamos solo el error (sin INFO)
        if log_conn is not None:
            try:
                log_event(
                    log_conn,
                    level="ERROR",
                    message="llm call failed",
                    run_id=run_id,
                    stage="text2triplet_llm_generate",
                    reason=type(e).__name__,
                    metadata={"error": str(e), "input_preview": str(input_text)[:200]},
                )
            except Exception:
                pass
        print(f"[text2triplet] Error llamando al LLM: {e}")
        return []

def _normalize_triplets(triplets: Iterable[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for s, r, o in triplets:
        s2, r2, o2 = _clean_text(s), _norm_relation(r), _clean_text(o)
        if r2 in PROPERTY_VERBS:
            norm_name, ptype = PROPERTY_VERBS[r2]
            r2 = norm_name
            if ptype == "date":
                parsed = _parse_date(o2)
                if parsed:
                    o2 = parsed
        out.append((s2, r2, o2))
    return out

# --------- Validación ----------
def _validate_triplet(tri: Tuple[str, str, str]) -> tuple[bool, str]:
    s, r, o = tri
    if r in ALLOWED_REL:
        return True, ""
    if r in {v[0] for v in PROPERTY_VERBS.values()} or r in ALLOWED_PROP:
        rev = {v[0]: v[1] for v in PROPERTY_VERBS.values()}
        ptype = rev.get(r)
        if ptype == "date":
            try:
                datetime.strptime(o, "%Y-%m-%d")
            except Exception:
                return False, f"valor de fecha inválido para {r}: '{o}'"
        return True, ""
    return False, f"relacion no permitida: '{r}'"

def _partition_valid_invalid(triplets: List[Tuple[str, str, str]], drop_invalid: bool):
    valid, invalid = [], []
    for tri in triplets:
        ok, reason = _validate_triplet(tri)
        if ok:
            valid.append(tri)
        else:
            invalid.append((tri, reason))
    return (valid, invalid) if drop_invalid else (triplets, invalid)

# --------- Run principal ----------
def run_kg(
    input_text: str,
    *,
    context: str = DEFAULT_CONTEXT,
    cfg: KGConfig | None = None,
    print_triplets: bool = True,
    drop_invalid: bool = True,
    sqlite_db_path: str = "./data/users/demo.sqlite",
    reset_log: bool = True,  # mismo comportamiento que engine: limpiar log por defecto
    # --- AÑADIDOS (informe opcional) ---
    generate_report: bool = False,
    report_path: Optional[str] = None,
    report_sample_limit: int = 15,
) -> List[Tuple[str, str, str]]:
    """
    Extrae tripletas desde texto usando un LLM y aplica validación básica.
    Logging:
      - Solo se guardan fallos: WARN (descartadas) y ERROR (fallo LLM).
      - El log se limpia por defecto al inicio salvo reset_log=False.
    Informe:
      - Si generate_report=True, se crea un informe del contenido de la SQLite indicada.
    """
    cfg = cfg or KGConfig()
    kg = _make_kg(cfg)

    # Canal de log (siempre SQLite)
    log_sql = SqliteClient(sqlite_db_path)
    ensure_sql_log_table(log_sql.conn)
    try:
        if reset_log:
            clear_log(log_sql.conn)

        # run_id en memoria (solo se escribe si hay fallos)
        run_id = new_run_id("kg")

        t0 = time.time()
        raw_triplets = _call_llm_directly(
            kg, input_text, context,
            log_conn=log_sql.conn,
            run_id=run_id,
        )
        t1 = time.time()
        print("\n=== TEXTO DE ENTRADA ===")
        print(input_text)
        print("========================\n")
        print(f"[text2triplet] LLM completado en {t1 - t0:.2f}s")
        print(f"[text2triplet] Tripletas crudas extraídas: {len(raw_triplets)}")

        norm = _normalize_triplets(raw_triplets)

        valid, rejected = _partition_valid_invalid(norm, drop_invalid=drop_invalid)
        t2 = time.time()

        print(f"[text2triplet] Tiempo total: {t2 - t0:.2f}s")

        # Solo fallos: registrar descartadas como WARN
        if rejected:
            insert_leftovers_log(
                log_sql.conn,
                rejected,
                run_id=run_id,
                stage="text2triplet_validate",
                message="Tripletas descartadas por validación",
            )

        if print_triplets:
            if valid:
                print("\n=== TRIPLETAS (válidas) ===")
                for s, r, o in valid:
                    print(f"({s}, {r}, {o})")
            else:
                print("\n[text2triplet] No hay tripletas válidas.")

            if rejected:
                print("\n=== DESCARTADAS ===")
                for (s, r, o), why in rejected:
                    print(f"({s}, {r}, {o})  -> {why}")
            print()

        result = valid

    except Exception as exc:
        # Solo error de ejecución general
        try:
            log_event(
                log_sql.conn,
                level="ERROR",
                message="text2triplet run failed",
                run_id=run_id,
                stage="end",
                reason=type(exc).__name__,
                metadata={"error": str(exc)},
            )
        except Exception:
            pass
        raise
    finally:
        # Cierra el canal de log primero
        log_sql.close()

    # --- Generación de informe opcional (sin alterar la lógica anterior) ---
    if generate_report:
        out_path = report_path if report_path else sqlite_db_path.replace(".sqlite", "_report.txt")
        make_content_only_report(
            sqlite_db_path,
            out_path,
            sample_limit=report_sample_limit,
        )
        print(f"[text2triplet] Informe generado en: {out_path}")

    return result
