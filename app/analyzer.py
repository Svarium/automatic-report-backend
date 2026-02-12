import pandas as pd
from datetime import datetime
from app.utils import (
    parse_percentage,
    parse_fraction,
    days_since,
    safe_round,
    school_id_from_filename,
)

VITALITY_DAYS = 30
RECENT_PROGRESS_DAYS = 15


# Mapeo reporte nuevo → nombres canónicos (mismos que reporte original)
NEW_REPORT_COLUMN_MAP = {
    "Usuario": "Estudiante",
    "Certificación": "Ruta",
    "Progreso en cursos": "Cursos completos",
    "Último login": "Último inicio de sesión (UTC-3)",
    "Último progreso": "Último progreso (UTC-3)",
}


def _normalize_columns_and_school(df, filename):
    """Detecta formato (original vs nuevo), normaliza columnas y devuelve school_id."""
    df.columns = [str(c).strip() for c in df.columns]

    is_new_format = "Certificación" in df.columns and "Usuario" in df.columns

    if is_new_format:
        rename = {k: v for k, v in NEW_REPORT_COLUMN_MAP.items() if k in df.columns}
        df = df.rename(columns=rename)
        school_id = school_id_from_filename(filename)
    else:
        school_id = df["Escuela"].iloc[0] if "Escuela" in df.columns else school_id_from_filename(filename)

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
    # Filtrar filas inválidas (ruta vacía, "Filtros aplicados")
    # --------------------------------------------------
    if "Ruta" not in df.columns:
        raise ValueError("El archivo no tiene el formato esperado. No se encontró la columna 'Ruta' (o 'Certificación'). Asegúrate de estar subiendo el reporte correcto.")
    
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

        df_students["last_login_days"] = df_students["Último inicio de sesión (UTC-3)"].apply(days_since)
        df_students["last_progress_days"] = df_students["Último progreso (UTC-3)"].apply(days_since)

        df_students["active_30d"] = df_students["last_login_days"] <= VITALITY_DAYS
        df_students["progress_15d"] = df_students["last_progress_days"] <= RECENT_PROGRESS_DAYS

        students_summary = {
            "digital_vitality_30d_avg": safe_round(df_students["active_30d"].mean() * 100),
            "recent_progress_15d_avg": safe_round(df_students["progress_15d"].mean() * 100),
        }

        groups = []
        for route, gdf in df_students.groupby("Ruta"):
            groups.append({
                "route_name": route,
                "route_type": "students",
                "students_count": len(gdf),
                "metrics": {
                    "classes_completion_percent": safe_round(gdf["classes_percent"].mean()),
                    "digital_vitality_30d_percent": safe_round(gdf["active_30d"].mean() * 100),
                    "courses_completion_percent": safe_round(gdf["courses_percent"].mean()),
                    "recent_progress_15d_percent": safe_round(gdf["progress_15d"].mean() * 100),
                }
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
