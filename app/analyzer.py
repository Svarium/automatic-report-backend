import pandas as pd
from datetime import datetime
from app.utils import (
    parse_percentage,
    parse_fraction,
    parse_completed_classes,
    parse_total_fraction,
    is_fraction_xy_complete,
    days_since,
    safe_round,
    school_id_from_filename,
)

VITALITY_DAYS = 30
VITALITY_DAYS_15 = 15
RECENT_PROGRESS_DAYS = 15
RECENT_PROGRESS_DAYS_30 = 30


# Mapeo multilingüe (ES, EN, PT) a nombres canónicos internos
MULTILINGUAL_COLUMN_MAP = {
    # Usuario / Estudiante
    "Usuario": "Estudiante",
    "User": "Estudiante",
    "Usuário": "Estudiante",

    # Certificación / Ruta
    "Certificación": "Ruta",
    "Certification": "Ruta",
    "Formaçao": "Ruta",

    # Obligatorios
    "Progreso de cursos obligatorios": "Cursos obligatorios completos",
    "Required courses progress": "Cursos obligatorios completos",
    "Progresso dos cursos obrigatórios": "Cursos obligatorios completos",

    # Progreso en cursos
    "Progreso en cursos": "Cursos completos",
    "Progress in courses": "Cursos completos",
    "Progresso nos cursos": "Cursos completos",

    # Clases completas
    "Clases completas": "Clases completas",
    "Completed lessons": "Clases completas",
    "Lições concluídas": "Clases completas",

    # Último progreso
    "Último progreso": "Último progreso (UTC-3)",
    "Latest Progress": "Último progreso (UTC-3)",
    "Último progresso": "Último progreso (UTC-3)",

    # Último login
    "Último login": "Último inicio de sesión (UTC-3)",
    "Last login": "Último inicio de sesión (UTC-3)",
}

# Columnas indispensables que el backend necesita para procesar
REQUIRED_CANONICAL_COLUMNS = [
    ("Estudiante", "Estudiante / Usuario / User / Usuário"),
    ("Ruta", "Ruta / Certificación / Certification / Formaçao"),
    ("Cursos completos", "Cursos completos / Progreso en cursos / Progress in courses / Progresso nos cursos"),
    ("Clases completas", "Clases completas / Completed lessons / Lições concluídas"),
    ("Último progreso (UTC-3)", "Último progreso / Latest Progress / Último progresso"),
    ("Último inicio de sesión (UTC-3)", "Último login / Last login"),
]


def _normalize_columns_and_school(df, filename):
    """Normaliza columnas en ES/EN/PT y determina school_id."""
    df.columns = [str(c).strip() for c in df.columns]

    # Renombrar columnas multilingües al esquema canónico
    rename = {k: v for k, v in MULTILINGUAL_COLUMN_MAP.items() if k in df.columns}
    if rename:
        df = df.rename(columns=rename)

    if "Escuela" in df.columns and not df["Escuela"].empty:
        school_id = df["Escuela"].iloc[0]
    else:
        school_id = school_id_from_filename(filename)

    return df, school_id


def analyze_report(file):
    # --------------------------------------------------
    # Leer archivo
    # --------------------------------------------------
    if file.filename.endswith(".csv"):
        df = pd.read_csv(file.file)
    else:
        df = pd.read_excel(file.file)

    # --------------------------------------------------
    # Normalizar columnas y obtener school_id (soporta reporte original y nuevo)
    # --------------------------------------------------
    try:
        df, school_id = _normalize_columns_and_school(df, file.filename or "")
    except Exception as e:
        raise ValueError(f"Error al procesar la estructura del archivo: {str(e)}")

    # --------------------------------------------------
    # Validación explícita de columnas requeridas
    # --------------------------------------------------
    missing_cols = [
        label for col, label in REQUIRED_CANONICAL_COLUMNS if col not in df.columns
    ]
    if missing_cols:
        cols_formatted = "\n- ".join(missing_cols)
        raise ValueError(
            f"El archivo no tiene el formato esperado. Faltan las siguientes columnas requeridas (o sus variantes en ES/EN/PT):\n- {cols_formatted}\n\nColumnas detectadas en el archivo: {list(df.columns)}"
        )

    # --------------------------------------------------
    # Filtrar filas inválidas (ruta vacía, "Filtros aplicados")
    # --------------------------------------------------
    df["Ruta"] = df["Ruta"].fillna("").astype(str)
    df = df[df["Ruta"].notna()]
    df = df[df["Ruta"].str.strip() != ""]
    df = df[~df["Ruta"].str.contains("Filtros aplicados", case=False, na=False)]

    # --------------------------------------------------
    # 🔥 FIX PLD — detección correcta (CONTIENTE, no prefijo)
    # --------------------------------------------------
    df["is_pld"] = df["Ruta"].str.contains("PLD", case=False, na=False)

    # Separar alumnos y docentes
    df_students = df[~df["is_pld"]].copy()
    df_teachers = df[df["is_pld"]].copy()

    # ==================================================
    # ALUMNOS
    # ==================================================
    if df_students.empty:
        # Caso especial: el reporte tiene solo PLD (docentes) y ningún alumno
        total_students = 0
        total_groups = 0
        students_summary = {
            "digital_vitality_30d_avg": 0.0,
            "recent_progress_15d_avg": 0.0,
            "mandatory_courses_full_completion_percent": None,
        }
        groups = []
    else:
        total_students = len(df_students)

        # 👉 contar SOLO rutas de alumnos válidas
        df_students_valid_routes = df_students[df_students["Ruta"].str.strip() != ""]
        total_groups = df_students_valid_routes["Ruta"].nunique()

        # Preparar columnas
        df_students["courses_percent"] = df_students["Cursos completos"].apply(parse_fraction)
        df_students["classes_percent"] = df_students["Clases completas"].apply(parse_fraction)
        df_students["classes_completed"] = df_students["Clases completas"].apply(parse_completed_classes)
        # Totales fijos por certificación/ruta (Y en 'X/Y')
        df_students["classes_total"] = df_students["Clases completas"].apply(parse_total_fraction)
        df_students["courses_total"] = df_students["Cursos completos"].apply(parse_total_fraction)

        has_mandatory_courses = "Cursos obligatorios completos" in df_students.columns
        if has_mandatory_courses:
            df_students["mandatory_courses_percent"] = df_students["Cursos obligatorios completos"].apply(
                parse_fraction
            )
            df_students["mandatory_courses_total"] = df_students["Cursos obligatorios completos"].apply(
                parse_total_fraction
            )
            df_students["mandatory_all_done"] = df_students["Cursos obligatorios completos"].apply(
                is_fraction_xy_complete
            )

        df_students["last_login_days"] = df_students["Último inicio de sesión (UTC-3)"].apply(days_since)
        df_students["last_progress_days"] = df_students["Último progreso (UTC-3)"].apply(days_since)

        df_students["active_30d"] = df_students["last_login_days"] <= VITALITY_DAYS
        df_students["active_15d"] = df_students["last_login_days"] <= VITALITY_DAYS_15
        df_students["progress_15d"] = df_students["last_progress_days"] <= RECENT_PROGRESS_DAYS
        df_students["progress_30d"] = df_students["last_progress_days"] <= RECENT_PROGRESS_DAYS_30

        students_summary = {
            "digital_vitality_30d_avg": safe_round(df_students["active_30d"].mean() * 100),
            "recent_progress_15d_avg": safe_round(df_students["progress_15d"].mean() * 100),
        }
        if has_mandatory_courses:
            students_summary["mandatory_courses_full_completion_percent"] = safe_round(
                df_students["mandatory_all_done"].mean() * 100
            )
        else:
            students_summary["mandatory_courses_full_completion_percent"] = None

        groups = []
        for route, gdf in df_students.groupby("Ruta"):
            # Se asume (según tu regla) que el denominador es consistente dentro del grupo
            classes_total = int(gdf["classes_total"].iloc[0]) if not gdf["classes_total"].empty else 0
            courses_total = int(gdf["courses_total"].iloc[0]) if not gdf["courses_total"].empty else 0

            classes_val = safe_round(gdf["classes_completed"].mean())
            courses_val = safe_round(gdf["courses_percent"].mean())
            metrics = {
                # Plantilla requerida por el front: "{valor} de {total} <clases/cursos> totales"
                "classes_completion_percent": f"{classes_val} de {classes_total} clases totales",
                "digital_vitality_30d_percent": safe_round(gdf["active_30d"].mean() * 100),
                "digital_vitality_15d_percent": safe_round(gdf["active_15d"].mean() * 100),
                "courses_completion_percent": f"{courses_val} de {courses_total} cursos totales",
                "recent_progress_15d_percent": safe_round(gdf["progress_15d"].mean() * 100),
                "recent_progress_30d_percent": safe_round(gdf["progress_30d"].mean() * 100),
            }
            if has_mandatory_courses:
                mandatory_total = (
                    int(gdf["mandatory_courses_total"].iloc[0]) if not gdf["mandatory_courses_total"].empty else 0
                )
                mandatory_val = safe_round(gdf["mandatory_courses_percent"].mean())
                metrics["mandatory_courses_completion_percent"] = (
                    f"{mandatory_val} de {mandatory_total} cursos obligatorios totales"
                )
            else:
                metrics["mandatory_courses_completion_percent"] = None

            groups.append({
                "route_name": route,
                "route_type": "students",
                "students_count": len(gdf),
                "metrics": metrics,
            })

    # ==================================================
    # DOCENTES (PLD) — un docente puede tener varias certificaciones (varias filas)
    # ==================================================
    teachers = []

    if not df_teachers.empty:
        df_teachers["progress_percent"] = df_teachers["Clases completas"].apply(parse_fraction)
        df_teachers["certified"] = df_teachers["progress_percent"] == 100

        for name, group in df_teachers.groupby("Estudiante"):
            plds = []
            for _, row in group.iterrows():
                plds.append({
                    "certification_name": row["Ruta"],
                    "progress_percent": safe_round(row["progress_percent"]),
                    "certified": bool(row["certified"]),
                })
            teachers.append({
                "name": name,
                "plds": plds,
            })

        total_teachers = len(teachers)
        certified_teachers = sum(1 for t in teachers if any(p["certified"] for p in t["plds"]))
        teachers_summary = {
            "total_teachers": total_teachers,
            "certified_teachers": certified_teachers,
            "certification_rate_percent": safe_round(certified_teachers / total_teachers * 100) if total_teachers else 0.0,
        }
    else:
        teachers_summary = {
            "total_teachers": 0,
            "certified_teachers": 0,
            "certification_rate_percent": 0.0,
        }

    # ==================================================
    # RESPONSE
    # ==================================================
    return {
        "school": {
            "id": school_id,
            "total_students": total_students,
            "total_student_groups": total_groups
        },
        "students": {
            "summary": students_summary,
            "groups": groups
        },
        "teachers_pld": {
            "summary": teachers_summary,
            "teachers": teachers
        },
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "vitality_window_days": VITALITY_DAYS,
            "recent_progress_window_days": RECENT_PROGRESS_DAYS
        }
    }
