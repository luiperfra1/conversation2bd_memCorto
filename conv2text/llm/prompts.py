# conv2text/llm/prompts.py
from datetime import datetime

SYSTEM = (
    "Eres un extractor-resumidor en ESPAÑOL. "
    "Recibes una conversación con turnos 'LLM:' (asistente) y 'user_<nombre>:' (usuario). "
    "Tu salida debe ser ÚNICAMENTE un resumen en frases breves, una idea por frase, "
    "centradas en HECHOS afirmados por el usuario. No inventes ni uses contenido de 'LLM:' salvo confirmación explícita."
)



SCHEMA_HINT = (
    "Relevancia: Actividad (nombre, frecuencia, categoría), Medicación (tipo, periodicidad), "
    "Síntoma (tipo, inicio/fin, gravedad, frecuencia, categoría), Persona (nombre, edad). "
    "No inventes campos. Usa lo que el usuario afirma explícitamente."
)

FORMAT = (
    "SALIDA: Devuelve exclusivamente el resumen en texto plano, sin encabezados, sin viñetas, "
    "sin JSON ni comillas, sin el prefijo 'Resumen:'."
)

STYLE_RULES = (
    "Reglas de estilo OBLIGATORIAS:\n"
    "1) Siempre escribe el SUJETO con nombre explícito. Evita pronombres.\n"
    "2) Usa tercera persona. Ej.: '<nombre> sale a correr.'\n"
    "3) Para propiedades adicionales, permite sujeto conceptual: 'Correr se hace todas las mañanas.'\n"
    "4) Una idea por frase. Sin 'y' como conector. Cada frase termina en punto.\n"
    "5) Máximo {max_sentences} frases; breves (6–14 palabras aprox.).\n"
    "6) Incluye solo hechos actuales o habituales. Ignora recomendaciones, hipótesis o acciones pasadas ya terminadas.\n"
    "7) Si no hay hechos útiles, devuelve cadena vacía.\n"
    "8) Manejo de tiempos relativos:\n"
    "   - Fecha actual de referencia: {current_date}\n"
    "   - Para períodos PRECISOS ('desde hace dos meses', 'desde hace 3 semanas'): CALCULAR fecha exacta. Ej: (inicio=2024-07-15)\n"
    "   - Para períodos IMPRECISOS ('desde hace meses', 'desde hace tiempo'): NO añadir fecha\n"
    "   - Para referencias con mes/año ('desde marzo de 2024'): usar formato ISO parcial. Ej: (inicio=2024-03)\n"
    "   - Para días específicos ('ayer', 'mañana', 'el martes que viene'): usar fecha completa ISO. Ej: (inicio=2024-09-14)\n"
)

NEGATIVE_RULES = (
    "EXCLUIR por completo:\n"
    "- Recomendaciones o condicionales ('el médico dijo que...', 'podría tomar...', 'si vuelve el dolor...').\n"
    "- Vida no sanitaria ('trabajo desde casa', 'vi una película').\n"
    "- Opiniones/emociones generales ('estoy bien', 'me siento feliz').\n"
    "- Negaciones puras ('no tengo síntomas', 'no tomo nada'): si solo hay esto, devuelve cadena vacía."
)


def build_instruction(max_sentences: int = 10) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")

    return (
        STYLE_RULES.format(max_sentences=max_sentences, current_date=current_date) + "\n\n" +
        SCHEMA_HINT + "\n\n" +
       # CONTEXT_RULES + "\n\n" +
        NEGATIVE_RULES + "\n\n" +
        FORMAT
    )
