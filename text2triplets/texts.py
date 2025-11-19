# Ejemplos variados para probar el extractor con distintos retos

# Caso base: síntoma + medicación con periodicidad
TEXT1 = "user_jose padece insomnio. user_jose toma paracetamol todas las noches."

# Actividad + síntoma con gravedad + frecuencia
TEXT2 = "user_maria camina diariamente. user_maria padece dolor lumbar moderado."

# Medicación con indicación + actividad con frecuencia
TEXT3 = "user_carlos toma ibuprofeno cuando duele. user_carlos practica yoga varias veces por semana."

# Resumen más rico, varias oraciones y propiedades
TEXT4 = (
    "user_ana realiza natación tres veces por semana. "
    "user_ana padece mareos moderados desde 2023-01-15. "
    "user_ana toma ibuprofeno cuando duele."
)

# Negación explícita (no debe generar ninguna tripleta de toma)
TEXT5 = "user_juan no toma ninguna medicación actualmente."

# Recomendación/hipótesis (no debería generar toma)
TEXT6 = "El médico recomendó a user_raul tomar ibuprofeno si aparece dolor."

# Dos personas + relación social + actividades distintas
TEXT7 = (
    "user_luis conoce a user_marta desde hace años. "
    "user_luis camina diariamente. "
    "user_marta practica yoga los fines de semana."
)

# Ruido conversacional, debería extraer lo esencial
TEXT8 = (
    "user_elena padece insomnio. "
    "user_elena camina a diario. "
    "user_elena toma valeriana por las noches."
)

# Plan futuro (no debería crear actividad)
TEXT9 = "user_sofia planea empezar a correr la semana que viene."

# Ambiguo / alergia (puede o no extraerse según tu ontología)
TEXT10 = "user_pedro es alérgico al polen. user_pedro estornuda a veces."

# Múltiples propiedades juntas
TEXT11 = (
    "user_miguel padece dolor cervical leve desde 2025-09-10. "
    "user_miguel practica pilates a diario. "
    "user_miguel toma naproxeno cada 8 horas cuando duele."
)

TEXT12 = "user_sara toma levotiroxina en ayunas cada mañana. user_sara practica pilates dos veces por semana."

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