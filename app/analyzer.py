import pandas as pd
from datetime import datetime
from app.utils import (
    parse_percentage,
    parse_fraction,
    days_since,
    safe_round
)

VITALITY_DAYS = 30
RECENT_PROGRESS_DAYS = 15


def analyze_report(file):
    # --------------------------------------------------
    # Leer archivo
    # --------------------------------------------------
    if file.filename.endswith(".csv"):
        df = pd.read_csv(file.file)
    else:
        df = pd.read_excel(file.file)

    # --------------------------------------------------
    # Normalizar nombres de columnas
    # --------------------------------------------------
    df = df[df["Ruta"].notna()]
    df = df[df["Ruta"].str.strip() != ""]
    # Eliminar filas de "Filtros aplicados"
    df = df[~df["Ruta"].str.contains("Filtros aplicados", case=False, na=False)]
    df.columns = [c.strip() for c in df.columns]

    # Normalizar Ruta (evita errores con NaN)
    df["Ruta"] = df["Ruta"].fillna("").astype(str)

    # --------------------------------------------------
    # Identificar colegio
    # --------------------------------------------------
    school_id = df["Escuela"].iloc[0]

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
    # DOCENTES (PLD)
    # ==================================================
    teachers = []

    if not df_teachers.empty:
        # progreso desde "X de Y"
        df_teachers["progress_percent"] = df_teachers["Clases completas"].apply(parse_fraction)
        df_teachers["certified"] = df_teachers["progress_percent"] == 100

        for _, row in df_teachers.iterrows():
            teachers.append({
                "name": row["Estudiante"],                
                "progress_percent": safe_round(row["progress_percent"]),
                "certified": bool(row["certified"])
            })

        teachers_summary = {
            "total_teachers": len(df_teachers),
            "certified_teachers": int(df_teachers["certified"].sum()),
            "certification_rate_percent": safe_round(df_teachers["certified"].mean() * 100),
        }

    else:
        teachers_summary = {
            "total_teachers": 0,
            "certified_teachers": 0,
            "certification_rate_percent": 0,
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
