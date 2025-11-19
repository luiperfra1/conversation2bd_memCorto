# conv2text/llm/prompts.py
from datetime import datetime

SYSTEM = (
    "Eres un extractor-resumidor. "
    "Recibes una conversación con turnos 'LLM:' (asistente) y 'user_<nombre>:' (usuario). "
    "Tu salida debe ser ÚNICAMENTE un resumen en frases breves, una idea por frase. "
    "**CRUCIAL: Siempre usar el identificador exacto 'user_<nombre>' como sujeto, NUNCA solo el nombre.**"
    "No inventes ni añadas información no mencionada."
)

FORMAT = (
    "SALIDA: Devuelve exclusivamente el resumen en texto plano, sin encabezados, sin viñetas, "
    "sin JSON ni comillas, sin el prefijo 'Resumen:'."
)

STYLE_RULES = (
    "Reglas de estilo OBLIGATORIAS:\n"
    "1) Siempre escribe el SUJETO con nombre explícito. Evita pronombres.\n"
    "2) Usa tercera persona. Ej.: 'user_antonio sale a correr todas las mañanas.'\n"
    "3) Una idea por frase. Sin 'y' como conector. Cada frase termina en punto.\n"
    "4) Máximo {max_sentences} frases; longitud media (8–14 palabras). Priorizar cohesión sobre fragmentación.\n"    
    "5) Incluye solo hechos actuales o habituales. Ignora recomendaciones, hipótesis o acciones pasadas ya terminadas.\n"
    "6) Si no hay hechos útiles, devuelve cadena vacía.\n"
    ") Manejo de tiempos relativos:\n"
    "   - Fecha actual de referencia: {current_date}\n"
    "   - Para períodos PRECISOS ('desde hace dos meses', 'desde hace 3 semanas'): CALCULAR fecha exacta. Ej: (inicio=2024-07-15)\n"
    "   - Para períodos IMPRECISOS ('desde hace meses', 'desde hace tiempo'): NO añadir fecha\n"
    "   - Para referencias con mes/año ('desde marzo de 2024'): usar formato ISO parcial. Ej: (inicio=2024-03)\n"
    "   - Para días específicos ('ayer', 'mañana', 'el martes que viene'): usar fecha completa ISO. Ej: (inicio=2024-09-14)\n"
)

def build_instruction(max_sentences: int = 10) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")

    return (
        STYLE_RULES.format(max_sentences=max_sentences, current_date=current_date) + "\n\n" +
        FORMAT
    )
