"""Demo streaming configurable: eventos nuevos → Pub/Sub → Dataflow → BigQuery → API/tablero.

Requiere proxy Cloud Run en localhost:8080. Ejecutar genera consumo GCP.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import demo_e2e

DEFAULT_EVENTS = 60
DEFAULT_RATE = 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=DEFAULT_EVENTS,
                        help="Eventos nuevos visibles; se suman 220 de replay, 5 controles y hasta 2 inválidos")
    parser.add_argument("--rate", type=float, default=DEFAULT_RATE, help="Eventos nuevos por segundo")
    parser.add_argument("--api-url", default="http://127.0.0.1:8080")
    args = parser.parse_args(argv)
    demo_e2e.main(["--events", str(args.events), "--rate", str(args.rate), "--api-url", args.api_url])


if __name__ == "__main__":
    main()
