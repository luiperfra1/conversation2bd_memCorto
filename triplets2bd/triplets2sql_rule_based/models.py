from typing import Dict, Optional, Tuple
from .helpers import to_title_name
from .helpers import slugify

class Entity:
    def __init__(self, etype: str, key: str):
        self.etype = etype  # persona | sintoma | actividad | medicacion
        self.key = key      # user_id | sintoma_id | actividad_id | medicacion_id
        self.props: Dict[str, Optional[str]] = {}

    def set(self, k: str, v: Optional[str]):
        if v is None:
            return
        self.props[k] = v

    def ensure_minimal(self):
        if self.etype == 'persona':
            self.props.setdefault('nombre', None)
        elif self.etype == 'sintoma':
            self.props.setdefault('tipo', None)
        elif self.etype == 'actividad':
            self.props.setdefault('nombre', None)
        elif self.etype == 'medicacion':
            self.props.setdefault('tipo', None)


class Collector:
    def __init__(self):
        self.entities: Dict[Tuple[str, str], Entity] = {}
        self.relations = []  # List[Tuple[str, str, str]] = (rel_table, persona_user_id, right_key)
        self.persona_index: Dict[str, str] = {}
        self.sintoma_index: Dict[str, str] = {}
        self.actividad_index: Dict[str, str] = {}
        self.medicacion_index: Dict[str, str] = {}

    def _get_or_new(self, etype: str, keyvalue: str) -> Entity:
        keycol = {
            'persona': 'user_id',
            'sintoma': 'sintoma_id',
            'actividad': 'actividad_id',
            'medicacion': 'medicacion_id',
        }[etype]
        k = (etype, keyvalue)
        if k not in self.entities:
            e = Entity(etype, keycol)
            e.set(keycol, keyvalue)
            self.entities[k] = e
        return self.entities[k]

    def persona_by_name(self, name: str) -> Entity:
        canonical = name.strip().lower()
        if canonical in self.persona_index:
            uid = self.persona_index[canonical]
        else:
            uid = f"persona_{slugify(canonical)}"
            self.persona_index[canonical] = uid
        e = self._get_or_new('persona', uid)
        e.set('nombre', to_title_name(name))
        return e

    def sintoma_by_type(self, tipo: str) -> Entity:
        canonical = tipo.strip().lower()
        if canonical in self.sintoma_index:
            sid = self.sintoma_index[canonical]
        else:
            sid = f"sintoma_{slugify(canonical)}"
            self.sintoma_index[canonical] = sid
        e = self._get_or_new('sintoma', sid)
        e.set('tipo', canonical)
        return e

    def actividad_by_name(self, nombre: str) -> Entity:
        canonical = nombre.strip().lower()
        if canonical in self.actividad_index:
            aid = self.actividad_index[canonical]
        else:
            aid = f"actividad_{slugify(canonical)}"
            self.actividad_index[canonical] = aid
        e = self._get_or_new('actividad', aid)
        e.set('nombre', canonical)
        return e

    def medicacion_by_type(self, tipo: str) -> Entity:
        canonical = tipo.strip().lower()
        if canonical in self.medicacion_index:
            mid = self.medicacion_index[canonical]
        else:
            mid = f"medicacion_{slugify(canonical)}"
            self.medicacion_index[canonical] = mid
        e = self._get_or_new('medicacion', mid)
        e.set('tipo', canonical)
        return e
