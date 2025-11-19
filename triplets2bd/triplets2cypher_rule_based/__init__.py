# triplets2bd/triplets2cypher_rule_based/__init__.py
from typing import Tuple

Triplet = Tuple[str, str, str]

from .helpers import (
    slugify,
    to_title_name,
    parse_age,
    normalize_date,
    cypher_quote,
    partition_triplets_strict,   # propio de cypher (incluye 'conoce')
    compile_cypher_script,
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
    "Triplet",
    "slugify", "to_title_name", "parse_age", "normalize_date", "cypher_quote",
    "partition_triplets_strict", "compile_cypher_script",
    "ALLOWED_REL", "ALLOWED_PROP", "PROPERTY_VERBS", "RELATION_VERBS",
    "Entity", "Collector", "upsert_from_triplets",
]
