# triplets2bd/triplets2cypher_rule_based/helpers.py
from __future__ import annotations
import re
import unicodedata
from datetime import datetime
from typing import Optional, List, Tuple

from utils.constants import _DATE_FORMATS, ALLOWED_REL, ALLOWED_PROP

def slugify(text: str) -> str:
    s = text.strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r"[^a-z0-9\s_-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    return s

def to_title_name(s: Optional[str]) -> Optional[str]:
    if not isinstance(s, str):
        return s
    parts = [p for p in s.strip().split() if p]
    return " ".join(p.capitalize() for p in parts)

def parse_age(obj: str) -> Optional[int]:
    o = obj.strip().lower()
    m = re.search(r"(\d{1,3})\s*años?", o)
    if m:
        return int(m.group(1))
    if o.isdigit():
        return int(o)
    return None

def normalize_date(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def cypher_quote(v: Optional[object]) -> str:
    if v is None:
        return "NULL"  # NO se escribe en Cypher si es NULL; el generador lo omitirá
    if isinstance(v, int):
        return str(v)
    s = str(v).replace("'", "\\'")
    return f"'{s}'"

Triplet = Tuple[str, str, str]

def _is_age_text(obj: str) -> bool:
    obj_l = obj.strip().lower()
    return bool(re.search(r"^\d{1,3}\s*años?$", obj_l)) or obj_l.isdigit()

def partition_triplets_strict(triplets: List[Triplet]) -> Tuple[List[Triplet], List[Tuple[Triplet, str]]]:
    """
    Igual filosofía que la versión SQL, pero permitimos además 'conoce' como relación.
    """
    supported: List[Triplet] = []
    leftovers: List[Tuple[Triplet, str]] = []

    for s, v, o in triplets:
        s_l, v_l, o_l = s.strip(), v.strip().lower(), o.strip()
        if v_l in ALLOWED_REL or v_l in ALLOWED_PROP:
            supported.append((s_l, v_l, o_l))
            continue
        if v_l == "edad":
            if _is_age_text(o_l):
                supported.append((s_l, v_l, o_l))
            else:
                leftovers.append(((s_l, v_l, o_l), "tiene_sin_edad"))
            continue
        leftovers.append(((s_l, v_l, o_l), "verbo_no_permitido"))

    return supported, leftovers

def compile_cypher_script(triplets: List[Triplet]) -> str:
    # import perezoso para evitar ciclo
    from .generator import upsert_from_triplets
    entity_cypher, relation_cypher = upsert_from_triplets(triplets)
    return "\n".join(entity_cypher + relation_cypher)
