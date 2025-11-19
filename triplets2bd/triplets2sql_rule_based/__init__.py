# triplets2bd/triplets2sql_rule_based/__init__.py
from typing import Tuple

# Tipo público
Triplet = Tuple[str, str, str]

# Re-exports de la API
from .helpers import (
    slugify,
    to_title_name,
    parse_age,
    normalize_date,
    sql_quote,
    partition_triplets_strict,
    compile_sql_script,
)

from utils.constants import (
    ALLOWED_REL,
    ALLOWED_PROP,
    PROPERTY_VERBS,
    RELATION_VERBS,
)

from .models import Entity, Collector
from .generator import upsert_from_triplets

__all__ = [
    # tipos
    "Triplet",
    # helpers
    "slugify", "to_title_name", "parse_age", "normalize_date", "sql_quote",
    # particionador/compilador
    "partition_triplets_strict", "compile_sql_script",
    # constantes
    "ALLOWED_REL", "ALLOWED_PROP", "PROPERTY_VERBS", "RELATION_VERBS",
    # modelos / API
    "Entity", "Collector", "upsert_from_triplets",
]
