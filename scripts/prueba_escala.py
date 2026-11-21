"""Prepara, sube y procesa una muestra batch; consolida solo tras DONE y verifica cierre.

Ejecutar este comando utiliza GCP y genera consumo. Mantener la laptop activa.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "proyecto-datalandia"


def run(command):
    process = subprocess.Popen([str(item) for item in command], cwd=ROOT)
    try:
        code = process.wait()
    except KeyboardInterrupt:
        # El controlador atiende SIGTERM y cancela su propio job antes de salir.
        if process.poll() is None:
            process.terminate()
        print("Interrupción: esperando el cierre del proceso y de su job...", flush=True)
        try:
            process.wait(timeout=240)
        except subprocess.TimeoutExpired:
            raise RuntimeError("No se confirmó el cierre; revisar el job en GCP") from None
        raise
    if code:
        raise RuntimeError(f"Falló {Path(str(command[1])).name} (salida {code})")


def verify_idle():
    commands = [
        ["gcloud", "dataflow", "jobs", "list", "--project=" + PROJECT,
         "--region=us-central1", "--status=active", "--format=json"],
        ["gcloud", "compute", "instances", "list", "--project=" + PROJECT, "--format=json"],
    ]
    counts = []
    for command in commands:
        response = subprocess.run(command, cwd=ROOT, check=True, capture_output=True,
                                  text=True, timeout=60)
        counts.append(len(json.loads(response.stdout)))
    result = {"active_jobs_in_region": counts[0], "vms_in_project": counts[1]}
    if any(counts):
        raise RuntimeError(f"Hay recursos activos; revisar antes de continuar: {result}")
    return result


def execute(bundle, trip_limit, workers, max_minutes):
    local_python = ROOT / ".venv_bigdata/bin/python"
    if not local_python.is_file():
        raise FileNotFoundError("Falta .venv_bigdata; revisar requirements/README.md")
    print("[1/6] Comprobando que no haya cómputo activo...", flush=True)
    verify_idle()
    manifest_file = bundle / "manifest.json"
    if not manifest_file.exists():
        print("[2/6] Preparando muestra local...", flush=True)
        run([local_python, "-m", "pipelines.cloud.preparar_muestras",
             "--trip-limit", trip_limit, "--sensor-limit", "11000", "--output", bundle])
    else:
        print("[2/6] Reutilizando muestra local; se comprobarán sus hashes al subir...", flush=True)
    manifest = json.loads(manifest_file.read_text())
    if manifest.get("counts", {}).get("viajes") != trip_limit:
        raise ValueError("La muestra no tiene el número solicitado de viajes; usar otra --input")

    name = "lumina-p3-scale-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    folder = ROOT / "referencias_locales/escala" / name
    folder.mkdir(parents=True, exist_ok=False)
    staging = folder / "staging.json"
    result = {"name": name, "input_records": trip_limit, "workers_requested": workers,
              "bundle_id": manifest["bundle_id"], "error": None}
    controller_started = False
    try:
        print("[3/6] Subiendo bundle independiente a Storage...", flush=True)
        run([sys.executable, "scripts/stage_inputs.py", "--input", bundle, "--report", staging])
        uri = json.loads(staging.read_text())["uris"]["viajes.jsonl"]
        result["input_uri"] = uri
        print(f"[4/6] Ejecutando batch: {workers} workers, plazo {max_minutes} minutos...", flush=True)
        controller_started = True
        run([sys.executable, "scripts/run_dataflow.py", "--mode", "batch", "--name", name,
             "--input", uri, "--workers", workers, "--max-minutes", max_minutes,
             "--batch-records", trip_limit,
             "--staging-report", staging])
        job = json.loads((ROOT / "referencias_locales/dataflow" / name / "result.json").read_text())
        result["dataflow"] = job
        if job.get("final_state") != "JOB_STATE_DONE" or not job.get("shutdown_confirmed") or job.get("error"):
            raise RuntimeError("El batch no terminó correctamente; no se consolida")
        print("[5/6] Consolidando batch terminado mediante MERGE...", flush=True)
        run([sys.executable, "scripts/finalize_batch.py", "--batch-id", name, "--record-status"])
        result["consolidated"] = True
    except BaseException as error:
        result["error"] = str(error) or type(error).__name__
        raise
    finally:
        try:
            if controller_started:
                print("[6/6] Verificando cero jobs activos y cero VMs...", flush=True)
                result["shutdown"] = verify_idle()
        except Exception as error:
            result["shutdown_error"] = str(error)
            raise
        finally:
            (folder / "resultado.json").write_text(json.dumps(result, indent=2) + "\n")
            print(f"Reporte local: {folder / 'resultado.json'}", flush=True)
    print("Prueba completada y cómputo cerrado. Revisar métricas y conteos por batch_id.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/p3/escala_1m")
    parser.add_argument("--trip-limit", type=int, default=1000000)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--max-minutes", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.trip_limit <= 3000000 or not 3 <= args.max_minutes <= 45:
        parser.error("Viajes entre 1 y 3.000.000; plazo entre 3 y 45 minutos")
    execute(args.input.resolve(), args.trip_limit, args.workers, args.max_minutes)


if __name__ == "__main__":
    main()
