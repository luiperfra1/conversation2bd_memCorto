# Ejemplos variados para probar el extractor con distintos retos

# Caso base: síntoma + medicación con periodicidad
TEXT1 = "José padece insomnio. José toma paracetamol todas las noches."

# Actividad + síntoma con gravedad + frecuencia
TEXT2 = "María realiza caminar diariamente y María padece dolor lumbar moderado."

# Medicación con indicación + actividad con frecuencia
TEXT3 = "Carlos toma ibuprofeno cuando duele. Carlos realiza yoga varias veces por semana."

# Resumen más rico, varias oraciones y propiedades
TEXT4 = (
    "na realiza natación tres veces por semana para mantenerse activa. "
    "Desde el 15/01/2023 Ana padece mareos de gravedad moderada. "
    "Ana toma ibuprofeno cuando duele."
)

# Negación explícita (no debe generar ninguna tripleta de toma)
TEXT5 = "Juan no toma ninguna medicación actualmente."

# Recomendación/hipótesis (no debería generar toma)
TEXT6 = "El médico le recomendó a Raúl tomar ibuprofeno si aparece dolor."

# Dos personas + relación social + actividades distintas
TEXT7 = (
    "Luis conoce a Marta desde hace años. "
    "Luis realiza caminar diariamente. "
    "Marta realiza yoga los fines de semana."
)

# Ruido conversacional, debería extraer lo esencial
TEXT8 = (
    "Pues mira, últimamente estoy fatal con el sueño, la verdad. "
    "Yo, Elena, intento moverme: yo realizo caminar a diario, aunque sea media hora. "
    "Por las noches tomo valeriana para ver si descanso mejor; sigo con insomnio."
)

# Plan futuro (no debería crear actividad)
TEXT9 = "Sofía planea empezar a correr la semana que viene."

# Ambiguo / alergia (puede o no extraerse según tu ontología)
TEXT10 = "Pedro es alérgico al polen y a veces estornuda."

# Múltiples propiedades juntas
TEXT11 = (
    "Desde el 10/09/2025 Miguel padece dolor cervical leve. "
    "Miguel realiza pilates a diario. "
    "Miguel toma naproxeno cada 8 horas cuando duele."
)
TEXT12 =("Sara toma levotiroxina en ayunas cada mañana. Sara hace pilates dos veces por semana.")


# Mapa para CLI u otras herramientas
ALL_TEXTS = {
    "TEXT1": TEXT1,   # básico: síntoma + medicación
    "TEXT2": TEXT2,   # actividad + síntoma + gravedad
    "TEXT3": TEXT3,   # medicación con indicación + actividad
    "TEXT4": TEXT4,   # resumen rico con propiedades
    "TEXT5": TEXT5,   # negación
    "TEXT6": TEXT6,   # recomendación (hipotético)
    "TEXT7": TEXT7,   # dos personas + relación social
    "TEXT8": TEXT8,   # ruido conversacional
    "TEXT9": TEXT9,   # plan futuro
    "TEXT10": TEXT10, # alergia (fuera de ontología)
    "TEXT11": TEXT11, # propiedades múltiples + frecuencia + periodicidad
    "TEXT12": TEXT12, # múltiples oraciones con misma persona
}
