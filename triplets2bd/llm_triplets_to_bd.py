from __future__ import annotations
from typing import List, Tuple
import json, requests, re
from utils.config import settings

# Utilidad simple para slug (debe replicarse en el LLM vía instrucciones)
_slug_re = re.compile(r"[^a-z0-9]+")

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = _slug_re.sub("_", s)
    return s.strip("_")

#Relaciones entre Nodos:   
    #" Actividad-[:EMPEORA {fecha, intensidad?}]->Sintoma\n"
    #" Actividad-[:MEJORA {fecha, intensidad?}]->Sintoma\n"
    #" Actividad-[:PROVOCA {fecha, intensidad?}]->Sintoma\n"
    #" Medicacion-[:MEJORA {fecha}]->Sintoma\n"
    #" Medicacion-[:EMPEORA {fecha}]->Sintoma\n"

#    "Relaciones las marcadas con {fecha} deben incluir prop {fecha} como fecha de alta):\n"
    # "  Persona-[:PADECE {fecha}]->Sintoma\n"
    #Persona-CONOCE {relacion}->Persona


SYSTEM_NEO4J = (
    "CONVERSIÓN DIRECTA DE TRIPLETAS A CYPHER - SIGUE ESTRICTAMENTE ESTAS REGLAS:\n"
    "\n"
    "ESQUEMA ÚNICO PERMITIDO:\n"
    "NODOS: Persona{user_id, nombre, edad} | Sintoma{sintoma_id, tipo, fecha_inicio, fecha_fin, categoria, frecuencia, gravedad} | Actividad{actividad_id, nombre, categoria, frecuencia} | Medicacion{medicacion_id, tipo, periodicidad}\n"
    "RELACIONES: (Persona)-[:TOMA]->(Medicacion) | (Persona)-[:PADECE]->(Sintoma) | (Persona)-[:REALIZA]->(Actividad)\n"
    "\n"

    "REGLAS DE CONVERSIÓN (OBLIGATORIAS):\n"
    "1. PROCESAR TODAS LAS TRIPLETAS: Analiza CADA tripleta (sujeto, verbo, objeto) secuencialmente\n"
    "2. EXTRACCIÓN DE PROPIEDADES:\n"
    "   - Si el verbo es 'tiene' y el objeto contiene 'años' → extraer número como edad\n"
    "   - Si el verbo es 'categoria' → asignar a propiedad 'categoria' del sujeto\n"
    "   - Si el verbo es 'frecuencia' → asignar a propiedad 'frecuencia' del sujeto\n"
    "   - Si el verbo es 'gravedad' → asignar a propiedad 'gravedad' del sujeto\n"
    "   - Si el verbo es 'inicio' → asignar a propiedad 'fecha_inicio' del sujeto\n"
    "3. GENERACIÓN DE IDs: \n"
    "   - Persona: 'Persona_' + slug(nombre) → user_id\n"
    "   - Sintoma: 'Sintoma_' + slug(tipo) → sintoma_id  \n"
    "   - Actividad: 'Actividad_' + slug(nombre) → actividad_id\n"
    "   - Medicacion: 'Medicacion_' + slug(tipo) → medicacion_id\n"
    "4. slug(texto): minúsculas, espacios→'_', sin acentos, sin signos\n"
    "\n"
    "REGLAS CRÍTICAS:\n"
    "  Usa siempre todas las tripletas recibidas, incluso si parecen redundantes o incompletas. Cada una debe reflejarse en el resultado Cypher siguiendo la estructura indicada."
    "  DEBES SIEMPRE establecer estas propiedades al crear nodos:\n"
    "   - Persona.nombre (obligatorio)\n"
    "   - Sintoma.tipo (obligatorio)\n"
    "   - Actividad.nombre (obligatorio)\n"
    "   - Medicacion.tipo (obligatorio)\n"
    "\n"
    "ORDEN DE OPERACIONES CON RELACIONES OBLIGATORIO:\n"
    "  1. PRIMERO crear todos los nodos con MERGE\n"
    "  2. DESPUÉS crear las relaciones con MATCH + MERGE\n"
    "  NUNCA intentar crear relaciones antes de asegurar que existen ambos nodos\n"
    "\n"
    "NORMALIZACIÓN DE FECHAS:\n"
    "  - Convertir '10/11/2022' → '2022-11-10' (formato ISO)\n"
    "  - Si no se puede determinar el formato, OMITIR la propiedad\n"
    "\n"
    "FORMATO CYPHER ESTRICTO:\n"
    "MERGE (n:Label {id_key: 'id_valor'})\n"
    "ON CREATE SET n.prop1 = valor1, n.prop2 = valor2;\n"
    "ON MATCH SET n.prop_opcional = valor2;\n"
    "\n"
    "MATCH (a:LabelA {id_key: 'id_a'}), (b:LabelB {id_key: 'id_b'})\n"
    "MERGE (a)-[:RELACION]->(b);\n"
    "\n"
    "PROHIBICIONES ABSOLUTAS:\n"
    " NO usar solo ON CREATE SET sin ON MATCH SET para propiedades actualizables\n"
    " NO omitir tripletas relevantes\n"
    " NO crear nodos sin propiedades obligatorias\n"
    " NO inferir propiedades/relaciones no explícitas\n"
    " NO usar MATCH sin filtro por ID\n" 
    " NO usar MERGE múltiple separado por comas\n"
    " NO explicaciones, solo Cypher\n"
    "\n"
    "EJEMPLOS DE CONVERSIÓN CORRECTA:\n"
    "Tripleta: (Juan, tiene, 25 años)\n"
    "Cypher: MERGE (p:Persona {user_id: 'persona_juan'}) ON CREATE SET p.nombre = 'Juan', p.edad = 25 ON MATCH SET p.edad = 25;\n"
    "\n"
    "Tripleta: (medicamento, se toma, cada 8 horas)\n"
    "Cypher: MERGE (m:Medicacion {medicacion_id: 'medicacion_medicamento'}) ON CREATE SET m.tipo = 'medicamento', m.periodicidad = 'cada 8 horas' ON MATCH SET m.periodicidad = 'cada 8 horas';\n"
    "\n"
    "Tripleta: (dolor, inicio, 10/11/2022)\n"
    "Cypher: MERGE (s:Sintoma {sintoma_id: 'sintoma_dolor'}) ON CREATE SET s.tipo = 'dolor', s.fecha_inicio = '2022-11-10' ON MATCH SET s.fecha_inicio = '2022-11-10';\n"
    "\n"
    "Tripleta: (Ana, realiza, natación)\n"
    "Cypher: MERGE (p:Persona {user_id: 'persona_ana'}) ON CREATE SET p.nombre = 'Ana';\n"
    "MERGE (a:Actividad {actividad_id: 'actividad_natacion'}) ON CREATE SET a.nombre = 'natación';\n"
    "MATCH (p:Persona {user_id: 'persona_ana'}), (a:Actividad {actividad_id: 'actividad_natacion'}) MERGE (p)-[:REALIZA]->(a);\n"
    "\n"
    "Tripleta: (dolor, frecuencia, diaria)\n"
    "Cypher: MERGE (s:Sintoma {sintoma_id: 'sintoma_dolor'}) ON CREATE SET s.tipo = 'dolor', s.frecuencia = 'diaria' ON MATCH SET s.frecuencia = 'diaria';\n"
    "SALIDA: ÚNICAMENTE código Cypher, sentencias separadas por ';', sin comentarios, sin markdown, sin texto explicativo."
)



SYSTEM_SQL = (
    "CONVERSIÓN DIRECTA DE TRIPLETAS A SQL - SIGUE ESTRICTAMENTE ESTAS REGLAS:\n"
    "\n"
    "ESQUEMA SQL ÚNICO PERMITIDO:\n"
    "TABLAS: persona(id, user_id, nombre, edad) | sintoma(id, sintoma_id, tipo, fecha_inicio, fecha_fin, categoria, frecuencia, gravedad) | actividad(id, actividad_id, nombre, categoria, frecuencia) | medicacion(id, medicacion_id, tipo, periodicidad)\n"
    "TABLAS RELACIONALES: persona_toma_medicacion(persona_id, medicacion_id) | persona_padece_sintoma(persona_id, sintoma_id) | persona_realiza_actividad(persona_id, actividad_id)\n"
    "\n"
    "REGLAS DE CONVERSIÓN (OBLIGATORIAS):\n"
    "1. PROCESAR TODAS LAS TRIPLETAS: Analiza CADA tripleta (sujeto, verbo, objeto) secuencialmente\n"
    "2. EXTRACCIÓN DE PROPIEDADES:\n"
    "   - Si el verbo es 'tiene' y el objeto contiene 'años' → extraer número como edad\n"
    "   - Si el verbo es 'categoria' → asignar a propiedad 'categoria' del sujeto\n"
    "   - Si el verbo es 'frecuencia' → asignar a propiedad 'frecuencia' del sujeto\n"
    "   - Si el verbo es 'gravedad' → asignar a propiedad 'gravedad' del sujeto\n"
    "   - Si el verbo es 'inicio' → asignar a propiedad 'fecha_inicio' del sujeto\n"
    "3. GENERACIÓN DE IDs: \n"
    "   - Persona: 'persona_' + slug(nombre) → user_id\n"
    "   - Sintoma: 'sintoma_' + slug(tipo) → sintoma_id  \n"
    "   - Actividad: 'actividad_' + slug(nombre) → actividad_id\n"
    "   - Medicacion: 'medicacion_' + slug(tipo) → medicacion_id\n"
    "4. slug(texto): minúsculas, espacios→'_', sin acentos, sin signos\n"
    "\n"
    "RELACIONES PERMITIDAS (SOLO ESTAS):\n"
    " - (Persona)-[toma]->(Medicacion) → persona_toma_medicacion\n"
    " - (Persona)-[padece]->(Sintoma) → persona_padece_sintoma\n"
    " - (Persona)-[realiza]->(Actividad) → persona_realiza_actividad\n"
    "\n"
    "REGLAS CRÍTICAS SQL:\n"
    "  Usa siempre todas las tripletas relevantes.\n"
    "  DEBES SIEMPRE establecer propiedades obligatorias al insertar.\n"
    "\n"
    "ORDEN DE OPERACIONES SQL OBLIGATORIO:\n"
    "  1. PRIMERO insertar/actualizar entidades principales\n"
    "  2. DESPUÉS insertar en tablas relacionales SOLO para relaciones permitidas\n"
    "  3. Usar INSERT con ON CONFLICT para entidades principales (PRESERVA DATOS EXISTENTES)\n"
    "  4. Usar INSERT OR IGNORE para relaciones\n"
    "\n"
    "MANEJO MEJORADO DE DUPLICADOS - ON CONFLICT (OBLIGATORIO):\n"
    "  Para entidades principales, usar siempre:\n"
    "  INSERT INTO tabla (id_columna, campo1, campo2, campo3) \n"
    "  VALUES ('id_valor', 'valor1', 'valor2', NULL)\n"
    "  ON CONFLICT(id_columna) DO UPDATE SET\n"
    "    campo1 = COALESCE(EXCLUDED.campo1, tabla.campo1),\n"
    "    campo2 = COALESCE(EXCLUDED.campo2, tabla.campo2),\n"
    "    campo3 = COALESCE(EXCLUDED.campo3, tabla.campo3);\n"
    "\n"
    "NORMALIZACIÓN DE FECHAS:\n"
    "  - Convertir '10/11/2022' → '2022-11-10' (formato ISO)\n"
    "  - Si no se puede determinar el formato, OMITIR la propiedad\n"
    "\n"
    "FORMATO SQL ESTRICTO:\n"
    "INSERT INTO tabla (id_columna, columna1, columna2, columna3) \n"
    "VALUES ('id_valor', 'valor1', 'valor2', NULL)\n"
    "ON CONFLICT(id_columna) DO UPDATE SET\n"
    "  columna1 = COALESCE(EXCLUDED.columna1, tabla.columna1),\n"
    "  columna2 = COALESCE(EXCLUDED.columna2, tabla.columna2),\n"
    "  columna3 = COALESCE(EXCLUDED.columna3, tabla.columna3);\n"
    "\n"
    "INSERT OR IGNORE INTO tabla_relacional (persona_id, otra_id)\n"
    "SELECT p.id, o.id \n"
    "FROM persona p, otra_tabla o \n"
    "WHERE p.user_id = 'id_persona' AND o.otra_id_col = 'id_otro';\n"
    "\n"
    "PROHIBICIONES ABSOLUTAS SQL:\n"
    " NO omitir tripletas relevantes\n"
    " NO crear registros sin propiedades obligatorias\n"
    " NO inferir propiedades/relaciones no explícitas\n"
    " NO usar INSERT OR REPLACE (causa pérdida de datos)\n"
    " NO explicaciones, solo SQL\n"
    "\n"
    "EJEMPLOS DE CONVERSIÓN CORRECTA:\n"
    "Tripleta: (Juan, tiene, 25 años)\n"
    "SQL: INSERT INTO persona (user_id, nombre, edad) VALUES ('persona_juan', 'Juan', 25)\n"
    "ON CONFLICT(user_id) DO UPDATE SET\n"
    "  nombre = EXCLUDED.nombre,\n"
    "  edad = COALESCE(EXCLUDED.edad, persona.edad);\n"
    "\n"
    "Tripleta: (medicamento, se toma, cada 8 horas)\n"
    "SQL: INSERT INTO medicacion (medicacion_id, tipo, periodicidad) VALUES ('medicacion_medicamento', 'medicamento', 'cada 8 horas')\n"
    "ON CONFLICT(medicacion_id) DO UPDATE SET\n"
    "  tipo = COALESCE(EXCLUDED.tipo, medicacion.tipo),\n"
    "  periodicidad = COALESCE(EXCLUDED.periodicidad, medicacion.periodicidad);\n"
    "\n"
    "Tripleta: (dolor, inicio, 10/11/2022)\n"
    "SQL: INSERT INTO sintoma (sintoma_id, tipo, fecha_inicio) VALUES ('sintoma_dolor', 'dolor', '2022-11-10')\n"
    "ON CONFLICT(sintoma_id) DO UPDATE SET\n"
    "  tipo = COALESCE(EXCLUDED.tipo, sintoma.tipo),\n"
    "  fecha_inicio = COALESCE(EXCLUDED.fecha_inicio, sintoma.fecha_inicio);\n"
    "\n"
    "Tripleta: (dolor, frecuencia, diaria)\n"
    "SQL: INSERT INTO sintoma (sintoma_id, tipo, frecuencia) VALUES ('sintoma_dolor', 'dolor', 'diaria')\n"
    "ON CONFLICT(sintoma_id) DO UPDATE SET\n"
    "  tipo = COALESCE(EXCLUDED.tipo, sintoma.tipo),\n"
    "  frecuencia = COALESCE(EXCLUDED.frecuencia, sintoma.frecuencia);\n"
    "\n"
    "Tripleta: (Juan, toma, medicamento)\n"
    "SQL: INSERT INTO persona (user_id, nombre) VALUES ('persona_juan', 'Juan')\n"
    "ON CONFLICT(user_id) DO UPDATE SET\n"
    "  nombre = EXCLUDED.nombre,\n"
    "  edad = COALESCE(EXCLUDED.edad, persona.edad);\n"
    "INSERT INTO medicacion (medicacion_id, tipo) VALUES ('medicacion_medicamento', 'medicamento')\n"
    "ON CONFLICT(medicacion_id) DO UPDATE SET\n"
    "  tipo = COALESCE(EXCLUDED.tipo, medicacion.tipo),\n"
    "  periodicidad = COALESCE(EXCLUDED.periodicidad, medicacion.periodicidad);\n"
    "INSERT OR IGNORE INTO persona_toma_medicacion (persona_id, medicacion_id) \n"
    "SELECT p.id, m.id FROM persona p, medicacion m \n"
    "WHERE p.user_id = 'persona_juan' AND m.medicacion_id = 'medicacion_medicamento';\n"
    "\n"
    "SALIDA: ÚNICAMENTE código SQL, sentencias separadas por ';', sin comentarios, sin markdown, sin texto explicativo."
)


def _post_chat(messages: list[dict], model: str | None = None) -> str:
    base = settings.OPENAI_API_BASE
    key = settings.OPENAI_API_KEY
    if not (base and key):
        raise RuntimeError("OPENAI_API_BASE/KEY no configurados en .env")
    url = f"{base}/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {"model": model or settings.MODEL_TRIPLETAS_CYPHER, "temperature": 0, "messages": messages}
    r = requests.post(url, headers=headers, data=json.dumps(data), timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def bd_from_triplets(raw: List[Tuple[str, str, str]], modo: str = "neo4j") -> str:

    normalized = [(a.strip().lower(), b.strip().lower(), c.strip().lower()) for a, b, c in raw]
    lines = [f"({a}, {b}, {c})" for a, b, c in normalized]
    prompt = "Tripletas:\n" + "\n".join(lines)

    if modo.lower() == "sql":
        system_prompt = SYSTEM_SQL
    else:
        system_prompt = SYSTEM_NEO4J

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt.strip()},
    ]

    script = _post_chat(messages)
    return script
