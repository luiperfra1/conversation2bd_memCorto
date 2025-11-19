# triplets2bd/triplets2cypher_rule_based/constants.py

ALLOWED_REL = {"padece", "toma", "realiza"}
ALLOWED_PROP = {"categoria", "frecuencia", "gravedad", "inicio", "fecha_inicio", "fin", "se toma", "periodicidad", "edad"}

PROPERTY_VERBS = {
    "categoria": ("categoria", "node"),
    "frecuencia": ("frecuencia", "node"),
    "gravedad": ("gravedad", "node"),
    "inicio": ("fecha_inicio", "date"),
    "fin": ("fecha_fin", "date"),
    "se toma": ("periodicidad", "node"),
    "periodicidad": ("periodicidad", "node"),
}

RELATION_VERBS = {
    "toma": "TOMA",
    "padece": "PADECE",
    "realiza": "REALIZA"
}

_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y")
