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

1. El usuario envía un archivo (`.csv` o `.xlsx`) vía POST
2. FastAPI recibe el archivo
3. `analyzer.py`:
   - Lee el archivo con pandas
   - Normaliza columnas
   - Detecta rutas PLD
   - Separa alumnos y docentes
4. Se calculan métricas
5. Se devuelve un JSON estructurado

---

## 📥 Entrada esperada (archivo)

El archivo debe contener columnas como:

- `Escuela`
- `Estudiante`
- `Ruta`
- `% Progreso en ruta`
- `Cursos completos`
- `Último inicio de sesión (UTC-3)`
- `Último progreso (UTC-3)`
- `Clases completas` (para PLD)

El sistema es tolerante a:
- Celdas vacías
- NaN
- Formatos inconsistentes (dentro de lo razonable)

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

#### Conteos

- `total_students`: cantidad de alumnos
- `total_student_groups`: cantidad de rutas NO vacías de alumnos

⚠️ Las rutas PLD y rutas vacías NO cuentan como grupos

#### Métricas calculadas

| Métrica | Descripción |
|---------|-------------|
| `avg_progress_percent` | Promedio de progreso en la ruta |
| `digital_vitality_30d_percent` | % de alumnos activos en los últimos 30 días |
| `courses_completion_percent` | Promedio de cursos completados |
| `recent_progress_15d_percent` | % con progreso reciente |

### 👩‍🏫 Métricas de docentes (PLD)

#### Reglas

- Cada fila PLD = 1 docente
- Se ignora completamente la ruta (no aporta valor)
- El progreso se calcula desde "X de Y"

#### Certificación

```
Progreso = 100% → certificado
```

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
- **Campo**: `file`

### Response

JSON con esta estructura:

```json
{
  "school": {},
  "students": {},
  "teachers_pld": {},
  "metadata": {}
}
```

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

El proyecto incluye funciones para:

- Parsear porcentajes ("75%")
- Parsear fracciones ("30 de 47")
- Calcular días desde una fecha
- Redondear valores de forma segura

Todo el procesamiento es defensivo (no rompe ante errores comunes).

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
- ✔ Métricas consistentes
- ✔ Listo para producción / dashboards

---

## 🧠 TL;DR

Subís un Excel → obtenés un JSON limpio, correcto y pedagógicamente consistente.
