# schema_sqlite_bootstrap.py
from __future__ import annotations
from textwrap import dedent
from sqlite3 import Connection

DDL = dedent("""
PRAGMA foreign_keys = ON;

-- ==============
-- Entidades
-- ==============

CREATE TABLE IF NOT EXISTS persona (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    TEXT UNIQUE NOT NULL,
  nombre     TEXT NOT NULL,
  edad       INTEGER CHECK (edad >= 0),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sintoma (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  sintoma_id   TEXT UNIQUE,
  tipo         TEXT NOT NULL,
  fecha_inicio TEXT,
  fecha_fin    TEXT,
  categoria    TEXT CHECK (categoria IN (
                  'motor','cognitivo','afectivo','sueno',
                  'autonomico','habla_voz','deglucion',
                  'dolor_fatiga','otros_no_motor'
                )),
  frecuencia   TEXT,
  gravedad     TEXT CHECK (gravedad IN ('leve','moderada','grave')),
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS actividad (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  actividad_id TEXT UNIQUE,
  nombre       TEXT NOT NULL,
  categoria    TEXT,
  frecuencia   TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medicacion (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  medicacion_id TEXT UNIQUE,
  tipo          TEXT NOT NULL,
  periodicidad  TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ==============
-- Relaciones N:M
-- ==============

CREATE TABLE IF NOT EXISTS persona_toma_medicacion (
  persona_id    INTEGER NOT NULL,
  medicacion_id INTEGER NOT NULL,
  pauta         TEXT,
  desde         TEXT,
  hasta         TEXT,
  PRIMARY KEY (persona_id, medicacion_id),
  FOREIGN KEY (persona_id)    REFERENCES persona(id)    ON DELETE CASCADE,
  FOREIGN KEY (medicacion_id) REFERENCES medicacion(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS persona_padece_sintoma (
  persona_id INTEGER NOT NULL,
  sintoma_id INTEGER NOT NULL,
  desde      TEXT,
  hasta      TEXT,
  PRIMARY KEY (persona_id, sintoma_id),
  FOREIGN KEY (persona_id) REFERENCES persona(id) ON DELETE CASCADE,
  FOREIGN KEY (sintoma_id) REFERENCES sintoma(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS persona_realiza_actividad (
  persona_id  INTEGER NOT NULL,
  actividad_id INTEGER NOT NULL,
  desde        TEXT,
  hasta        TEXT,
  PRIMARY KEY (persona_id, actividad_id),
  FOREIGN KEY (persona_id)   REFERENCES persona(id)   ON DELETE CASCADE,
  FOREIGN KEY (actividad_id) REFERENCES actividad(id) ON DELETE CASCADE
);
-- ==============
-- Índices
-- ==============

CREATE INDEX IF NOT EXISTS idx_persona_user_id ON persona(user_id);
CREATE INDEX IF NOT EXISTS idx_sintoma_tipo ON sintoma(tipo);
CREATE INDEX IF NOT EXISTS idx_actividad_nombre ON actividad(nombre);
CREATE INDEX IF NOT EXISTS idx_medicacion_tipo ON medicacion(tipo);

CREATE INDEX IF NOT EXISTS idx_toma_persona ON persona_toma_medicacion(persona_id);
CREATE INDEX IF NOT EXISTS idx_toma_medicacion ON persona_toma_medicacion(medicacion_id);

CREATE INDEX IF NOT EXISTS idx_padece_persona ON persona_padece_sintoma(persona_id);
CREATE INDEX IF NOT EXISTS idx_padece_sintoma ON persona_padece_sintoma(sintoma_id);

CREATE INDEX IF NOT EXISTS idx_realiza_persona ON persona_realiza_actividad(persona_id);
CREATE INDEX IF NOT EXISTS idx_realiza_actividad ON persona_realiza_actividad(actividad_id);


-- ==============
-- Vistas (opcionales, solo lectura)
-- ==============

CREATE VIEW IF NOT EXISTS vw_persona_meds AS
SELECT p.user_id, p.nombre AS persona, m.tipo AS medicacion, ptm.pauta, ptm.desde, ptm.hasta
FROM persona p
JOIN persona_toma_medicacion ptm ON ptm.persona_id = p.id
JOIN medicacion m ON m.id = ptm.medicacion_id;

CREATE VIEW IF NOT EXISTS vw_persona_sintomas AS
SELECT p.user_id, p.nombre AS persona, s.tipo AS sintoma, s.categoria, s.frecuencia, s.gravedad
FROM persona p
JOIN persona_padece_sintoma pps ON pps.persona_id = p.id
JOIN sintoma s ON s.id = pps.sintoma_id;

DROP VIEW IF EXISTS vw_persona_actividades;
CREATE VIEW vw_persona_actividades AS
SELECT p.user_id, p.nombre AS persona, a.nombre AS actividad, a.categoria, a.frecuencia
FROM persona p
JOIN persona_realiza_actividad pra ON pra.persona_id = p.id
JOIN actividad a ON a.id = pra.actividad_id;

-- ==============
-- Triggers de updated_at
-- ==============

CREATE TRIGGER IF NOT EXISTS trg_persona_updated
AFTER UPDATE ON persona
BEGIN
  UPDATE persona SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_sintoma_updated
AFTER UPDATE ON sintoma
BEGIN
  UPDATE sintoma SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_actividad_updated
AFTER UPDATE ON actividad
BEGIN
  UPDATE actividad SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_medicacion_updated
AFTER UPDATE ON medicacion
BEGIN
  UPDATE medicacion SET updated_at = datetime('now') WHERE id = NEW.id;
END;
""")

def reset_sql(conn: Connection) -> None:
    """Elimina vistas y tablas en orden seguro, sin mezclar DROP VIEW/TABLE."""
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")

    # 1) Vistas primero (pueden depender de tablas)
    vistas = (
        "vw_persona_meds",
        "vw_persona_sintomas",
        "vw_persona_actividades",
    )
    for v in vistas:
        cur.execute(f"DROP VIEW IF EXISTS {v};")

    # 2) Tablas de relación -> tablas base -> tablas auxiliares (incluye 'log')
    tablas = (
        "persona_realiza_actividad",
        "persona_padece_sintoma",
        "persona_toma_medicacion",
        "medicacion",
        "actividad",
        "sintoma",
        "persona",
    )
    for t in tablas:
        cur.execute(f"DROP TABLE IF EXISTS {t};")

    cur.execute("PRAGMA foreign_keys = ON;")
    conn.commit()



def bootstrap_sqlite(conn: Connection) -> None:
    conn.executescript(DDL)
    conn.commit()
