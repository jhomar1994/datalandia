"""Lanza un solo worker privado y vigila su terminación con un límite de tiempo.

El proceso debe permanecer activo mientras exista el job. Los logs y reportes van
a referencias_locales/dataflow/. No registra tokens ni modifica el proyecto del CLI.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {"JOB_STATE_DONE", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_DRAINED", "JOB_STATE_UPDATED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["batch", "stream"], required=True)
    parser.add_argument("--input", help="URI GCS de viajes para batch")
    parser.add_argument("--max-minutes", type=int, default=12)
    parser.add_argument("--name")
    parser.add_argument("--stop-file", type=Path, help="En streaming solicita drain cuando aparece")
    args = parser.parse_args()
    if not 3 <= args.max_minutes <= 15:
        parser.error("El límite de esta demo debe estar entre 3 y 15 minutos")
    if args.mode == "batch" and not args.input:
        parser.error("batch requiere --input")
    raw = subprocess.run(["terraform", "-chdir=infra/terraform", "output", "-json"], cwd=ROOT,
                         check=True, capture_output=True, text=True).stdout
    config = {key: value["value"] for key, value in json.loads(raw).items()}
    target = config["project"]
    if target["id"] != "proyecto-datalandia" or str(target["number"]) != "637872675138":
        raise ValueError("Destino Terraform no autorizado")
    staging = json.loads((ROOT / "referencias_locales/p3_staging.json").read_text())
    now = dt.datetime.now(dt.timezone.utc)
    name = args.name or f"lumina-p3-{args.mode}-{now:%Y%m%d%H%M%S}"
    import re
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,62}", name):
        raise ValueError("Nombre de job inválido")
    folder = ROOT / "referencias_locales/dataflow" / name
    folder.mkdir(parents=True, exist_ok=False)
    report_file = folder / "submission.json"
    stop_file = args.stop_file or folder / "stop"
    if stop_file.exists():
        raise ValueError("El archivo de parada ya existe")
    runtime = config["dataflow_runtime"]
    command = [
        sys.executable, "-m", "pipelines.cloud.pipeline_beam", "--mode", args.mode,
        "--project", target["id"], "--region", target["region"],
        "--runner", "DataflowRunner", "--job_name", name,
        "--num_workers", "1", "--max_num_workers", "1", "--autoscaling_algorithm", "NONE",
        "--machine_type", "n1-standard-1" if args.mode == "batch" else "n1-standard-2",
        "--disk_size_gb", "30", "--no_use_public_ips",
        "--service_account_email", runtime["service_account_email"],
        "--subnetwork", runtime["subnetwork"],
        "--staging_location", runtime["staging_location"] + "/" + name,
        "--temp_location", runtime["temp_location"] + "/" + name,
        "--sdk_location", "container", "--setup_file", str(ROOT / "setup.py"),
        "--experiments", "use_runner_v2", "--job-report", str(report_file),
    ]
    if args.mode == "batch":
        command += ["--input", args.input, "--batch-id", name,
                    "--bq-temp-location", runtime["temp_location"] + "/bq/" + name]
    else:
        command += ["--subscription", config["pubsub"]["subscription"],
                    "--node-map", staging["uris"]["puente_stream.jsonl"],
                    "--sensor-catalog", staging["uris"]["catalogo_sensores.jsonl"],
                    "--enable_streaming_engine"]

    token = subprocess.run(["gcloud", "auth", "print-access-token"], check=True,
                           capture_output=True, text=True).stdout.strip()
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + token
    base = f"https://dataflow.googleapis.com/v1b3/projects/{target['id']}/locations/{target['region']}/jobs"

    def request(method, url, **kwargs):
        response = session.request(method, url, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()

    def discover():
        if report_file.exists():
            return json.loads(report_file.read_text())["id"]
        page = request("GET", base, params={"filter": "ALL", "pageSize": 100})
        return next((job["id"] for job in page.get("jobs", []) if job["name"] == name), None)

    def update(job_id, state):
        return request("PUT", f"{base}/{job_id}", json={"requestedState": state})

    def interrupted(signum, frame):
        raise KeyboardInterrupt("Señal de parada")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    started = time.monotonic()
    deadline = started + args.max_minutes * 60
    child = None
    job_id = None
    state = None
    error = None
    stopping = None
    stop_deadline = None
    transitions = []
    exit_seen = None
    print(json.dumps({"name": name, "mode": args.mode, "max_minutes": args.max_minutes,
                      "workers": 1, "stop_file": str(stop_file), "logs": str(folder / "driver.log")}), flush=True)
    try:
        active = request("GET", base, params={"filter": "ACTIVE", "pageSize": 100}).get("jobs", [])
        if active:
            raise RuntimeError("Ya existe un job activo; no se inicia otro para limitar recursos")
        with (folder / "driver.log").open("w") as log:
            child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     env={**os.environ, "PYTHONWARNINGS": "ignore"})
            while True:
                if job_id is None:
                    job_id = discover()
                if job_id:
                    job = request("GET", f"{base}/{job_id}")
                    current = job.get("currentState")
                    if current != state:
                        state = current
                        transitions.append({"state": state, "elapsed_seconds": round(time.monotonic() - started)})
                        print(json.dumps({"job_id": job_id, "state": state}), flush=True)
                    if state in TERMINAL:
                        break
                if child.poll() is not None and job_id is None:
                    if exit_seen is None:
                        exit_seen = time.monotonic()
                    if time.monotonic() - exit_seen >= 60:
                        raise RuntimeError(f"El envío terminó sin ID (exit {child.returncode}); revisar driver.log")
                clock = time.monotonic()
                if clock >= deadline and stopping != "cancel":
                    if job_id:
                        update(job_id, "JOB_STATE_CANCELLED")
                    stopping, stop_deadline = "cancel", clock + 180
                    if child.poll() is None:
                        child.terminate()
                    print("Límite de tiempo: solicitando cancelación.", flush=True)
                elif job_id and args.mode == "stream" and stop_file.exists() and not stopping:
                    update(job_id, "JOB_STATE_DRAINED")
                    stopping, stop_deadline = "drain", clock + 120
                    print("Drain solicitado para completar datos en tránsito.", flush=True)
                if stop_deadline and clock >= stop_deadline:
                    if stopping == "drain":
                        update(job_id, "JOB_STATE_CANCELLED")
                        stopping, stop_deadline = "cancel", clock + 180
                    else:
                        raise TimeoutError("No se confirmó la terminación dentro del plazo")
                if not job_id and clock >= deadline:
                    raise TimeoutError("No se obtuvo ID de job dentro del plazo")
                time.sleep(10)
    except BaseException as problem:
        error = str(problem)
        # El envío puede haber sido aceptado antes de que se escribiera submission.json.
        # Detener primero el emisor y descubrir por nombre evita abandonar ese job.
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
        if job_id is None and child is not None:
            try:
                job_id = discover()
            except Exception as discovery_error:
                error += "; no se pudo verificar envío: " + type(discovery_error).__name__
        if job_id and state not in TERMINAL:
            try:
                update(job_id, "JOB_STATE_CANCELLED")
                for _ in range(18):
                    state = request("GET", f"{base}/{job_id}").get("currentState")
                    if state in TERMINAL:
                        break
                    time.sleep(10)
            except Exception as cleanup_error:
                error += "; no se confirmó cierre: " + type(cleanup_error).__name__
    finally:
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
        result = {"name": name, "job_id": job_id, "mode": args.mode, "batch_id": name if args.mode == "batch" else None,
                  "project": target["id"], "region": target["region"], "final_state": state,
                  "elapsed_seconds": round(time.monotonic() - started), "transitions": transitions,
                  "shutdown_confirmed": state in TERMINAL, "error": error}
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    success = state == "JOB_STATE_DONE" if args.mode == "batch" else state in {"JOB_STATE_DRAINED", "JOB_STATE_CANCELLED"}
    return 0 if success and not error else 1


if __name__ == "__main__":
    raise SystemExit(main())
