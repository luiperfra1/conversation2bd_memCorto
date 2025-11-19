# conv2text/texts.py
"""
Colección de conversaciones de ejemplo (versión compacta y variada).
Formato: 'LLM:' y 'user_<nombre>:'.
Cada entrada prueba un tipo diferente de comportamiento.
"""

ALL_TEXTS = {

    # === Caso base simple: actividad + medicación + síntoma ===
    "TEXT1": """LLM: ¿Qué sueles hacer por las mañanas?
user_juan: Salgo a correr cada día y tomo ibuprofeno cuando me duele la cabeza.
LLM: ¿Te notas algún síntoma habitual?
user_juan: Nada grave, solo algo de cansancio a veces.
""",

    # === Actividad + síntoma con tiempo definido ===
    "TEXT2": """LLM: ¿Cómo te encuentras últimamente?
user_marta: Desde marzo de 2024 me duele la espalda, pero camino media hora cada tarde.
""",

    # === Medicación regular y ejercicio habitual ===
    "TEXT3": """LLM: ¿Cuál es tu rutina diaria?
user_pedro: Voy al gimnasio tres veces por semana y tomo metformina cada mañana.
""",

    # === Síntoma persistente + actividad relajante ===
    "TEXT4": """LLM: ¿Duermes bien?
user_lucia: Tengo insomnio desde hace dos meses.
LLM: ¿Realizas alguna actividad física?
user_lucia: Hago yoga los fines de semana para relajarme.
""",

    # === Caso ambiguo: recomendación médica, sin acción real ===
    "TEXT5": """LLM: ¿Tomas algún medicamento?
user_eduardo: El médico me dijo que empiece con amoxicilina si vuelve el dolor de garganta, pero no la estoy tomando.
""",

    # === Caso de negación completa (no hay información útil) ===
    "TEXT6": """LLM: ¿Tienes algún síntoma o tomas medicación?
user_javier: No tengo síntomas y no tomo nada ahora mismo.
""",

    # === Caso con pasado + presente (mezcla temporal) ===
    "TEXT7": """LLM: ¿Cómo te encuentras hoy?
user_laura: Ayer tuve fiebre, pero hoy estoy bien. Tomé ibuprofeno y descansé. Suelo hacer pilates los martes y jueves.
""",

    # === Caso de interrupción de hábitos (actividad suspendida) ===
    "TEXT8": """LLM: ¿Haces deporte últimamente?
user_ines: Antes iba al gimnasio, pero lo he dejado porque estoy de viaje. A veces tomo vitamina D cuando me acuerdo.
""",

    # === Caso emocional / psicológico ===
    "TEXT9": """LLM: ¿Cómo te sientes últimamente?
user_sandra: Estoy algo nerviosa y duermo mal. Hago yoga por las mañanas y tomo lorazepam por las noches desde hace un mes.
""",

    # === Caso mixto con enfermedad diagnosticada ===
    "TEXT10": """LLM: Cuéntame tu día a día.
user_pablo: Trabajo desde casa y hago bicicleta estática por las mañanas. Soy diabético tipo 2 desde hace 5 años y tomo metformina dos veces al día.
""",

    # === Caso largo y variado: combina síntomas, emociones y rutinas ===
    "TEXT11": """LLM: Cuéntame cómo han sido tus últimas semanas.
user_clara: Han sido algo pesadas. Desde hace meses tengo dolor cervical leve, sobre todo al final del día. 
Voy a nadar los sábados, camino casi todos los días y practico algo de meditación antes de dormir. 
Tomo simvastatina cada noche porque tengo colesterol alto, y mi médico me dijo que controle la dieta. 
A veces me cuesta dormir por el estrés, pero intento no preocuparme demasiado. 
LLM: ¿Notas alguna mejoría con el ejercicio?
user_clara: Sí, cuando hago ejercicio me siento mejor, aunque el dolor vuelve si paso mucho tiempo frente al ordenador.
""",

    # === Caso sin información relevante (ruido conversacional) ===
    "TEXT12": """LLM: ¿Qué tal el fin de semana?
user_david: Bien, estuve con mi familia y vimos una película. No he hecho nada especial.
LLM: ¿Y de salud?
user_david: Todo normal, nada nuevo que contar.
""",

    # === Caso negativo-condicional (hipotético) ===
    "TEXT13": """LLM: ¿Te ha recetado algo el médico?
user_rocio: Me dijo que podría tomar paracetamol si volvía el dolor, pero no lo he necesitado.
""",

    # === Caso físico leve + actividad social ===
    "TEXT14": """LLM: ¿Cómo va tu salud últimamente?
user_maria: Bien, solo congestión nasal leve por alergia. Camino con mi hija cada tarde y voy a pilates los sábados.
""",

    # === Caso emocional prolongado + tratamiento constante ===
    "TEXT15": """LLM: ¿Cómo te encuentras estos días?
user_ernesto: Llevo semanas durmiendo mal y con mucha ansiedad. 
Intento relajarme escuchando música y hago estiramientos por la tarde. 
Tomo lorazepam desde hace tres meses.
""",

    # === Caso extenso y detallado: síntomas, emociones, rutinas y seguimiento médico ===
"TEXT16": """LLM: ¿Cómo te encuentras estos días?
user_ernesto: Llevo semanas durmiendo mal y con mucha ansiedad. Me despierto varias veces durante la noche, sobre todo cuando tengo preocupaciones del trabajo. 
Intento relajarme escuchando música antes de dormir, pero a veces no me funciona. También hago estiramientos por la tarde y camino unos veinte minutos después de cenar. 
Tomo lorazepam desde hace tres meses porque el médico me lo recetó para la ansiedad. En general me ayuda, aunque últimamente noto que el efecto dura menos.

LLM: ¿Has notado algún otro síntoma físico?
user_ernesto: Sí, dolor de cuello y algo de tensión en los hombros, sobre todo cuando paso mucho tiempo frente al ordenador. A veces me da taquicardia leve, pero desaparece cuando respiro hondo. 
No tengo fiebre ni nada más grave.

LLM: ¿Sigues alguna rutina de ejercicio o alimentación?
user_ernesto: Intento comer sano entre semana, aunque los fines de semana suelo comer fuera. Practico yoga una vez a la semana y a veces salgo en bici con un amigo los domingos, pero no siempre. 
He pensado en apuntarme a natación, aunque me cuesta organizarme.

LLM: ¿El sueño ha mejorado o sigue igual?
user_ernesto: Un poco mejor que al principio, pero sigo despertándome al menos dos o tres veces cada noche. Cuando descanso bien al día siguiente me siento más tranquilo. 
También noto que si tomo el lorazepam demasiado tarde, me levanto algo mareado.

LLM: ¿Has hablado de esto con tu médico últimamente?
user_ernesto: Sí, hace dos semanas. Me recomendó mantener horarios fijos para dormir, reducir el café y evitar pantallas por la noche. Dijo que si no mejoro, podríamos cambiar la dosis o probar otro medicamento.

LLM: Entiendo. ¿Quieres añadir algo más?
user_ernesto: Solo que me gustaría dormir mejor sin depender de la medicación. Estoy intentando ser constante con las rutinas, aunque hay días que me cuesta. 
Cuando logro dormir bien y mantenerme activo, mi estado de ánimo mejora mucho.
""",

 "TEXT17": """LLM: ¿Que edad tienes?
user_ernesto: Tengo 45 años
""",
}
