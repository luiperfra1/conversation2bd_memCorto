from __future__ import annotations
from .neo4j_client import Neo4jClient


# --- Existencia de fecha en TODAS las relaciones que usas ---
    #"CREATE CONSTRAINT rel_fecha_toma IF NOT EXISTS FOR ()-[r:TOMA]-() REQUIRE r.fecha IS NOT NULL",
    #"CREATE CONSTRAINT rel_fecha_padece IF NOT EXISTS FOR ()-[r:PADECE]-() REQUIRE r.fecha IS NOT NULL",
    #"CREATE CONSTRAINT rel_fecha_realiza IF NOT EXISTS FOR ()-[r:REALIZA]-() REQUIRE r.fecha IS NOT NULL",
    #"CREATE CONSTRAINT rel_fecha_conoce IF NOT EXISTS FOR ()-[r:CONOCE]-() REQUIRE r.fecha IS NOT NULL",

# Claves naturales por id
CONSTRAINTS = [
    #UNICIDAD
    "CREATE CONSTRAINT persona_id IF NOT EXISTS FOR (n:Persona) REQUIRE n.user_id IS UNIQUE",
    "CREATE CONSTRAINT sintoma_id IF NOT EXISTS FOR (n:Sintoma) REQUIRE n.sintoma_id IS UNIQUE",
    "CREATE CONSTRAINT actividad_id IF NOT EXISTS FOR (n:Actividad) REQUIRE n.actividad_id IS UNIQUE",
    "CREATE CONSTRAINT medicacion_id IF NOT EXISTS FOR (n:Medicacion) REQUIRE n.medicacion_id IS UNIQUE",

    #PROPIEDAD NOT NULL
    "CREATE CONSTRAINT persona_nombre_req IF NOT EXISTS FOR (n:Persona) REQUIRE n.nombre IS NOT NULL",
    "CREATE CONSTRAINT sintoma_tipo_req IF NOT EXISTS FOR (n:Sintoma) REQUIRE n.tipo IS NOT NULL",
    "CREATE CONSTRAINT actividad_nombre_req IF NOT EXISTS FOR (n:Actividad) REQUIRE n.nombre IS NOT NULL",
    "CREATE CONSTRAINT medicacion_tipo_req IF NOT EXISTS FOR (n:Medicacion) REQUIRE n.tipo IS NOT NULL",
]



INDEXES = [
    # Persona
    "CREATE INDEX persona_nombre IF NOT EXISTS FOR (n:Persona) ON (n.nombre)",

    # Sintoma
    "CREATE INDEX sintoma_tipo IF NOT EXISTS FOR (n:Sintoma) ON (n.tipo)",

    # Actividad
    "CREATE INDEX actividad_nombre IF NOT EXISTS FOR (n:Actividad) ON (n.nombre)",

    # Medicacion
    "CREATE INDEX medicacion_tipo IF NOT EXISTS FOR (n:Medicacion) ON (n.tipo)",
]


def bootstrap(db: Neo4jClient):
    for cy in CONSTRAINTS + INDEXES:
        db.write(cy, {})