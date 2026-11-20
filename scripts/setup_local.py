"""Crea directorios de trabajo sin modificar datos ni resultados existentes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    "data/raw/nyc_tlc", "data/raw/uber_movement", "data/raw/ine",
    "data/raw/array_of_things", "data/silver", "data/gold",
    "data/muestras_gcp", "data/p2/silver", "data/p2/gold",
    "data/p2/stream/input", "notebooks", "docs/evidencias",
    "reports/parte_1", "reports/parte_2", "referencias_locales",
)


def main():
    for directory in DIRECTORIES:
        path = ROOT / directory
        path.mkdir(parents=True, exist_ok=True)
        print(f"[CARPETA] Creada o verificada: {path}")


if __name__ == "__main__":
    main()
