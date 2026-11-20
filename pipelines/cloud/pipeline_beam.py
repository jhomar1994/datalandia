"""Beam batch y streaming: configuración explícita, catálogos y cuarentena."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import sys
from importlib.resources import files
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import apache_beam as beam
from apache_beam.io.filesystems import FileSystems
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions, StandardOptions

from pipelines.cloud.validaciones import (
    InvalidEvent, UTC, reject, timestamp, validate_sensor, validate_trip,
)

DEFAULT_PROJECT = "proyecto-datalandia"


def schema(name):
    return {"fields": json.loads(files("schemas").joinpath(f"bigquery/{name}.json").read_text())}


def read_jsonl(path):
    with FileSystems.open(path) as source:
        return [json.loads(line) for line in source if line.strip()]


def load_catalogs(node_path, sensor_path):
    nodes = {}
    for row in read_jsonl(node_path):
        node = row["node_id"]
        if node in nodes:
            raise ValueError(f"Nodo con más de una asociación: {node}")
        nodes[node] = row["datalandia_zone_id"]
    sensors = {}
    for row in read_jsonl(sensor_path):
        key = tuple(row[k] for k in ("subsystem", "sensor", "parameter"))
        if key in sensors:
            raise ValueError(f"Sensor duplicado en catálogo: {key}")
        sensors[key] = row
    if not nodes or not sensors:
        raise ValueError("Los catálogos no pueden estar vacíos")
    return nodes, sensors


class ValidateTrip(beam.DoFn):
    def __init__(self, batch_id, start_date, end_date):
        self.batch_id, self.start_date, self.end_date = batch_id, start_date, end_date

    def process(self, raw):
        try:
            result = validate_trip(raw, self.start_date, self.end_date)
            result.update(batch_id=self.batch_id, processed_at=dt.datetime.now(UTC).isoformat())
            yield result
        except InvalidEvent as error:
            yield beam.pvalue.TaggedOutput("invalid", reject("viaje", error, raw, self.batch_id))


class ValidateSensor(beam.DoFn):
    def __init__(self, nodes, sensors, start, end, shift_days):
        self.nodes, self.sensors = nodes, sensors
        self.start, self.end, self.shift_days = start, end, shift_days

    def process(self, message):
        raw = message if isinstance(message, str) else message.data.decode("utf-8", errors="replace")
        try:
            result = validate_sensor(raw, self.nodes, self.sensors, self.start, self.end, self.shift_days)
            result["processed_at"] = dt.datetime.now(UTC).isoformat()
            yield result
        except InvalidEvent as error:
            yield beam.pvalue.TaggedOutput("invalid", reject("sensor", error, raw))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["batch", "stream"], required=True)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--dataset", default="lumina_demo")
    parser.add_argument("--input")
    parser.add_argument("--subscription")
    parser.add_argument("--batch-id")
    parser.add_argument("--node-map")
    parser.add_argument("--sensor-catalog")
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default="2024-02-01")
    parser.add_argument("--event-start", default="2024-01-01T05:00:00Z")
    parser.add_argument("--event-end", default="2024-01-02T05:00:00Z")
    parser.add_argument("--shift-days", type=int, default=2191)
    parser.add_argument("--bq-temp-location")
    parser.add_argument("--job-report", type=Path, help="Guarda el ID devuelto por Dataflow, sin credenciales")
    parser.add_argument("--local-output", help="Salida local para validar sin escribir en GCP.")
    parser.add_argument("--local-input", help="JSONL de replay; en stream evita leer Pub/Sub.")
    args, extra = parser.parse_known_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", args.project):
        parser.error("Project ID inválido")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.dataset):
        parser.error("Dataset inválido")
    if args.mode == "batch":
        if not args.input or not args.batch_id:
            parser.error("batch requiere --input y --batch-id")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.batch_id):
            parser.error("batch-id inválido")
        if dt.date.fromisoformat(args.start_date) >= dt.date.fromisoformat(args.end_date):
            parser.error("start-date debe ser anterior a end-date")
        if not args.local_output and not args.bq_temp_location:
            parser.error("batch BigQuery requiere --bq-temp-location")
    elif not args.node_map or not args.sensor_catalog or not (args.subscription or args.local_input):
        parser.error("stream requiere catálogos y --subscription o --local-input")
    if args.local_input and not args.local_output:
        parser.error("--local-input requiere --local-output para evitar confundir replay con ingesta cloud")

    options = PipelineOptions(extra, project=args.project, region=args.region)
    if args.local_output and options.view_as(StandardOptions).runner not in (None, "DirectRunner"):
        parser.error("La validación local debe usar DirectRunner")
    if not args.local_output and options.view_as(StandardOptions).runner != "DataflowRunner":
        parser.error("La escritura cloud requiere --runner DataflowRunner; para validar usa --local-output")
    options.view_as(StandardOptions).streaming = args.mode == "stream" and not args.local_input
    options.view_as(SetupOptions).save_main_session = True
    pipeline = beam.Pipeline(options=options)
    if args.mode == "batch":
        result = (
            pipeline
            | "ReadTrips" >> beam.io.ReadFromText(args.input)
            | "ValidateTrips" >> beam.ParDo(ValidateTrip(args.batch_id, args.start_date, args.end_date))
                .with_outputs("invalid", main="valid")
        )
        table = "viajes_staging"
    else:
        nodes, sensors = load_catalogs(args.node_map, args.sensor_catalog)
        start = timestamp(args.event_start, "event_start", aware=True)
        end = timestamp(args.event_end, "event_end", aware=True)
        if start >= end:
            parser.error("event-start debe ser anterior a event-end")
        source = (
            beam.io.ReadFromText(args.local_input) if args.local_input else
            beam.io.ReadFromPubSub(subscription=args.subscription, with_attributes=True)
        )
        result = (
            pipeline | "ReadSensors" >> source
            | "ValidateSensors" >> beam.ParDo(ValidateSensor(nodes, sensors, start, end, args.shift_days))
                .with_outputs("invalid", main="valid")
        )
        table = "sensores_validos"
    for collection, name in [(result.valid, table), (result.invalid, "rechazados_raw")]:
        if args.local_output:
            collection | "JSON_" + name >> beam.Map(json.dumps) | "Local_" + name >> beam.io.WriteToText(
                str(Path(args.local_output) / name), file_name_suffix=".jsonl", num_shards=1)
        else:
            method = (
                beam.io.WriteToBigQuery.Method.FILE_LOADS if args.mode == "batch"
                else beam.io.WriteToBigQuery.Method.STREAMING_INSERTS
            )
            kwargs = {"custom_gcs_temp_location": args.bq_temp_location} if args.mode == "batch" else {}
            collection | "BQ_" + name >> beam.io.WriteToBigQuery(
                f"{args.project}:{args.dataset}.{name}", schema=schema(name), method=method,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND, **kwargs)
    running = pipeline.run()
    if args.job_report and not args.local_output:
        args.job_report.parent.mkdir(parents=True, exist_ok=True)
        args.job_report.write_text(json.dumps({
            "id": running.job_id(), "project": args.project, "region": args.region,
            "mode": args.mode, "batch_id": args.batch_id,
        }, indent=2) + "\n")
    if args.mode == "batch" or args.local_output:
        running.wait_until_finish()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
