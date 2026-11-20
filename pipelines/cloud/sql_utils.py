"""Renderiza únicamente identificadores de destino; los datos usan parámetros SQL."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def render_sql(filename, project, dataset):
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        raise ValueError("Project ID inválido")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dataset):
        raise ValueError("Dataset inválido")
    folder = ROOT / "sql/bigquery"
    path = (folder / filename).resolve()
    if path.parent != folder.resolve():
        raise ValueError("La consulta debe pertenecer a sql/bigquery")
    return path.read_text().replace("__PROJECT__", project).replace("__DATASET__", dataset)
