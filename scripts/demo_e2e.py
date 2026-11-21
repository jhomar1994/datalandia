"""Demo real Pub/Sub → Dataflow → BigQuery → API. Cierra el job al terminar.

Requiere el proxy autenticado de Cloud Run en localhost:8080, .venv_beam y datos P3.
Los tiempos observados son de esta muestra, no garantías de producción.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import requests
from google.cloud import pubsub_v1

ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8080")
    visible = parser.add_mutually_exclusive_group()
    visible.add_argument("--visible-seconds", type=int, default=0,
                        help="Opcional: hasta 60 s de eventos nuevos para observar el tablero")
    visible.add_argument("--events", type=int, help="Cantidad de eventos nuevos visibles (1..10000)")
    parser.add_argument("--rate", type=float, default=1, help="Eventos nuevos por segundo (0.5..100)")
    args = parser.parse_args(argv)
    if not 0 <= args.visible_seconds <= 60:
        parser.error("visible-seconds debe estar entre cero y sesenta")
    if not 0.5 <= args.rate <= 100:
        parser.error("rate debe estar entre 0.5 y 100")
    if args.events is not None and not 1 <= args.events <= 10000:
        parser.error("events debe estar entre 1 y 10000")
    args.live_events = args.events if args.events is not None else args.visible_seconds
    if args.live_events / args.rate > 120:
        parser.error("La ráfaga debe durar como máximo 120 segundos; reducir events o aumentar rate")
    return args


def main(argv=None):
    args = parse_args(argv)
    base = args.api_url.rstrip("/")
    try:
        health = requests.get(base + "/health", timeout=30)
        health.raise_for_status()
    except requests.RequestException as error:
        raise SystemExit("No se pudo consultar la API. Mantener abierto el proxy: "
                         "gcloud run services proxy lumina-api --project=proyecto-datalandia "
                         "--region=us-central1 --port=8080. No se inició Dataflow.") from None
    if health.json().get("project") != "proyecto-datalandia":
        raise ValueError("La API apunta a otro proyecto")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    name = "lumina-p3-stream-" + stamp
    folder = ROOT / "referencias_locales/demo" / stamp
    folder.mkdir(parents=True)
    stop_file = folder / "stop"
    # Comprobar ADC del publicador antes de crear cómputo en Dataflow.
    publisher = pubsub_v1.PublisherClient()
    topic = publisher.topic_path("proyecto-datalandia", "lumina-eventos")
    controller_log = (folder / "controller.log").open("w")
    process = subprocess.Popen([sys.executable, "scripts/run_dataflow.py", "--mode", "stream",
                                "--name", name, "--max-minutes", "12", "--stop-file", str(stop_file)],
                               cwd=ROOT, stdout=controller_log, stderr=subprocess.STDOUT)
    result = {"name": name, "scenario": "historical replay + synthetic control events", "error": None}
    print(json.dumps({"job_name": name, "logs": str(folder / "controller.log"),
                      "status": "Iniciando un worker privado; el arranque puede tardar varios minutos"}), flush=True)
    started = time.monotonic()
    try:
        counts = Counter()
        historical = []
        for line in (ROOT / "data/p3/input/sensores.jsonl").open():
            event = json.loads(line)
            node = event["node_id"]
            if counts[node] < 20:
                historical.append(event)
                counts[node] += 1
        if len(counts) != 11 or len(historical) != 220:
            raise ValueError("Se esperaban 20 eventos de cada uno de los 11 nodos")
        # Un ID nuevo evita confundir un evento de ayer con el arranque de hoy.
        historical[0] = dict(historical[0], event_id="warmup-p3-" + uuid.uuid4().hex)
        sent = []

        def publish(event):
            event = dict(event, published_at=dt.datetime.now(dt.timezone.utc).isoformat())
            message_id = publisher.publish(topic, json.dumps(event).encode(), event_id=event["event_id"]).result(timeout=30)
            sent.append({"message_id": message_id, "event": event})
            return event

        for event in historical:
            publish(event)
        print("Publicados 220 eventos. Esperando su llegada a la API (máximo siete minutos).", flush=True)
        # Esperar el primer evento válido antes de medir latencia de la ruta caliente.
        probe = historical[0]["event_id"]
        while time.monotonic() - started < 420:
            if process.poll() is not None:
                raise RuntimeError("El controlador terminó antes de recibir datos")
            response = requests.get(base + "/api/events/" + probe, timeout=30)
            if response.status_code == 200:
                print("Primer evento recibido: validando duplicado, conflicto y cuarentena.", flush=True)
                break
            if response.status_code not in (404, 503):
                response.raise_for_status()
            time.sleep(10)
        else:
            raise TimeoutError("El replay no apareció en la API dentro de siete minutos")
        event_id = "demo-p3-" + uuid.uuid4().hex
        control = dict(historical[0], event_id=event_id, value=11.25)
        published = publish(control)
        publish(control)  # Mismo negocio y diferente published_at.
        conflict_id = event_id + "-conflict"
        publish(dict(control, event_id=conflict_id, value=12.25))
        publish(dict(control, event_id=conflict_id, value=13.25))
        publish(dict(control, event_id=event_id + "-invalid", value="error"))
        result.update(event_id=event_id, conflict_id=conflict_id, published_at=published["published_at"],
                      historical_events=220, control_messages=5, nodes=len(counts))
        wait_start = time.monotonic()
        while time.monotonic() - wait_start < 120:
            observed = requests.get(base + "/api/events/" + event_id, timeout=30)
            response_received_at = dt.datetime.now(dt.timezone.utc)
            conflict = requests.get(base + "/api/events/" + conflict_id, timeout=30)
            quality = requests.get(base + "/api/quality", timeout=30)
            if observed.status_code == 200:
                body = observed.json()
                if "first_observed" not in result:
                    result["first_observed"] = body
                    result["response_received_at"] = response_received_at.isoformat()
                    result["availability_seconds"] = round((response_received_at - dt.datetime.fromisoformat(published["published_at"])).total_seconds(), 3)
                quarantined = quality.status_code == 200 and any(
                    x["source"] == "sensor" and x["reason"] == "valor_no_numerico" and x["records"] >= 1
                    for x in quality.json()["reasons"])
                if body["copies_received"] >= 2 and conflict.status_code == 409 and quarantined:
                    # La calidad es global: comprobar además que el rechazo corresponde
                    # al ID de esta ejecución y que Gold conserva el conteo deduplicado.
                    from google.cloud import bigquery
                    sql = """
                    SELECT
                      (SELECT COUNT(*) FROM `proyecto-datalandia.lumina_demo.rechazados`
                       WHERE source='sensor' AND reason='valor_no_numerico'
                       AND JSON_VALUE(raw_payload,'$.event_id')=@invalid_id) invalid_event_rows,
                      (SELECT SUM(lecturas) FROM `proyecto-datalandia.lumina_demo.gold_sensores_5min`) gold_readings,
                      (SELECT COUNT(DISTINCT event_id) FROM `proyecto-datalandia.lumina_demo.sensores_validos`
                       WHERE event_id NOT IN (SELECT event_id FROM `proyecto-datalandia.lumina_demo.conflictos_sensores`)) expected_gold
                    """
                    job = bigquery.Client(project="proyecto-datalandia").query(
                        sql, location="us-central1", job_config=bigquery.QueryJobConfig(
                            maximum_bytes_billed=134217728,
                            query_parameters=[bigquery.ScalarQueryParameter("invalid_id", "STRING", event_id + "-invalid")]))
                    checks = dict(next(iter(job.result(timeout=30))))
                    if not checks["invalid_event_rows"] or checks["gold_readings"] != checks["expected_gold"]:
                        time.sleep(5)
                        continue
                    result["bigquery_checks"] = checks
                    result.update(trace=body, conflict_status=409, quality=quality.json())
                    break
            time.sleep(5)
        else:
            raise TimeoutError("No se observaron todos los controles en dos minutos")
        metrics = requests.get(base + "/api/metrics", timeout=30)
        metrics.raise_for_status()
        result["metrics"] = metrics.json()
        if args.live_events:
            print("Worker listo: publicando eventos nuevos para observar el gráfico y la tarjeta.", flush=True)
            fixture = [json.loads(line) for line in (ROOT / "tests/fixtures/viajes_errores_demo.jsonl").open()]
            burst_start = time.monotonic()
            for i in range(args.live_events):
                publish(dict(control, event_id=event_id + f"-live-{i}", value=10 + i / 10))
                if i < len(fixture):
                    # Datos de viajes en la entrada de sensores: rechazo deliberado de contrato.
                    publish(dict(fixture[i], event_id=event_id + f"-fixture-{i}"))
                time.sleep(max(0, burst_start + (i + 1) / args.rate - time.monotonic()))
            # Esperar visibilidad del último ID de esta ráfaga, sin confundir datos anteriores.
            last_id = event_id + f"-live-{args.live_events - 1}"
            for _ in range(12):
                last = requests.get(base + "/eventos/ultimo", timeout=30)
                chart = requests.get(base + "/eventos/por-minuto?min=15", timeout=30)
                if last.status_code == 200 and last.json().get("event_id") == last_id and chart.status_code == 200:
                    points = chart.json()["minutos"]
                    if len(points) == 15 and any(p["aceptadas"] for p in points) and any(p["rechazadas"] for p in points):
                        result["dashboard_live"] = {"ultimo": last.json(), "por_minuto": chart.json(),
                                                    "new_events": args.live_events, "rate": args.rate,
                                                    "fixture_messages": min(args.live_events, len(fixture))}
                        break
                time.sleep(5)
            else:
                raise TimeoutError("No se confirmó el último evento y barras del tablero nuevo")
        print(json.dumps({"event_id": event_id, "availability_seconds": result["availability_seconds"],
                          "conflict_status": result["conflict_status"]}), flush=True)
    except BaseException as error:
        result["error"] = str(error)
    finally:
        stop_file.touch()
        publisher.stop()
        if "sent" in locals():
            (folder / "published.json").write_text(json.dumps(sent, indent=2) + "\n")
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"report": str(folder / "result.json"), "error": result["error"], "shutdown_requested": True}), flush=True)
        try:
            code = process.wait(timeout=360)
        except subprocess.TimeoutExpired:
            process.terminate()
            code = process.wait(timeout=240)
        controller_log.close()
    if result["error"] or code:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
