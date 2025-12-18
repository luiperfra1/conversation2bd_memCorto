# triplet2text.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

from utils.config import settings
from .llm_client import LLMClient, LLMConfig

# Tipo de sexteta que usa text2triplet:
# (subject, verb, predicate, frequency, condition, probability)
Sextet = Tuple[str, str, str, str, str, str]


# ---------------------------------------------------------------------------
# PROMPTS: modo "frase suelta" (una frase por sexteta)
# ---------------------------------------------------------------------------

TRIPLET2TEXT_PROMPT_EN = (
    "You are a generator that converts structured behavioral facts into natural language.\n\n"
    "You receive one or more sextets, each in the form:\n"
    "(subject,verb,predicate,frequency/temporality,condition,probability)\n\n"
    "Your job is to generate ONE simple sentence in natural language for EACH sextet.\n"
    "RULES:\n"
    "1) Generate exactly one sentence per input sextet.\n"
    "2) Keep the subject identifier exactly as given (e.g., 'user_paula'). "
    "   Do NOT change it to 'she', 'the user', etc.\n"
    "3) Use the verb in a correct infinitive/appropriate form, but keep the meaning.\n"
    "4) The predicate must clearly appear in the sentence.\n"
    "5) If frequency/temporality is not 'null', integrate it naturally "
    "   (e.g., 'every day', 'weekly', 'on weekends').\n"
    "6) If condition is not 'null' or 'unknown', include it with 'if', 'when', 'unless', etc.\n"
    "7) Ignore the probability explanation in the last field, it is only meta-information. "
    "   You do NOT need to verbalize it.\n"
    "8) Output format: one sentence per line, with NO bullet points, NO numbering, "
    "   and NO extra commentary.\n"
    "9) Sentences should be short and simple, not combining multiple sextets.\n"
).strip()


TRIPLET2TEXT_PROMPT_ES = (
    "Eres un generador que convierte hechos estructurados en lenguaje natural.\n\n"
    "Recibes una o varias sextetas con el formato:\n"
    "(sujeto,verbo,predicado,frecuencia/temporalidad,condición,probabilidad)\n\n"
    "Tu tarea es generar UNA frase sencilla en lenguaje natural por cada sexteta.\n"
    "REGLAS:\n"
    "1) Genera exactamente una frase por cada sexteta de entrada.\n"
    "2) Mantén el identificador de sujeto EXACTAMENTE como viene (por ejemplo, 'user_paula'). "
    "   NO lo cambies a 'ella', 'la usuaria', etc.\n"
    "3) Usa el verbo en una forma correcta (infinitivo o conjugado) manteniendo el sentido.\n"
    "4) El predicado debe aparecer claramente en la frase.\n"
    "5) Si la frecuencia/temporalidad no es 'null', intégrala de forma natural "
    "   (por ejemplo, 'cada día', 'semanalmente', 'los fines de semana').\n"
    "6) Si la condición no es 'null' o 'unknown', inclúyela con 'si', 'cuando', 'a menos que', etc.\n"
    "7) Ignora la explicación de probabilidad del último campo; es metainformación "
    "   que NO necesitas verbalizar.\n"
    "8) Formato de salida: una frase por línea, SIN viñetas, SIN numeración y "
    "   SIN comentarios adicionales.\n"
    "9) Las frases deben ser cortas y sencillas, sin combinar varias sextetas.\n"
).strip()


# ---------------------------------------------------------------------------
# PROMPTS: modo "diálogo" (LLM: ... / user_x: ...)
# ---------------------------------------------------------------------------

TRIPLET2DIALOG_PROMPT_EN = (
    "You are a generator that converts structured behavioral facts into VERY SHORT dialog turns.\n\n"
    "You receive one or more sextets in the form:\n"
    "(subject,verb,predicate,frequency/temporality,condition,probability)\n\n"
    "For EACH sextet you must produce exactly TWO lines:\n"
    "  1) A question from the assistant starting with 'LLM: '\n"
    "  2) An answer from the user starting with '<subject>: '\n\n"
    "RULES:\n"
    "1) Keep the subject IDENTIFIER exactly as given (e.g., 'user_paula').\n"
    "2) The LLM question should naturally ask about the habit/behavior in the sextet.\n"
    "   - Example: 'LLM: Can you tell me about your habit of drinking water?'\n"
    "3) The user answer must clearly express the behavior encoded in the sextet:\n"
    "   - Include verb and predicate.\n"
    "   - Include frequency/temporality when it is not 'null' or 'unknown'.\n"
    "   - Include condition when it is not 'null' or 'unknown'.\n"
    "4) DO NOT verbalize the probability field; it is meta-information.\n"
    "5) Output STRICTLY in this pattern for EACH sextet:\n"
    "   LLM: [question]\n"
    "   <subject>: [answer]\n"
    "   (then immediately the next pair for the next sextet, no bullet points, no numbering).\n"
    "6) No extra comments, no explanations, no blank lines between pairs.\n"
    "7) Sentences must be short and simple.\n"
).strip()


TRIPLET2DIALOG_PROMPT_ES = (
    "Eres un generador que convierte hechos estructurados en pequeños turnos de diálogo.\n\n"
    "Recibes una o varias sextetas con el formato:\n"
    "(sujeto,verbo,predicado,frecuencia/temporalidad,condición,probabilidad)\n\n"
    "Por CADA sexteta debes producir exactamente DOS líneas:\n"
    "  1) Una pregunta del asistente empezando por 'LLM: '\n"
    "  2) Una respuesta del usuario empezando por '<sujeto>: '\n\n"
    "REGLAS:\n"
    "1) Mantén el identificador de sujeto EXACTAMENTE como viene (por ejemplo, 'user_paula').\n"
    "2) La pregunta del LLM debe preguntar de forma natural por el hábito/conducta de la sexteta.\n"
    "   - Ejemplo: 'LLM: ¿Puedes contarme tu hábito de beber agua?'\n"
    "3) La respuesta del usuario debe expresar claramente la conducta codificada en la sexteta:\n"
    "   - Incluye verbo y predicado.\n"
    "   - Incluye frecuencia/temporalidad cuando no sea 'null' o 'unknown'.\n"
    "   - Incluye condición cuando no sea 'null' o 'unknown'.\n"
    "4) NO verbalices el campo de probabilidad; es solo metainformación.\n"
    "5) Formato ESTRICTO de salida por cada sexteta:\n"
    "   LLM: [pregunta]\n"
    "   <sujeto>: [respuesta]\n"
    "   (y a continuación el siguiente par para la siguiente sexteta, sin viñetas ni numeración).\n"
    "6) No añadas comentarios extra ni líneas en blanco entre pares.\n"
    "7) Las frases deben ser cortas y sencillas.\n"
).strip()


# ---------------------------------------------------------------------------
# Config LLM para este módulo
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Triplet2TextConfig:
    """
    Configuración para el módulo inverso (sextet -> texto/diálogo).
    Se parece a KGConfig de text2triplet, pero separada por claridad.
    """
    model: str = settings.MODEL_KG_GEN or "gpt-4o-mini"
    temperature: float = 0.4  # un poco más alto para generar lenguaje natural
    api_key: Optional[str] = settings.OPENAI_API_KEY
    api_base: Optional[str] = settings.OPENAI_API_BASE
    # idioma del prompt: "en" o "es"
    lang: str = "en"


def _make_llm(cfg: Triplet2TextConfig) -> LLMClient:
    print(f"[triplet2text] Inicializando LLMClient con model='{cfg.model}', temp={cfg.temperature}")
    llm_cfg = LLMConfig(
        api_key=cfg.api_key,
        base_url=cfg.api_base,
        model=cfg.model,
        temperature=cfg.temperature,
    )
    return LLMClient(llm_cfg)


def _build_input_from_sextets(sextets: List[Sextet]) -> str:
    """
    Convierte la lista de sextetas en un texto que se pasa al LLM.
    Ejemplo:

    Input sextets:
      [
        ('user_paula','drink','water','daily','when stressed','0.8: ...'),
        ...
      ]

    Texto resultante:

      Sextets:
      (user_paula,drink,water,daily,when stressed,0.8: stated as fact)
      (...)
    """
    lines = ["Sextets:"]
    for s, v, o, f, c, p in sextets:
        # No forzamos lower aquí; usamos tal cual para que el modelo vea la forma original
        line = f"({s},{v},{o},{f},{c},{p})"
        lines.append(line)
    return "\n".join(lines)


def _select_prompt(lang: str) -> str:
    if lang.lower().startswith("es"):
        return TRIPLET2TEXT_PROMPT_ES
    return TRIPLET2TEXT_PROMPT_EN


def _select_dialog_prompt(lang: str) -> str:
    if lang.lower().startswith("es"):
        return TRIPLET2DIALOG_PROMPT_ES
    return TRIPLET2DIALOG_PROMPT_EN


# ---------------------------------------------------------------------------
# API pública: generación de frases (una por sexteta)
# ---------------------------------------------------------------------------

def generate_text_from_sextets(
    sextets: List[Sextet],
    *,
    cfg: Triplet2TextConfig | None = None,
) -> List[str]:
    """
    Dada una lista de sextetas (subject, verb, predicate, frequency, condition, probability),
    genera una frase en lenguaje natural por cada sexteta usando el mismo LLM base.

    Devuelve una lista de frases en el mismo orden que las sextetas.
    """
    if not sextets:
        return []

    cfg = cfg or Triplet2TextConfig()
    llm = _make_llm(cfg)
    context = _select_prompt(cfg.lang)

    input_text = _build_input_from_sextets(sextets)

    response = llm.generate(
        input_data=f"{input_text}\n\nGenerate one sentence per sextet, in order.",
        context=context,
    )

    # Post-procesado simple: una línea = una frase
    raw_lines = [line.strip() for line in response.splitlines()]
    sentences = [l for l in raw_lines if l]

    # Si el modelo devuelve más o menos frases que sextetas, ajustamos:
    # - si hay más, recortamos
    # - si hay menos, rellenamos con cadenas vacías
    if len(sentences) > len(sextets):
        sentences = sentences[: len(sextets)]
    elif len(sentences) < len(sextets):
        sentences = sentences + [""] * (len(sextets) - len(sentences))

    return sentences


def generate_text_from_sextet(
    sextet: Sextet,
    *,
    cfg: Triplet2TextConfig | None = None,
) -> str:
    """
    Versión conveniente para una sola sexteta.
    """
    result = generate_text_from_sextets([sextet], cfg=cfg)
    return result[0] if result else ""


# ---------------------------------------------------------------------------
# API pública: generación de diálogos (LLM: ... / user_x: ...)
# ---------------------------------------------------------------------------

def generate_dialog_from_sextets(
    sextets: List[Sextet],
    *,
    cfg: Triplet2TextConfig | None = None,
) -> List[str]:
    """
    Dada una lista de sextetas, genera para cada una un bloque de texto:

      LLM: ...
      user_x: ...

    Devolvemos una lista de BLOQUES (cadena con dos líneas por sexteta),
    en el mismo orden que las sextetas.
    """
    if not sextets:
        return []

    cfg = cfg or Triplet2TextConfig()
    llm = _make_llm(cfg)
    context = _select_dialog_prompt(cfg.lang)

    input_text = _build_input_from_sextets(sextets)

    response = llm.generate(
        input_data=f"{input_text}\n\nGenerate one LLM/user pair per sextet, in order.",
        context=context,
    )

    # Partimos por líneas y limpiamos
    lines = [l.strip() for l in response.splitlines() if l.strip()]

    # Agrupamos de 2 en 2: (LLM, user)
    blocks: List[str] = []
    for i in range(0, len(lines), 2):
        pair = lines[i:i + 2]
        if not pair:
            continue
        block = "\n".join(pair)
        blocks.append(block)

    # Ajustamos longitud por si el modelo se pasa o se queda corto
    if len(blocks) > len(sextets):
        blocks = blocks[: len(sextets)]
    elif len(blocks) < len(sextets):
        # completamos con cadenas vacías si falta
        blocks += [""] * (len(sextets) - len(blocks))

    return blocks


def generate_dialog_from_sextet(
    sextet: Sextet,
    *,
    cfg: Triplet2TextConfig | None = None,
) -> str:
    """
    Versión conveniente para una sola sexteta.
    """
    blocks = generate_dialog_from_sextets([sextet], cfg=cfg)
    return blocks[0] if blocks else ""


if __name__ == "__main__":
    # Pequeño ejemplo manual para debug rápido
    example_sextet: Sextet = (
        "user_paula",
        "drink",
        "water",
        "daily",
        "when she feels stressed",
        "0.8: stated as a habit",
        )
    cfg = Triplet2TextConfig(lang="en")

    print("=== Sentencia suelta ===")
    print(generate_text_from_sextet(example_sextet, cfg=cfg))

    print("\n=== Diálogo ===")
    print(generate_dialog_from_sextet(example_sextet, cfg=cfg))
