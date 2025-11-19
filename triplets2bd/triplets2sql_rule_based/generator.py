from typing import List, Tuple, Optional
from .models import Collector, Entity
from .helpers import parse_age, normalize_date, sql_quote
from utils.constants import PROPERTY_VERBS, RELATION_VERBS

Triplet = Tuple[str, str, str]


def upsert_from_triplets(triplets: List[Triplet]) -> Tuple[List[str], List[str]]:
    """
    Construye sentencias SQL para entidades (UPSERT) y relaciones (INSERT OR IGNORE)
    a partir de tripletas crudas, sin LLM. Asume tripletas correctas y ordenadas.
    """
    col = Collector()
    property_buffer: List[Tuple[str, str, str]] = []
    leftovers_for_props: List[Tuple[Triplet, str]] = []

    # PASADA 1: crear entidades por relaciones y edad; y relaciones base
    for s, v, o in triplets:
        s_l, v_l, o_l = s.strip().lower(), v.strip().lower(), o.strip().lower()

        # Edad
        if v_l == 'edad':
            print(1)
            age = parse_age(o_l)
            print(age)
            if age is not None:
                p = col.persona_by_name(s_l)
                p.set('edad', age)
            continue

        # Relaciones canónicas
        if v_l in RELATION_VERBS:
            p = col.persona_by_name(s_l)
            if v_l == 'padece':
                snt = col.sintoma_by_type(o_l)
                col.relations.append(('persona_padece_sintoma', p.props['user_id'], snt.props['sintoma_id']))
            elif v_l == 'toma':
                med = col.medicacion_by_type(o_l)
                col.relations.append(('persona_toma_medicacion', p.props['user_id'], med.props['medicacion_id']))
            elif v_l == 'realiza':
                act = col.actividad_by_name(o_l)
                col.relations.append(('persona_realiza_actividad', p.props['user_id'], act.props['actividad_id']))
            continue

        # Propiedades permitidas: diferir a PASADA 2
        if v_l in PROPERTY_VERBS:
            property_buffer.append((s_l, v_l, o_l))
            continue

    # PASADA 2: aplicar props SOLO si la entidad ya existe en índices
    for s_l, v_l, o_l in property_buffer:
        prop, kind = PROPERTY_VERBS[v_l]
        value: Optional[str] = normalize_date(o_l) if kind == 'date' else o_l

        ent: Optional[Entity] = None
        if s_l in col.sintoma_index:
            ent = col._get_or_new('sintoma', col.sintoma_index[s_l])
        elif s_l in col.actividad_index:
            ent = col._get_or_new('actividad', col.actividad_index[s_l])
        elif s_l in col.medicacion_index:
            ent = col._get_or_new('medicacion', col.medicacion_index[s_l])

        if ent is None:
            leftovers_for_props.append(((s_l, v_l, o_l), "prop_sin_entidad_previa"))
            continue

        ent.set(prop, value)

    for ent in col.entities.values():
        ent.ensure_minimal()

    # Build SQL
    entity_sql: List[str] = []
    unique_map = {
        'persona':   ('persona',   'user_id',     ('nombre', 'edad')),
        'sintoma':   ('sintoma',   'sintoma_id',  ('tipo', 'fecha_inicio', 'fecha_fin', 'categoria', 'frecuencia', 'gravedad')),
        'actividad': ('actividad', 'actividad_id',('nombre', 'categoria', 'frecuencia')),
        'medicacion':('medicacion','medicacion_id',('tipo', 'periodicidad')),
    }

    for (etype, key), ent in sorted(col.entities.items(), key=lambda x: (x[0][0], x[0][1])):
        table, keycol, other_cols = unique_map[etype]
        cols = [keycol] + list(other_cols)
        vals = [sql_quote(ent.props.get(c)) for c in cols]
        insert = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)})"
        updates = ",\n  ".join(f"{c} = excluded.{c}" for c in other_cols)
        entity_sql.append(insert + f"\nON CONFLICT({keycol}) DO UPDATE SET\n  {updates};")

    relation_sql: List[str] = []
    for rel_table, left_key, right_key in sorted(col.relations):
        if rel_table == 'persona_toma_medicacion':
            relation_sql.append(
                "INSERT OR IGNORE INTO persona_toma_medicacion (persona_id, medicacion_id, pauta)\n"
                "SELECT p.id, m.id, m.periodicidad FROM persona p, medicacion m\n"
                f"WHERE p.user_id = '{left_key}' AND m.medicacion_id = '{right_key}';"
            )
        elif rel_table == 'persona_realiza_actividad':
            relation_sql.append(
                "INSERT OR IGNORE INTO persona_realiza_actividad (persona_id, actividad_id)\n"
                "SELECT p.id, a.id FROM persona p, actividad a\n"
                f"WHERE p.user_id = '{left_key}' AND a.actividad_id = '{right_key}';"
            )
        elif rel_table == 'persona_padece_sintoma':
            relation_sql.append(
                "INSERT OR IGNORE INTO persona_padece_sintoma (persona_id, sintoma_id, desde)\n"
                "SELECT p.id, s.id, s.fecha_inicio FROM persona p, sintoma s\n"
                f"WHERE p.user_id = '{left_key}' AND s.sintoma_id = '{right_key}';"
            )

    return entity_sql, relation_sql