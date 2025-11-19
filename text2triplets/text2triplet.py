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
    ALLOWED_REL,          # {"padece", "toma", "realiza"} (puede que no las uses ahora, pero se mantiene)
    ALLOWED_PROP,         # {"categoria", "frecuencia", "gravedad", "inicio", "fin", "se toma", "periodicidad"}
    PROPERTY_VERBS,       # mapeo a nombre normalizado + tipo ("date"/"node")
    RELATION_VERBS,       # {"toma": "persona_toma_medicacion", ...} (para referencia)
    _DATE_FORMATS,        # formatos a intentar
)

# --- Logging (siempre SQLite; solo errores) ---
from utils.sql_log import (
    ensure_sql_log_table,
    clear_log,             # limpieza de registros (no borra la tabla)
    log_event,             # para registrar errores (ERROR)
    new_run_id,            # generar run_id en memoria
)

# ---- Prompt para generar SEXTETAS ----
SEXTET_PROMPT = (
    "Eres un extractor de tripletas enriquecidas. "
    "Recibes un resumen de conversación en frases simples. "
    "Tu tarea es convertir CADA frase en una sexteta con formato:\n"
    "(sujeto,verbo,predicado,frecuencia/temporalidad,condición,confianza)\n\n"
    
    "REGLAS ESTRICTAS:\n"
    "1) UNA sexteta por frase del resumen. No combines frases.\n"
    "2) SUJETO: Usa exactamente el mismo sujeto que en el resumen (ej: 'user_maria')\n"
    "3) VERBO: Acción principal en infinitivo\n"
    "4) PREDICADO: Objeto/complemento directo\n"
    "5) FRECUENCIA/TEMPORALIDAD: Especifica cuándo ocurre.\n"
    "6) CONDICIÓN: Circunstancia específica.\n"
    "7) CONFIANZA: Evalúa seguridad del hecho:\n"
    
    "FORMATO DE SALIDA:\n"
    "- Una sexteta por línea\n"
    "- Formato exacto: (elemento1,elemento2,elemento3,elemento4,elemento5,elemento6)\n"
    "- Sin texto adicional, sin numeración, sin explicaciones\n"
    "- Si el resumen está vacío, devuelve lista vacía\n"
)

SEXTET_PROMPT_EN = (
    "You are an enriched triplet extractor. "
    "You receive a conversation summary in simple sentences. "
    "Your task is to convert EACH sentence into a sextet with format:\n"
    "(subject,verb,predicate,frequency/temporality,condition,confidence)\n\n"
    
    "STRICT RULES:\n"
    "1) ONE sextet per summary sentence. Do not combine sentences.\n"
    "2) SUBJECT: Use exactly the same subject as in the summary (e.g., 'user_maria')\n"
    "3) VERB: Main action in infinitive form\n"
    "4) PREDICATE: Direct object/complement\n"
    "5) FREQUENCY/TEMPORALITY: Specify when it occurs\n"
    "6) CONDITION: Specific circumstance\n"
    "7) CONFIDENCE: Evaluate fact certainty:\n"
    
    
    "OUTPUT FORMAT:\n"
    "- One sextet per line\n"
    "- Exact format: (element1,element2,element3,element4,element5,element6)\n"
    "- No additional text, no numbering, no explanations\n"
    "- If summary is empty, return empty list\n"
)

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


# --------- Parser: extraer SEXTETAS del texto del LLM ----------
def _extract_sextets_from_llm_response(
    response_text: str,
) -> List[Tuple[str, str, str, str, str, str]]:
    sextets: List[Tuple[str, str, str, str, str, str]] = []

    if not response_text:
        return sextets

    # Elimina fences si vienen
    cleaned = response_text.strip()
    cleaned = re.sub(
        r"^```(?:python|txt|json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)

    # Busca cualquier cosa entre paréntesis: (a,b,c,d,e,f)
    tuple_contents = re.findall(r"\((.*?)\)", cleaned, flags=re.DOTALL)

    for content in tuple_contents:
        # Split básico por comas
        parts = [p.strip().strip('"').strip("'") for p in content.split(",")]

        # Queremos al menos sujeto, verbo, predicado
        if len(parts) < 3:
            continue

        # Forzamos a 6 elementos rellenando con "null"
        while len(parts) < 6:
            parts.append("null")

        s_raw, r_raw, o_raw, freq_raw, cond_raw, conf_raw = parts[:6]

        # Normalizamos sujeto, relación y objeto como antes
        s_clean = _clean_text(s_raw)
        r_clean = _norm_relation(r_raw)
        o_clean = _clean_text(o_raw)

        # Normalización de propiedades tipo fecha
        if r_clean in PROPERTY_VERBS:
            norm_name, ptype = PROPERTY_VERBS[r_clean]
            r_clean = norm_name
            if ptype == "date":
                parsed = _parse_date(o_clean)
                if parsed:
                    o_clean = parsed

        # Limpieza ligera en los demás campos
        freq_clean = (
            _clean_text(freq_raw)
            if freq_raw and freq_raw.lower() != "null"
            else "null"
        )
        cond_clean = (
            _clean_text(cond_raw)
            if cond_raw and cond_raw.lower() != "null"
            else "null"
        )
        conf_clean = (
            _clean_text(conf_raw)
            if conf_raw and conf_raw.lower() != "null"
            else "null"
        )

        sextets.append((s_clean, r_clean, o_clean, freq_clean, cond_clean, conf_clean))

    return sextets


def _call_llm_directly(
    kg: LLMClient,
    input_text: str,
    context: str,
    *,
    log_conn=None,
    run_id: Optional[str] = None,
) -> List[Tuple[str, str, str, str, str, str]]:
    try:
        response_text = kg.generate(
            input_data=f"Texto: {input_text}\n\nExtrae las sextetas:",
            context=context,
        )

        # (Opcional, útil para debug; puedes comentar si no lo quieres siempre)
        # print("\n=== RESPUESTA LLM BRUTA ===")
        # print(response_text)
        # print("=== FIN RESPUESTA LLM BRUTA ===\n")

        sextets = _extract_sextets_from_llm_response(response_text)
        return sextets
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
                    metadata={
                        "error": str(e),
                        "input_preview": str(input_text)[:200],
                    },
                )
            except Exception:
                pass
        print(f"[text2triplet] Error llamando al LLM: {e}")
        return []


def _normalize_sextets(
    sextets: Iterable[Tuple[str, str, str, str, str, str]]
) -> List[Tuple[str, str, str, str, str, str]]:
    """
    Normaliza campos de las sextetas (sujeto, verbo, predicado, frecuencia, condición, confianza).
    NO filtra ni valida nada, solo limpia texto y ajusta propiedades tipo fecha.
    """
    out: List[Tuple[str, str, str, str, str, str]] = []
    for s, r, o, freq, cond, conf in sextets:
        s2, r2, o2 = _clean_text(s), _norm_relation(r), _clean_text(o)

        # Normalización de propiedades tipo fecha, igual que antes
        if r2 in PROPERTY_VERBS:
            norm_name, ptype = PROPERTY_VERBS[r2]
            r2 = norm_name
            if ptype == "date":
                parsed = _parse_date(o2)
                if parsed:
                    o2 = parsed

        freq2 = _clean_text(freq) if freq and freq.lower() != "null" else "null"
        cond2 = _clean_text(cond) if cond and cond.lower() != "null" else "null"
        conf2 = _clean_text(conf) if conf and conf.lower() != "null" else "null"

        out.append((s2, r2, o2, freq2, cond2, conf2))
    return out


# --------- Run principal (sextetas, SIN validación) ----------
def run_kg(
    input_text: str,
    *,
    context: str = SEXTET_PROMPT_EN,
    cfg: KGConfig | None = None,
    print_triplets: bool = True,   # ahora imprime sextetas, se mantiene el nombre por compatibilidad
    drop_invalid: bool = True,     # ya NO se usa; se deja por compatibilidad con main_kg
    sqlite_db_path: str = "./data/users/demo.sqlite",
    reset_log: bool = True,        # mismo comportamiento: limpiar log por defecto
    # --- Informe opcional ---
    generate_report: bool = False,
    report_path: Optional[str] = None,
    report_sample_limit: int = 15,
) -> List[Tuple[str, str, str, str, str, str]]:
    """
    Extrae SEXTETAS desde texto usando un LLM y SOLO aplica normalización básica.
    
    Cambios respecto a la versión anterior:
      - NO se realiza validación ni filtrado de tripletas/sextetas.
      - NO se registran descartadas.
      - TODAS las sextetas devueltas por el LLM (tras normalizar) se usan tal cual.
    
    Logging:
      - Solo se guardan errores (ERROR) en la tabla de log.
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

        # run_id en memoria (solo se escribe si hay errores)
        run_id = new_run_id("kg")

        t0 = time.time()
        raw_sextets = _call_llm_directly(
            kg,
            input_text,
            context,
            log_conn=log_sql.conn,
            run_id=run_id,
        )
        t1 = time.time()
        print("\n=== TEXTO DE ENTRADA ===")
        print(input_text)
        print("========================\n")
        print(f"[text2triplet] LLM completado en {t1 - t0:.2f}s")
        print(f"[text2triplet] Sextetas crudas extraídas: {len(raw_sextets)}")

        norm = _normalize_sextets(raw_sextets)
        t2 = time.time()
        print(f"[text2triplet] Sextetas normalizadas: {len(norm)}")
        print(f"[text2triplet] Tiempo total: {t2 - t0:.2f}s")

        if print_triplets:
            if norm:
                print("\n=== SEXTETAS ===")
                for s, r, o, freq, cond, conf in norm:
                    print(f"({s}, {r}, {o}, {freq}, {cond}, {conf})")
            else:
                print("\n[text2triplet] No hay sextetas extraídas.")
            print()

        result = norm

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
        out_path = (
            report_path
            if report_path
            else sqlite_db_path.replace(".sqlite", "_report.txt")
        )
        make_content_only_report(
            sqlite_db_path,
            out_path,
            sample_limit=report_sample_limit,
        )
        print(f"[text2triplet] Informe generado en: {out_path}")

    return result
