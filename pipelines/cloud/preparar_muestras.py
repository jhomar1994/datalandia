"""Prepara entradas P3 sin modificar las fuentes ni la muestra histórica P2."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]


def sqlpath(path):
    return str(path).replace("'", "''")


def seal_manifest(output, manifest):
    manifest = dict(manifest)
    manifest.pop("bundle_id", None)
    artifacts = {}
    for name in ("viajes", "sensores", "puente_batch", "puente_stream", "referencia_zona", "catalogo_sensores"):
        path = output / (name + ".jsonl")
        with path.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        artifacts[path.name] = {"sha256": checksum, "bytes": path.stat().st_size}
    manifest["artifacts"] = artifacts
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest["bundle_id"] = hashlib.sha256(encoded).hexdigest()
    return manifest


def prepare(output, trip_limit=100000, sensor_limit=11000):
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"No se sobrescribe {output}; usa otra carpeta")
    if trip_limit < 0 or sensor_limit < 0:
        raise ValueError("Los límites deben ser cero (sin límite) o positivos")
    raw = ROOT / "data/raw"
    silver = ROOT / "data/silver/datalandia_v1"
    source = raw / "nyc_tlc/yellow_tripdata_2024-01.parquet"
    with source.open("rb") as handle:
        source_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    c = duckdb.connect()
    c.execute("SET TimeZone='UTC'")
    output.mkdir(parents=True, exist_ok=True)
    counts = {}

    def export(name, query):
        path = output / (name + ".jsonl")
        c.execute(f"COPY ({query}) TO '{sqlpath(path)}' (FORMAT JSON, ARRAY false)")
        counts[name] = c.execute(f"SELECT count(*) FROM read_json_auto('{sqlpath(path)}')").fetchone()[0]

    limit = f"LIMIT {trip_limit}" if trip_limit else ""
    trips = sqlpath(source)
    # file_row_number conserva viajes distintos aunque tengan los mismos valores.
    export("viajes", f"""
        WITH source AS (
          SELECT *, row_number() OVER (PARTITION BY PULocationID ORDER BY file_row_number) zone_rank
          FROM read_parquet('{trips}', file_row_number=true)
        )
        SELECT sha256(concat_ws('|','{source_hash}',cast(file_row_number AS VARCHAR))) trip_id,
          PULocationID origin_id,DOLocationID destination_id,
          cast(tpep_pickup_datetime AS VARCHAR) pickup_local,
          cast(tpep_dropoff_datetime AS VARCHAR) dropoff_local,
          trip_distance distance_miles,total_amount total_usd
        FROM source ORDER BY zone_rank,PULocationID NULLS LAST,file_row_number {limit}
    """)
    limit = f"LIMIT {sensor_limit}" if sensor_limit else ""
    stream = sqlpath(silver / "aot_stream_batches/*.parquet")
    export("sensores", f"""
        WITH source AS (
          SELECT *, row_number() OVER (
            PARTITION BY datalandia_zone_id ORDER BY event_timestamp_simulated,node_id,subsystem,sensor,parameter
          ) zone_rank FROM read_parquet('{stream}')
        )
        SELECT sha256(concat_ws('|',node_id,subsystem,sensor,parameter,
          cast(event_timestamp_original AS VARCHAR),cast(value_raw AS VARCHAR),cast(value_hrf AS VARCHAR))) event_id,
          node_id,subsystem,sensor,parameter,hrf_unit unit,cast(value_hrf AS VARCHAR) value,
          strftime(event_timestamp_original,'%Y-%m-%dT%H:%M:%SZ') original_ts,
          strftime(event_timestamp_simulated,'%Y-%m-%dT%H:%M:%SZ') event_ts
        FROM source ORDER BY zone_rank,datalandia_zone_id,subsystem,sensor,parameter {limit}
    """)
    for name, filename in [
        ("puente_batch", "bridge_batch.parquet"),
        ("puente_stream", "bridge_streaming.parquet"),
        ("referencia_zona", "batch_reference.parquet"),
    ]:
        export(name, f"SELECT * FROM read_parquet('{sqlpath(silver / filename)}')")
    export("catalogo_sensores", f"""
        SELECT subsystem,sensor,parameter,hrf_unit unit,
          CASE WHEN isfinite(try_cast(hrf_minval AS DOUBLE)) THEN try_cast(hrf_minval AS DOUBLE) END min_value,
          CASE WHEN isfinite(try_cast(hrf_maxval AS DOUBLE)) THEN try_cast(hrf_maxval AS DOUBLE) END max_value
        FROM read_csv_auto('{sqlpath(raw / 'array_of_things/sensors.csv')}',all_varchar=true)
    """)
    coverage = {
        "trip_origin_zones": c.execute(f"SELECT count(DISTINCT origin_id) FROM read_json_auto('{sqlpath(output / 'viajes.jsonl')}')").fetchone()[0],
        "sensor_nodes": c.execute(f"SELECT count(DISTINCT node_id) FROM read_json_auto('{sqlpath(output / 'sensores.jsonl')}')").fetchone()[0],
        "sensor_zones": c.execute(f"SELECT count(DISTINCT datalandia_zone_id) FROM read_json_auto('{sqlpath(output / 'puente_stream.jsonl')}')").fetchone()[0],
    }
    manifest = {
        "source_trip_file": source.name, "source_trip_sha256": source_hash,
        "trip_id_strategy": "sha256(source_file_sha256|parquet_file_row_number)",
        "trip_limit": trip_limit, "sensor_limit": sensor_limit, "counts": counts, "coverage": coverage,
        "homologacion_simulada": True, "trip_period": ["2024-01-01", "2024-02-01"],
        "sensor_simulated_period_utc": ["2024-01-01T05:00:00Z", "2024-01-02T05:00:00Z"],
        "shift_days": 2191,
        "note": "Viajes sin prevalidación; selección por zona. Censo y Uber se conservan como referencias agregadas históricas.",
    }
    manifest = seal_manifest(output, manifest)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    c.close()
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/p3/input")
    parser.add_argument("--trip-limit", type=int, default=100000, help="0 procesa el archivo completo")
    parser.add_argument("--sensor-limit", type=int, default=11000, help="0 selecciona todo el replay")
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.trip_limit, args.sensor_limit), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
