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
