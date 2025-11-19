# 🧠 Proyecto: Conversación → Tripletas → Cypher / SQL

Este proyecto implementa un **pipeline conversacional completo** capaz de transformar una conversación natural con un LLM en **información estructurada**, almacenada en **SQLite** o **Neo4j**.

El objetivo es extraer de forma fiable **información clínica o de hábitos personales** procedente de conversaciones reales, garantizando:

* Coherencia interna
* Seguridad semántica  
* Dominio cerrado
* Validación estricta
* Persistencia en BD sin ruido

---

## 🧠 Funcionamiento global del sistema

El sistema opera como un **ETL conversacional**, compuesto por **4 capas** que se ejecutan siempre en el mismo orden:

```bash
CONVERSACIÓN → RESUMEN → TRIPLETAS → BASE DE DATOS
```

---

### 1) Conversación con LLM → Paquetitos (`conv/`)

El usuario habla con un LLM.

Cada turno genera un **paquetito** del estilo:

```bash
LLM: <mensaje del asistente>
user_<nombre>: <mensaje del usuario>
```

El módulo:

* Detecta el nombre del usuario automáticamente
* Mantiene el estado conversacional
* Genera paquetitos que alimentan el pipeline principal

**Ejecutar:**

```bash
python -m conv.main_conv
```

---

### 2) Paquetitos → Resumen semántico (`conv2text/`)

Convierte esos paquetitos en frases breves totalmente explícitas.

**Ejemplo:**

```bash
Luis practica yoga una vez por semana.
Luis toma lorazepam desde 2024-03.
Luis duerme mal desde hace dos semanas.
```

Este resumen se usa como entrada para el extractor de tripletas.

---

### 3) Resumen → Tripletas (`text2triplets/` → `main_kg.py`)

Convierte el texto en tripletas con formato:

```bash
(sujeto, predicado, objeto)
```

Las tripletas se validan estrictamente contra la estructura fija del dominio.
Tripletas no válidas → descartadas o marcadas como leftover.

---

### 4) Tripletas → Base de Datos (`triplets2bd/`)

Genera scripts SQL o Cypher según el backend elegido:

* `--bd sql`
* `--bd neo4j`

El módulo:

* Limpia la BD (si no se usa `--no-reset`)
* Limpia el log (si no se usa `--no-reset-log`)
* Inserta entidades y relaciones válidas
* Genera scripts deterministas y scripts LLM (modo híbrido)

---

## 🧩 Estructura fija del dominio (OBLIGATORIA)

El dominio del proyecto es **cerrado y obligatorio**.
No se permiten nodos nuevos, relaciones nuevas ni campos nuevos.

### 🗂️ TABLAS PRINCIPALES

```bash
persona(id, user_id, nombre, edad)

sintoma(
  id,
  sintoma_id,
  tipo,
  fecha_inicio,
  fecha_fin,
  categoria,
  frecuencia,
  gravedad
)

actividad(
  id,
  actividad_id,
  nombre,
  categoria,
  frecuencia
)

medicacion(
  id,
  medicacion_id,
  tipo,
  periodicidad
)
```

### 🔗 TABLAS RELACIONALES

```bash
persona_toma_medicacion(persona_id, medicacion_id)
persona_padece_sintoma(persona_id, sintoma_id)
persona_realiza_actividad(persona_id, actividad_id)
```

✔ El pipeline SOLO inyecta información dentro de esta estructura  
✔ Las tripletas deben mapear estrictamente a estas tablas

---

## ⚙️ Configuración

### 1. Crear entorno virtual

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Crear archivo `.env`

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=***

# Backend LLM
LLAMUS_BACKEND=OPENAI
LLAMUS_API_KEY=***
LLAMUS_URL=***
OLLAMA_URL=***

# OPENAI
OPENAI_API_BASE=***
OPENAI_API_KEY=***

# Modelos
MODEL_TRIPLETAS_CYPHER=qwen2.5:32b
MODEL_KG_GEN=openai/qwen2.5:14b
MODEL_CONV2TEXT=qwen2.5:32b
MODEL_CONV=hermes3:8b


```

---

## 🗣️ Módulos del Pipeline

### `conv` — Conversación → Paquetitos

**Ejecutar:**

```bash
python -m conv.main_conv
```

---

### `conv2text` — Conversación → Resumen

Basado en `main_conv2text.py`:

**Ejecutar:**

```bash
python -m conv2text.main_conv2text --text-key TEXT1
```

#### 🚩 Flags Completas (conv2text)

| Flag | Uso |
|------|-----|
| `--in RUTA` | Entrada manual (si no usas `--text-key`) |
| `--out RUTA` | Guarda el resumen |
| `--max N` | Máx. frases del resumen |
| `--temp X` | Temperatura del LLM |
| `--text-key CLAVE` | Usa texto de conv2text/texts.py |
| `--list-texts` | Lista textos disponibles |
| `--sqlite-db RUTA` | Base SQLite para log |
| `--no-reset-log` | No limpiar tabla `log` |
| `--generate-report` | Genera informe SQLite |
| `--report-out` | Ruta del informe |
| `--report-limit` | Nº filas por tabla |

---

### `text2triplets` — Texto → Tripletas

Basado en `main_kg.py`.

**Ejecutar:**

```bash
python -m text2triplets.main_kg --text TEXT1
```

#### 🚩 Flags Completas (main_kg.py)

| Flag | Uso |
|------|-----|
| `--mode llm` | Extractor LLM |
| `--mode kggen` | Extractor KG-Base |
| `--text TEXTX` | Selecciona texto de texts.py |
| `--model` | Sobrescribe el modelo |
| `--context` | Ontología/Contexto |
| `--no-drop` | No descartar inválidas |
| `--sqlite-db RUTA` | Log de tripletas |
| `--no-reset-log` | No limpiar log |
| `--generate-report` | Genera informe SQLite |
| `--report-path` | Ruta del informe |
| `--report-sample-limit N` | Nº filas por tabla |

---

### `triplets2bd` — Tripletas → SQL / Cypher

Basado en `main_tripletas_bd.py`.

**Ejecutar:**

```bash
python -m triplets2bd.main_tripletas_bd --bd sql
```

#### 🚩 Flags Completas

| Flag | Uso |
|------|-----|
| `--bd sql` | SQLite |
| `--bd neo4j` | Neo4j |
| `--llm` | Solo LLM |
| `--no-llm` | Solo determinista |
| (sin flags) | Híbrido |
| `--no-reset` | No resetear BD |
| `--no-reset-log` | No limpiar tabla log |
| `--triplets-json STR` | Tripletas como JSON string |
| `--triplets-file RUTA` | Tripletas desde fichero |

---

## 🔄 Pipelines del proyecto

### Tabla comparativa

| Script | Conversación | Resetea BD | Imprime | Guarda archivo | Uso |
|--------|--------------|------------|---------|----------------|-----|
| `conversation_pipeline.py` | Sí | Sí | Sí | Sí (`pipelines/pipeline.txt`) | Flujo real |
| `processing_pipeline.py` | No | No | No | Sí | Producción |
| `processing_pipeline_debug.py` | No | Opcional | Sí | No | Depuración |

---

## 🧠 Ejemplo de uso completo

```bash
# 1. Conversación real
python -m conversation_pipeline

# 2. Ver salida del pipeline
type pipelines/pipeline.txt

# 3. Debug completo manual
python -m processing_pipeline_debug
```

---

## 📍 Créditos

Proyecto desarrollado en la **Universidad de Sevilla**
