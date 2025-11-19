# triplets2bd/triplets2cypher_rule_based/generator.py
from typing import List, Tuple, Optional
from .models import Collector, Entity
from .helpers import parse_age, normalize_date, cypher_quote
from utils.constants import PROPERTY_VERBS, RELATION_VERBS

Triplet = Tuple[str, str, str]

def _set_if_not_none(pairs):
    # Devuelve lista "prop = valor" sin los None
    out = []
    for k, v in pairs:
        if v is None:
            continue
        if isinstance(v, int):
            out.append(f"{k} = {v}")
        else:
            out.append(f"{k} = {cypher_quote(v)}")
    return out

def upsert_from_triplets(triplets: List[Triplet]) -> Tuple[List[str], List[str]]:
    """
    Construye sentencias **Cypher** deterministas para nodos y relaciones, sin LLM.
    Sigue el estilo del prompt:
      - MERGE por ID
      - ON CREATE SET props obligatorias
      - ON MATCH SET props actualizables / repetidas
      - Crear primero nodos, después relaciones (con MATCH por ID + MERGE de la relación)
    """
    col = Collector()
    property_buffer: List[Tuple[str, str, str]] = []

    # PASADA 1: crear entidades a partir de relaciones y edad; y registrar relaciones base
    for s, v, o in triplets:
        s_l, v_l, o_l = s.strip().lower(), v.strip().lower(), o.strip().lower()

        # Edad
        if v_l == "edad":
            age = parse_age(o_l)
            if age is not None:
                p = col.persona_by_name(s_l)
                p.set("edad", age)
            continue

        # Relaciones canónicas
        if v_l in RELATION_VERBS:
            if v_l == "padece":
                p = col.persona_by_name(s_l)
                snt = col.sintoma_by_type(o_l)
                col.relations.append(("PADECE", p.props["user_id"], snt.props["sintoma_id"]))
            elif v_l == "toma":
                p = col.persona_by_name(s_l)
                med = col.medicacion_by_type(o_l)
                col.relations.append(("TOMA", p.props["user_id"], med.props["medicacion_id"]))
            elif v_l == "realiza":
                p = col.persona_by_name(s_l)
                act = col.actividad_by_name(o_l)
                col.relations.append(("REALIZA", p.props["user_id"], act.props["actividad_id"]))
            continue

        # Propiedades: diferir a PASADA 2 (para fechas y otras props)
        property_buffer.append((s, v, o))

    # PASADA 2: aplicar props (si la entidad no existe, crearla ahora para no perder info)
    for s, v, o in property_buffer:
        s_l, v_l, o_l = s.strip().lower(), v.strip().lower(), o.strip()
        prop, kind = PROPERTY_VERBS.get(v_l, (None, None))
        if not prop:
            continue
        value: Optional[str] = normalize_date(o_l) if kind == "date" else o_l.strip().lower()

        ent: Optional[Entity] = None
        if s_l in col.sintoma_index:
            ent = col._get_or_new("sintoma", col.sintoma_index[s_l])
        elif s_l in col.actividad_index:
            ent = col._get_or_new("actividad", col.actividad_index[s_l])
        elif s_l in col.medicacion_index:
            ent = col._get_or_new("medicacion", col.medicacion_index[s_l])
        elif s_l in col.persona_index:
            ent = col._get_or_new("persona", col.persona_index[s_l])
        else:
            # Si llega una propiedad aislada, inferimos el tipo por el verbo:
            # (preferencia: sintoma/actividad/medicacion; persona solo si nada encaja)
            # Aquí es difícil saber el tipo sin contexto; no inferimos etiqueta salvo persona.
            # Si la prop es 'periodicidad' asumimos medicación; si 'categoria'/'frecuencia' puede ser síntoma o actividad.
            if v_l in ("se toma", "periodicidad"):
                ent = col.medicacion_by_type(s_l)
            else:
                # fallback: si el sujeto está en minúsculas y parece nombre propio NO fiable;
                # dejamos como síntoma por defecto si encaja con props típicas, si no, actividad.
                if v_l in ("categoria", "frecuencia", "gravedad", "inicio", "fin"):
                    ent = col.sintoma_by_type(s_l)
                else:
                    ent = col.actividad_by_name(s_l)

        ent.set(prop, value)

    for ent in col.entities.values():
        ent.ensure_minimal()

    # --- Build CYPHER (NODOS) ---
    entity_cypher: List[str] = []
    # Orden estable por tipo e id para que sea determinista
    for (etype, key), ent in sorted(col.entities.items(), key=lambda x: (x[0][0], x[0][1])):
        if etype == "persona":
            # obligatorias: nombre (Title Case), edad opcional
            on_create = _set_if_not_none([
                ("n.nombre", ent.props.get("nombre")),
                ("n.edad", ent.props.get("edad")),
            ])
            on_match  = _set_if_not_none([
                ("n.edad", ent.props.get("edad")),
            ])
            stmt = (
                f"MERGE (n:Persona {{user_id: {cypher_quote(ent.props['user_id'])}}}) "
                f"ON CREATE SET {', '.join(on_create) if on_create else 'n._created = true'} "
                f"ON MATCH SET {', '.join(on_match) if on_match else 'n._seen = true'};"
            )
            entity_cypher.append(stmt)

        elif etype == "sintoma":
            on_create = _set_if_not_none([
                ("n.tipo", ent.props.get("tipo")),
                ("n.fecha_inicio", ent.props.get("fecha_inicio")),
                ("n.fecha_fin", ent.props.get("fecha_fin")),
                ("n.categoria", ent.props.get("categoria")),
                ("n.frecuencia", ent.props.get("frecuencia")),
                ("n.gravedad", ent.props.get("gravedad")),
            ])
            on_match = _set_if_not_none([
                ("n.fecha_inicio", ent.props.get("fecha_inicio")),
                ("n.fecha_fin", ent.props.get("fecha_fin")),
                ("n.categoria", ent.props.get("categoria")),
                ("n.frecuencia", ent.props.get("frecuencia")),
                ("n.gravedad", ent.props.get("gravedad")),
            ])
            stmt = (
                f"MERGE (n:Sintoma {{sintoma_id: {cypher_quote(ent.props['sintoma_id'])}}}) "
                f"ON CREATE SET {', '.join(on_create) if on_create else 'n._created = true'} "
                f"ON MATCH SET {', '.join(on_match) if on_match else 'n._seen = true'};"
            )
            entity_cypher.append(stmt)

        elif etype == "actividad":
            on_create = _set_if_not_none([
                ("n.nombre", ent.props.get("nombre")),
                ("n.categoria", ent.props.get("categoria")),
                ("n.frecuencia", ent.props.get("frecuencia")),
            ])
            on_match = _set_if_not_none([
                ("n.categoria", ent.props.get("categoria")),
                ("n.frecuencia", ent.props.get("frecuencia")),
            ])
            stmt = (
                f"MERGE (n:Actividad {{actividad_id: {cypher_quote(ent.props['actividad_id'])}}}) "
                f"ON CREATE SET {', '.join(on_create) if on_create else 'n._created = true'} "
                f"ON MATCH SET {', '.join(on_match) if on_match else 'n._seen = true'};"
            )
            entity_cypher.append(stmt)

        elif etype == "medicacion":
            on_create = _set_if_not_none([
                ("n.tipo", ent.props.get("tipo")),
                ("n.periodicidad", ent.props.get("periodicidad")),
            ])
            on_match = _set_if_not_none([
                ("n.periodicidad", ent.props.get("periodicidad")),
            ])
            stmt = (
                f"MERGE (n:Medicacion {{medicacion_id: {cypher_quote(ent.props['medicacion_id'])}}}) "
                f"ON CREATE SET {', '.join(on_create) if on_create else 'n._created = true'} "
                f"ON MATCH SET {', '.join(on_match) if on_match else 'n._seen = true'};"
            )
            entity_cypher.append(stmt)

    # --- Build CYPHER (RELACIONES) ---
    relation_cypher: List[str] = []
    for rel_type, left_key, right_key in sorted(col.relations):
        if rel_type in {"TOMA", "PADECE", "REALIZA"}:
            # left: Persona; right: Medicacion/Sintoma/Actividad
            label_right = {
                "TOMA": "Medicacion",
                "PADECE": "Sintoma",
                "REALIZA": "Actividad",
            }[rel_type]
            id_right = {
                "TOMA": ("medicacion_id", right_key),
                "PADECE": ("sintoma_id", right_key),
                "REALIZA": ("actividad_id", right_key),
            }[rel_type]
            rk, rv = id_right
            stmt = (
                f"MATCH (p:Persona {{user_id: {cypher_quote(left_key)}}}), "
                f"(x:{label_right} {{{rk}: {cypher_quote(rv)}}}) "
                f"MERGE (p)-[:{rel_type}]->(x);"
            )
            relation_cypher.append(stmt)

    return entity_cypher, relation_cypher
