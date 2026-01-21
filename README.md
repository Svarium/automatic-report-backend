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
   - Normaliza nombres de columnas (elimina espacios)
   - Filtra filas inválidas (rutas vacías, "Filtros aplicados", etc.)
   - Identifica el colegio desde la columna `Escuela`
4. **Separación alumnos/docentes**:
   - Detecta rutas que contienen "PLD" (case-insensitive)
   - Crea dos datasets completamente separados: `df_students` y `df_teachers`
5. **Cálculo de métricas**:
   - **Alumnos**: Se agrupan por ruta y se calculan métricas por grupo
   - **Docentes**: Se procesan individualmente y se determina certificación
6. **Respuesta**: Se devuelve un JSON estructurado con toda la información organizada

---

## 📥 Entrada esperada (archivo)

El archivo debe contener las siguientes columnas:

### Columnas principales:
- `Escuela`: Identificador del colegio
- `Estudiante`: Nombre del estudiante o docente
- `Ruta`: Nombre de la ruta educativa (si contiene "PLD" → es docente)

### Columnas para alumnos:
- `Cursos completos`: Formato fracción `"X/Y"` (ej: `"30/47"` o `"47.0/47"`)
- `Clases completas`: Formato fracción `"X/Y"` (ej: `"15/20"` o `"20.0/20"`)
- `Último inicio de sesión (UTC-3)`: Fecha del último login
- `Último progreso (UTC-3)`: Fecha del último progreso registrado

### Columnas para docentes (PLD):
- `Clases completas`: Formato fracción `"X/Y"` (ej: `"47/47"`)

### Tolerancia del sistema:
- ✅ Celdas vacías
- ✅ Valores NaN
- ✅ Formatos inconsistentes (dentro de lo razonable)
- ✅ Rutas vacías (se filtran automáticamente)

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

- **Cada fila PLD = 1 docente** (no se agrupan por ruta)
- Se ignora completamente el nombre de la ruta (no aporta valor analítico)
- El progreso se calcula desde la columna `Clases completas` usando `parse_fraction()`
  - Formato esperado: `"X/Y"` (ej: `"47/47"` o `"35/47"`)
  - Se convierte a porcentaje: `(X/Y) * 100`

#### Certificación docente

```
Si progress_percent == 100% → certified = true
Si progress_percent < 100% → certified = false
```

**Ejemplo**:
- Docente con `Clases completas = "47/47"` → `progress_percent = 100%` → `certified = true`
- Docente con `Clases completas = "35/47"` → `progress_percent = 74.47%` → `certified = false`

#### Summary docentes

- `total_teachers`
- `certified_teachers`
- `certification_rate_percent`

#### Listado de docentes

Cada docente incluye:

```json
{
  "name": "Nombre Apellido",
  "progress_percent": 75.0,
  "certified": false
}
```

❌ No se incluye `route_name` porque no aporta valor analítico

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
        "progress_percent": 100.0,
        "certified": true
      },
      {
        "name": "Juan Pérez",
        "progress_percent": 75.0,
        "certified": false
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
- **`teachers_pld.summary`**: Resumen de docentes (totales y certificados)
- **`teachers_pld.teachers`**: Lista individual de cada docente con su progreso y estado de certificación
- **`metadata`**: Información sobre cuándo se generó el reporte y parámetros usados

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
- **`parse_fraction(value)`**: Convierte fracciones como `"30/47"` o `"47.0/47"` a porcentaje `(30/47)*100 = 63.83`
- **`days_since(date_str)`**: Calcula días transcurridos desde una fecha hasta hoy
- **`safe_round(value)`**: Redondea valores de forma segura, manejando NaN y None

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
