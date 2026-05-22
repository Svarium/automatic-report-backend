from datetime import datetime
import math
import os


def school_id_from_filename(filename):
    """
    Extrae el nombre del colegio desde el nombre del archivo.
    Quita la extensión y espacios al inicio/final. Los espacios en el nombre se conservan.
    """
    if not filename or not isinstance(filename, str):
        return ""
    base = os.path.splitext(filename.strip())[0]
    return base.strip()


def parse_percentage(value):
    """
    '74,5 %' -> 74.5
    """
    try:
        if value is None or value == "":
            return 0.0
        if isinstance(value, str):
            value = value.replace("%", "").replace(",", ".").strip()
        return float(value)
    except:
        return 0.0


def parse_fraction(value):
    """
    '20/40' -> 50.0
    """
    try:
        if value is None or value == "":
            return 0.0
        completed, total = value.split("/")
        completed = float(completed)
        total = float(total)
        if total == 0:
            return 0.0
        return (completed / total) * 100
    except:
        return 0.0


def parse_completed_classes(value):
    """
    '20/40' -> 20.0
    Devuelve solo el número de clases completadas (X en 'X/Y').
    """
    try:
        if value is None or value == "":
            return 0.0
        completed, _ = value.split("/")
        completed = float(completed)
        return completed
    except:
        return 0.0


def parse_total_fraction(value):
    """
    '20/40' -> 40 (solo el denominador Y).
    """
    try:
        if value is None or value == "":
            return 0
        _, total = value.split("/")
        total = float(total)
        # Si viene como 47.0 lo mostramos como entero 47
        return int(total) if total.is_integer() else int(total)
    except:
        return 0


def is_fraction_xy_complete(value):
    """
    True si en 'X/Y' el progreso está completo: X == Y (ej. 4/4, 2/2) y Y > 0.
    No cuenta avance parcial (ej. 2/4).
    """
    try:
        if value is None or value == "":
            return False
        left, right = value.split("/")
        x = float(left)
        y = float(right)
        if y <= 0:
            return False
        return abs(x - y) < 1e-9
    except:
        return False


def days_since(value):
    """
    Fecha -> días desde hoy
    """
    try:
        if not value or value == "":
            return 999
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        return (datetime.now() - value).days
    except:
        return 999


def safe_round(value, digits=1):
    """
    Evita NaN / inf en JSON
    """
    if value is None or isinstance(value, float) and math.isnan(value):
        return 0.0
    return round(value, digits)
