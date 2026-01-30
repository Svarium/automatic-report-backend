# 📊 Reporte Automático Educativo — Backend

Este proyecto es un **backend en Python** que procesa reportes educativos (CSV o Excel) exportados desde plataformas educativas y genera un **análisis estructurado en JSON**, separando claramente:

- 📘 **Alumnos**
- 👩‍🏫 **Docentes (PLD)**

El objetivo es transformar un archivo "crudo" en un **reporte limpio, consistente y reutilizable**, listo para ser consumido por:
- Dashboards
- PDFs automáticos
- APIs
- Análisis posteriores con IA

---

## 🧠 Concepto clave del sistema

El archivo de entrada contiene **alumnos y docentes mezclados**.

La **clave conceptual** del sistema es:

> 🔥 **Toda ruta cuyo nombre contiene "PLD" corresponde a DOCENTES, no a alumnos**

Esto impacta directamente en:
- Conteo de alumnos
- Conteo de grupos
- Métricas de progreso
- Certificación docente

---

## 🏗️ Arquitectura general

```
backend/
│
├── app/
│   ├── main.py          # FastAPI app + endpoint
│   ├── analyzer.py      # Lógica central de análisis (core)
│   ├── utils.py         # Helpers de parsing y normalización
│   └── __init__.py
│
├── .venv/               # Entorno virtual (local)
├── requirements.txt
└── README.md
```

---

## 🔄 Flujo de información (end-to-end)

### Paso a paso detallado:

1. **Recepción**: El usuario envía un archivo (`.csv` o `.xlsx`) vía POST al endpoint `/analyze-report`
2. **Lectura**: FastAPI recibe el archivo y lo pasa a `analyzer.py`
3. **Procesamiento inicial** (`analyzer.py`):
   - Lee el archivo con pandas
   - Detecta formato (original vs nuevo) y normaliza nombres de columnas al esquema canónico
   - Identifica el colegio: columna `Escuela` (formato original) o **nombre del archivo sin extensión** (formato nuevo)
   - Filtra filas inválidas (rutas vacías, "Filtros aplicados", etc.)
4. **Separación alumnos/docentes**:
   - Detecta rutas que contienen "PLD" (case-insensitive)
   - Crea dos datasets completamente separados: `df_students` y `df_teachers`
5. **Cálculo de métricas**:
   - **Alumnos**: Se agrupan por ruta y se calculan métricas por grupo
   - **Docentes**: Se agrupan por nombre (persona); cada docente puede tener varias certificaciones (PLD), cada una con su progreso y estado de certificación
6. **Respuesta**: Se devuelve un JSON estructurado con toda la información organizada

---

## 📥 Entrada esperada (archivo)

El backend acepta **dos formatos de reporte**. Se detecta automáticamente por la presencia de las columnas `Certificación` y `Usuario` (formato nuevo) o las columnas originales.

### Formato original (reporte antiguo)

- `Escuela`: Identificador del colegio (se usa para `school.id`)
- `Estudiante`: Nombre del estudiante o docente
- `Ruta`: Nombre de la ruta educativa (si contiene "PLD" → es docente)
- `Cursos completos`: Formato fracción `"X/Y"` (ej: `"30/47"` o `"47.0/47"`)
- `Clases completas`: Formato fracción `"X/Y"`
- `Último inicio de sesión (UTC-3)`: Fecha del último login
- `Último progreso (UTC-3)`: Fecha del último progreso registrado

### Formato nuevo (reporte con certificaciones por fila)

| Columna en el archivo | Equivale a (lógica interna) |
|----------------------|-----------------------------|
| **Usuario** (A) | Estudiante (nombre) |
| **Certificación** (C) | Ruta (si contiene "PLD" → docente) |
| **Progreso en cursos** (D) | Cursos completos (fracción, ej: `44/47`) |
| **Clases completas** (E) | Clases completas (fracción, ej: `44/47`) |
| **Último progreso** (F) | Último progreso (UTC-3) |
| **Último login** (G) | Último inicio de sesión (UTC-3) |

- **Nombre del colegio (`school.id`)**: En el formato nuevo no hay columna "Escuela". El nombre del colegio se toma del **nombre del archivo** subido (sin extensión, espacios al inicio/final eliminados). Se recomienda que los mentores guarden el reporte con el nombre correcto del colegio.
- Columnas ignoradas en el formato nuevo: Email (B), Fecha de inscripción (H), track_id (I), user_id (J).

### Tolerancia del sistema:
- ✅ Celdas vacías
- ✅ Valores NaN
- ✅ Formatos inconsistentes (dentro de lo razonable)
- ✅ Rutas vacías (se filtran automáticamente)
- ✅ Fracciones con enteros (`44/47`) o decimales (`44.0/47`)

---

## 🔍 Lógica clave de negocio

### 1️⃣ Identificación de docentes (PLD)

```python
df["is_pld"] = df["Ruta"].str.contains("PLD", case=False, na=False)
# Si una fila tiene PLD en la ruta → es docente
# Nunca se mezcla con alumnos
```

### 2️⃣ Separación absoluta de datasets

```python
df_students = df[~df["is_pld"]].copy()
df_teachers = df[df["is_pld"]].copy()
```

A partir de acá:

- ❌ Nunca se cruzan métricas
- ❌ Nunca se agrupan juntos
- ❌ Nunca se cuentan juntos

### 👨‍🎓 Métricas de alumnos

#### Conteos a nivel colegio

- `total_students`: Cantidad total de alumnos (filas que NO tienen "PLD" en la ruta)
- `total_student_groups`: Cantidad de rutas únicas de alumnos (sin contar PLD ni rutas vacías)

⚠️ **Importante**: Las rutas PLD y rutas vacías NO cuentan como grupos de estudiantes

#### Procesamiento por grupo

1. Los alumnos se **agrupan por ruta** (`Ruta`)
2. Para cada grupo se calculan las métricas promedio de todos sus alumnos
3. Cada grupo aparece como un objeto en el array `students.groups`

#### Métricas calculadas (por grupo/ruta)

Cada grupo de estudiantes tiene las siguientes métricas:

| Métrica | Descripción | Fuente de datos |
|---------|-------------|-----------------|
| `classes_completion_percent` | **Promedio porcentual de clases completadas** de todos los alumnos de esa ruta | Columna `Clases completas` (formato `"X/Y"` → `(X/Y)*100`) |
| `courses_completion_percent` | Promedio porcentual de cursos completados de todos los alumnos de esa ruta | Columna `Cursos completos` (formato `"X/Y"` → `(X/Y)*100`) |
| `digital_vitality_30d_percent` | % de alumnos que iniciaron sesión en los últimos 30 días | Columna `Último inicio de sesión (UTC-3)` |
| `recent_progress_15d_percent` | % de alumnos con progreso registrado en los últimos 15 días | Columna `Último progreso (UTC-3)` |

**Nota importante**: `classes_completion_percent` se calcula así:
1. Para cada alumno de la ruta, se toma el valor de `Clases completas` (ej: `"15/20"`)
2. Se parsea la fracción usando `parse_fraction()` → `(15/20) * 100 = 75%`
3. Se promedian todos los porcentajes de los alumnos de esa ruta
4. El resultado se redondea con `safe_round()` y se envía como `classes_completion_percent`

**Ejemplo práctico**:
- Ruta "Matemáticas" tiene 3 alumnos:
  - Alumno 1: `"18/20"` → 90%
  - Alumno 2: `"15/20"` → 75%
  - Alumno 3: `"20/20"` → 100%
- `classes_completion_percent` = `(90 + 75 + 100) / 3 = 88.33%`

### 👩‍🏫 Métricas de docentes (PLD)

#### Reglas de procesamiento

- **Un mismo docente puede aparecer en varias filas** (una por certificación/PLD que está cursando).
- El backend **agrupa por nombre** (persona) y, para cada docente, lista **todas las certificaciones (PLD)** en las que figura.
- El progreso de cada PLD se calcula desde la columna `Clases completas` usando `parse_fraction()` (formato `"X/Y"`).
- Por cada PLD: `progress_percent == 100%` → `certified = true` en esa certificación.

#### Summary docentes

- `total_teachers`: cantidad de **docentes únicos** (personas).
- `certified_teachers`: cantidad de docentes que tienen **al menos una** certificación al 100%.
- `certification_rate_percent`: `certified_teachers / total_teachers * 100`.

#### Listado de docentes

Cada docente incluye su nombre y la lista de PLD en los que figura:

```json
{
  "name": "Nombre Apellido",
  "plds": [
    { "certification_name": "PLD Matemáticas", "progress_percent": 100.0, "certified": true },
    { "certification_name": "PLD Lengua", "progress_percent": 75.0, "certified": false }
  ]
}
```

---

## 🧪 Endpoint disponible

**POST** `/analyze-report`

### Request

- **Tipo**: `multipart/form-data`
- **Campo**: `file` (archivo `.csv` o `.xlsx`)

### Response

JSON estructurado con la siguiente arquitectura:

```json
{
  "school": {
    "id": "Nombre del colegio",
    "total_students": 150,
    "total_student_groups": 8
  },
  "students": {
    "summary": {
      "digital_vitality_30d_avg": 75.5,
      "recent_progress_15d_avg": 60.2
    },
    "groups": [
      {
        "route_name": "Ruta de Matemáticas",
        "route_type": "students",
        "students_count": 25,
        "metrics": {
          "classes_completion_percent": 85.3,
          "courses_completion_percent": 72.1,
          "digital_vitality_30d_percent": 80.0,
          "recent_progress_15d_percent": 65.0
        }
      },
      {
        "route_name": "Ruta de Lengua",
        "route_type": "students",
        "students_count": 30,
        "metrics": {
          "classes_completion_percent": 90.5,
          "courses_completion_percent": 78.3,
          "digital_vitality_30d_percent": 85.0,
          "recent_progress_15d_percent": 70.0
        }
      }
    ]
  },
  "teachers_pld": {
    "summary": {
      "total_teachers": 10,
      "certified_teachers": 7,
      "certification_rate_percent": 70.0
    },
    "teachers": [
      {
        "name": "María González",
        "plds": [
          { "certification_name": "PLD Matemáticas", "progress_percent": 100.0, "certified": true },
          { "certification_name": "PLD Lengua", "progress_percent": 75.0, "certified": false }
        ]
      },
      {
        "name": "Juan Pérez",
        "plds": [
          { "certification_name": "PLD Ciencias", "progress_percent": 75.0, "certified": false }
        ]
      }
    ]
  },
  "metadata": {
    "generated_at": "2024-01-15T10:30:00",
    "vitality_window_days": 30,
    "recent_progress_window_days": 15
  }
}
```

### Estructura de la respuesta explicada:

- **`school`**: Información general del colegio y conteos totales
- **`students.summary`**: Métricas agregadas de todos los alumnos (sin agrupar por ruta)
- **`students.groups`**: Array con un objeto por cada ruta de alumnos, incluyendo:
  - Nombre de la ruta y cantidad de estudiantes
  - Métricas específicas de esa ruta (incluyendo `classes_completion_percent`)
- **`teachers_pld.summary`**: Resumen de docentes (totales únicos y cuántos tienen al menos una certificación al 100%)
- **`teachers_pld.teachers`**: Lista de docentes; cada uno tiene `name` y `plds` (array de certificaciones con `certification_name`, `progress_percent`, `certified`)
- **`metadata`**: Información sobre cuándo se generó el reporte y parámetros usados

---

## 📱 Guía para el front: consumir la nueva estructura de docentes (PLD)

Esta sección explica en detalle el cambio en `teachers_pld` para que el front pueda mostrar correctamente a los docentes y sus certificaciones.

### ¿Qué cambió y por qué?

**Antes** (reporte antiguo): cada docente aparecía como máximo una vez. La respuesta traía un objeto por docente con un único progreso y un único estado de certificación:

```json
{
  "name": "María González",
  "progress_percent": 100.0,
  "certified": true
}
```

**Ahora** (reporte nuevo): un mismo docente puede estar cursando **varias certificaciones (PLD)** a la vez. Por eso la respuesta agrupa por persona y, dentro de cada docente, lista **todas** sus certificaciones con el progreso y el estado de cada una.

La estructura actual es:

```json
{
  "name": "María González",
  "plds": [
    { "certification_name": "PLD Matemáticas", "progress_percent": 100.0, "certified": true },
    { "certification_name": "PLD Lengua", "progress_percent": 75.0, "certified": false }
  ]
}
```

- **`name`**: nombre del docente (persona). Es único en la lista `teachers`.
- **`plds`**: array de certificaciones en las que figura ese docente. Cada elemento es una certificación distinta (PLD) con:
  - **`certification_name`**: nombre de la certificación/ruta (ej. "PLD Matemáticas").
  - **`progress_percent`**: progreso en esa certificación (0–100). Viene de la columna "Clases completas" (fracción X/Y convertida a %).
  - **`certified`**: `true` si en esa certificación llegó al 100%; `false` si no.

### Cómo consumirlo en el front

1. **Listar docentes**: iterar sobre `response.teachers_pld.teachers`. Cada elemento es un docente (persona) con `name` y `plds`.
2. **Por cada docente, listar sus certificaciones**: iterar sobre `teacher.plds`. Cada elemento es una certificación con `certification_name`, `progress_percent` y `certified`.
3. **Dejar de usar** en cada docente:
   - `progress_percent` (ya no existe a nivel docente).
   - `certified` (ya no existe a nivel docente).
4. **Usar en su lugar**:
   - Para mostrar “progreso del docente”: puede ser el progreso de cada PLD en `teacher.plds[].progress_percent`, o un resumen (ej. “X de Y certificaciones al 100%”).
   - Para “¿está certificado?”: depende del diseño. Opciones típicas:
     - “Certificado” = tiene **al menos una** certificación al 100% → `teacher.plds.some(p => p.certified)`.
     - Mostrar por certificación: “PLD Matemáticas: 100% ✓” y “PLD Lengua: 75%”.

### Resumen (`teachers_pld.summary`)

- **`total_teachers`**: cantidad de **personas** (docentes únicos). No es la cantidad de filas ni de certificaciones.
- **`certified_teachers`**: cantidad de docentes que tienen **al menos una** certificación con `certified: true`.
- **`certification_rate_percent`**: `(certified_teachers / total_teachers) * 100`. Porcentaje de docentes que tienen al menos un PLD al 100%.

Ejemplo: 10 docentes, 7 con al menos una certificación al 100% → `total_teachers: 10`, `certified_teachers: 7`, `certification_rate_percent: 70.0`.

### Ejemplo de uso en código (pseudocódigo)

```javascript
// Listar docentes y sus certificaciones
response.teachers_pld.teachers.forEach(teacher => {
  console.log(teacher.name);
  teacher.plds.forEach(pld => {
    console.log(`  - ${pld.certification_name}: ${pld.progress_percent}% ${pld.certified ? '✓' : ''}`);
  });
});

// Saber si un docente tiene al menos una certificación al 100%
const hasAnyCertified = teacher.plds.some(p => p.certified);

// Contar cuántas certificaciones completó (al 100%)
const certifiedCount = teacher.plds.filter(p => p.certified).length;
```

### Compatibilidad con el reporte antiguo

Si el backend recibe un **reporte en formato antiguo**, cada docente sigue teniendo una sola fila, así que cada uno tendrá **un solo elemento** en `plds`. La estructura es la misma: `name` + `plds` (array de uno o más elementos). El front puede asumir siempre que existe `teachers[].plds` y recorrerlo; no hace falta una rama especial para “formato viejo”.

---

## 🚀 Cómo levantar el proyecto (paso a paso)

### 1️⃣ Clonar o copiar el proyecto

```bash
git clone <repo>
cd backend
```

### 2️⃣ Crear entorno virtual (recomendado)

```bash
python -m venv .venv
```

**Activar:**

**Windows:**
```bash
.venv\Scripts\activate
```

**Mac / Linux:**
```bash
source .venv/bin/activate
```

### 3️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4️⃣ Levantar el servidor

```bash
uvicorn app.main:app --reload
```

Servidor disponible en:

```
http://127.0.0.1:8000
```

### 5️⃣ Probar con Postman

- **Método**: POST
- **URL**: `http://127.0.0.1:8000/analyze-report`
- **Body** → `form-data`
  - **Key**: `file`
  - **Value**: archivo `.csv` o `.xlsx`

---

## 🧰 Utilidades internas (utils.py)

El proyecto incluye funciones helper para:

- **`parse_percentage(value)`**: Convierte strings como `"75%"` a número `75.0`
- **`parse_fraction(value)`**: Convierte fracciones como `"30/47"` o `"44/47"` a porcentaje `(X/Y)*100`
- **`days_since(date_str)`**: Calcula días transcurridos desde una fecha hasta hoy
- **`safe_round(value)`**: Redondea valores de forma segura, manejando NaN y None
- **`school_id_from_filename(filename)`**: Extrae el nombre del colegio desde el nombre del archivo (sin extensión, sin espacios al inicio/final)

**Uso en el código**:
- `Cursos completos` y `Clases completas` usan `parse_fraction()` porque vienen en formato `"X/Y"`
- Las fechas usan `days_since()` para calcular actividad reciente
- Todos los valores finales pasan por `safe_round()` para evitar decimales infinitos

Todo el procesamiento es **defensivo** (no rompe ante errores comunes como celdas vacías, formatos raros, etc.).

---

## 🧩 Diseño pensado para extender

Este backend está preparado para:

- Agregar nuevos indicadores
- Exportar a PDF
- Guardar resultados en DB
- Integrar IA para insights automáticos
- Versionar reglas pedagógicas

---

## ✅ Estado actual

- ✔ Separación correcta alumnos / docentes
- ✔ PLD interpretado correctamente
- ✔ Métricas consistentes y bien calculadas
- ✔ `classes_completion_percent` basado en columna `Clases completas` (formato fracción)
- ✔ `courses_completion_percent` basado en columna `Cursos completos` (formato fracción)
- ✔ Cálculo de vitalidad digital y progreso reciente funcionando
- ✔ Certificación docente basada en progreso 100%
- ✔ Listo para producción / dashboards

---

## 🧠 TL;DR

Subís un Excel → obtenés un JSON limpio, correcto y pedagógicamente consistente.
