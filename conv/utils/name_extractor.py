# conv/name_extractor.py
def extract_name(user_text: str) -> str:
    """
    Extrae un nombre del texto del usuario.
    Métodos simples pero efectivos:

    - "me llamo X"
    - "soy X"
    - "mi nombre es X"
    - o si es una sola palabra, se toma tal cual

    Devuelve un nombre en minúsculas sin espacios.
    """
    text = user_text.strip().lower()

    triggers = ["me llamo ", "soy ", "mi nombre es "]
    for t in triggers:
        if t in text:
            name = text.split(t)[1].strip().split()[0]
            return name

    # Si es una sola palabra, se usa tal cual
    if len(text.split()) == 1:
        return text

    # Si no lo detecta, pone "usuario"
    return "usuario"
