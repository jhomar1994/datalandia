"""Demo batch configurable: muestra TLC → Storage → Dataflow → BigQuery.

Ejecutar genera consumo GCP. La cantidad representa viajes reales seleccionados, no filas sintéticas.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prueba_escala import execute

DEFAULT_RECORDS = 10000
DEFAULT_WORKERS = 2


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=DEFAULT_RECORDS)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=DEFAULT_WORKERS)
    parser.add_argument("--max-minutes", type=int, default=15)
    parser.add_argument("--input", type=Path, help="Carpeta de muestra local; por defecto una por volumen")
    args = parser.parse_args(argv)
    if not 1 <= args.records <= 3000000 or not 3 <= args.max_minutes <= 45:
        parser.error("records entre 1 y 3000000; max-minutes entre 3 y 45")
    args.input = (args.input or ROOT / f"data/p3/demo_batch_{args.records}").resolve()
    return args


def main(argv=None):
    args = parse_args(argv)
    execute(args.input, args.records, args.workers, args.max_minutes)


if __name__ == "__main__":
    main()
