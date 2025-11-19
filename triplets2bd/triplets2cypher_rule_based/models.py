# triplets2bd/triplets2cypher_rule_based/models.py
from typing import Dict, Optional, Tuple
from .helpers import to_title_name, slugify

class Entity:
    def __init__(self, etype: str, key: str):
        # etype: persona | sintoma | actividad | medicacion
        # key:   user_id | sintoma_id | actividad_id | medicacion_id
        self.etype = etype
        self.key = key
        self.props: Dict[str, Optional[str]] = {}

    def set(self, k: str, v: Optional[str]):
        if v is None:
            return
        self.props[k] = v

    def ensure_minimal(self):
        if self.etype == "persona":
            self.props.setdefault("nombre", None)
        elif self.etype == "sintoma":
            self.props.setdefault("tipo", None)
        elif self.etype == "actividad":
            self.props.setdefault("nombre", None)
        elif self.etype == "medicacion":
            self.props.setdefault("tipo", None)

class Collector:
    def __init__(self):
        self.entities: Dict[Tuple[str, str], Entity] = {}
        self.relations = []  # (rel_type, left_person_uid, right_key or right_person_uid)
        self.persona_index: Dict[str, str] = {}
        self.sintoma_index: Dict[str, str] = {}
        self.actividad_index: Dict[str, str] = {}
        self.medicacion_index: Dict[str, str] = {}

    def _get_or_new(self, etype: str, keyvalue: str) -> Entity:
        keycol = {
            "persona": "user_id",
            "sintoma": "sintoma_id",
            "actividad": "actividad_id",
            "medicacion": "medicacion_id",
        }[etype]
        k = (etype, keyvalue)
        if k not in self.entities:
            e = Entity(etype, keycol)
            e.set(keycol, keyvalue)
            self.entities[k] = e
        return self.entities[k]

    def persona_by_name(self, name: str) -> Entity:
        canonical = name.strip().lower()
        uid = self.persona_index.get(canonical) or f"persona_{slugify(canonical)}"
        self.persona_index[canonical] = uid
        e = self._get_or_new("persona", uid)
        e.set("nombre", to_title_name(name))
        return e

    def sintoma_by_type(self, tipo: str) -> Entity:
        canonical = tipo.strip().lower()
        sid = self.sintoma_index.get(canonical) or f"sintoma_{slugify(canonical)}"
        self.sintoma_index[canonical] = sid
        e = self._get_or_new("sintoma", sid)
        e.set("tipo", canonical)
        return e

    def actividad_by_name(self, nombre: str) -> Entity:
        canonical = nombre.strip().lower()
        aid = self.actividad_index.get(canonical) or f"actividad_{slugify(canonical)}"
        self.actividad_index[canonical] = aid
        e = self._get_or_new("actividad", aid)
        e.set("nombre", canonical)
        return e

    def medicacion_by_type(self, tipo: str) -> Entity:
        canonical = tipo.strip().lower()
        mid = self.medicacion_index.get(canonical) or f"medicacion_{slugify(canonical)}"
        self.medicacion_index[canonical] = mid
        e = self._get_or_new("medicacion", mid)
        e.set("tipo", canonical)
        return e
