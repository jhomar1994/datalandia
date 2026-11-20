"""P2 Lumina: batch validado y streaming continuo local (Spark + SQLite).

Comandos: batch, serve, publish, inject, status. Ver docs/ejecucion_local.md.
No se modifican fuentes raw ni resultados v1.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw'
V1 = ROOT / 'data/silver/datalandia_v1'
BASE = ROOT / 'data/p2'
SILVER = BASE / 'silver'
GOLD = BASE / 'gold'
INBOX = BASE / 'stream/input'
CHECKPOINT = BASE / 'stream/checkpoint'
DB = GOLD / 'lumina.sqlite'
SHIFT = dt.timedelta(days=2191)
UTC = dt.timezone.utc


def q(path):
    return str(path).replace("'", "''")


def has_generated_content(path):
    """Ignora el marcador usado por Git al comprobar salidas existentes."""
    return path.exists() and any(item.name != '.gitkeep' for item in path.iterdir())


def parse_utc(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('timestamp_ausente')
    try:
        result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('timestamp_invalido') from exc
    if result.tzinfo is None:
        raise ValueError('timestamp_sin_zona_horaria')
    return result.astimezone(UTC)


def run_batch():
    """Crea una versión inicial inmutable; las referencias originales provienen de v1."""
    output = SILVER / 'batch'
    if has_generated_content(output):
        raise FileExistsError(f'{output} ya existe; consérvalo o usa otra ruta versionada')
    required = ['dim_datalandia_zone.parquet', 'bridge_batch.parquet', 'bridge_streaming.parquet', 'batch_reference.parquet']
    for name in required:
        if not (V1 / name).exists():
            raise FileNotFoundError(f'Falta referencia v1: {V1 / name}')
    output.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET TimeZone='America/New_York'")
    src = q(RAW / 'nyc_tlc/yellow_tripdata_2024-01.parquet')
    con.execute(f"""
    CREATE TEMP TABLE assessed AS
    SELECT *, concat_ws(';',
       CASE WHEN tpep_pickup_datetime IS NULL OR tpep_pickup_datetime < TIMESTAMP '2024-01-01'
                 OR tpep_pickup_datetime >= TIMESTAMP '2024-02-01' THEN 'pickup_fuera_periodo' END,
       CASE WHEN tpep_dropoff_datetime IS NULL OR tpep_dropoff_datetime <= tpep_pickup_datetime
                 OR date_diff('second',tpep_pickup_datetime,tpep_dropoff_datetime) > 14400 THEN 'duracion_invalida' END,
       CASE WHEN trip_distance IS NULL OR NOT isfinite(trip_distance)
                 OR trip_distance < 0.3 OR trip_distance > 120 THEN 'distancia_fuera_limites_millas' END,
       CASE WHEN total_amount IS NULL OR NOT isfinite(total_amount) OR total_amount <= 0 THEN 'importe_invalido' END,
       CASE WHEN PULocationID IS NULL OR PULocationID NOT BETWEEN 1 AND 263 THEN 'origen_no_homologado' END,
       CASE WHEN DOLocationID IS NULL OR DOLocationID NOT BETWEEN 1 AND 263 THEN 'destino_no_homologado' END
    ) rejection_reason FROM read_parquet('{src}')
    """)
    con.execute(f"COPY (SELECT * FROM assessed WHERE rejection_reason <> '') TO '{q(output / 'nyc_rejected.parquet')}' (FORMAT PARQUET)")
    con.execute(f"""
    COPY (SELECT *,trip_distance*1.609344 distance_km,
                 date_diff('second',tpep_pickup_datetime,tpep_dropoff_datetime)/60.0 duration_min
          FROM assessed WHERE rejection_reason = '') TO '{q(output / 'nyc_valid.parquet')}' (FORMAT PARQUET)
    """)
    con.execute(f"""
    COPY (SELECT printf('DL-%03d',PULocationID) datalandia_zone_id,
                 epoch(timezone('America/New_York',time_bucket(INTERVAL '5 minutes',tpep_pickup_datetime)))::BIGINT window_start_epoch,
                 count(*) trip_count, sum(total_amount) total_usd, sum(distance_km) total_km,
                 sum(total_amount)/sum(distance_km) taxi_usd_per_km, avg(duration_min) avg_duration_min
          FROM read_parquet('{q(output / 'nyc_valid.parquet')}')
          WHERE tpep_pickup_datetime >= TIMESTAMP '2024-01-01' AND tpep_pickup_datetime < TIMESTAMP '2024-01-02'
          GROUP BY 1,2) TO '{q(output / 'fact_mobility_5min.parquet')}' (FORMAT PARQUET)
    """)
    counts = con.execute("SELECT count(*),count(*) FILTER(WHERE rejection_reason=''),count(*) FILTER(WHERE rejection_reason<>'') FROM assessed").fetchone()
    metrics = {'received': counts[0], 'valid': counts[1], 'rejected': counts[2],
               'source': 'yellow_tripdata_2024-01.parquet', 'rules_version': 'p2_v1',
               'gold_local_date': '2024-01-01', 'local_timezone': 'America/New_York',
               'distance_miles_min': 0.3, 'distance_miles_max': 120,
               'max_duration_seconds': 14400}
    (output / 'batch_metrics.json').write_text(json.dumps(metrics, indent=2)+'\n', encoding='utf-8')
    con.close()
    initialize_db()
    print(json.dumps(metrics, ensure_ascii=False))


def initialize_db():
    GOLD.mkdir(parents=True, exist_ok=True)
    batch_file = SILVER / 'batch/fact_mobility_5min.parquet'
    if not batch_file.exists():
        raise FileNotFoundError('Ejecuta primero el comando batch')
    con = sqlite3.connect(DB)
    con.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS mobility_5min(zone_id TEXT, window_start_epoch INTEGER,
      trip_count INTEGER, total_usd REAL, total_km REAL, taxi_usd_per_km REAL, avg_duration_min REAL,
      PRIMARY KEY(zone_id,window_start_epoch));
    CREATE TABLE IF NOT EXISTS dim_zone(zone_id TEXT PRIMARY KEY, nyc_zone_id INTEGER, zone_name TEXT,
      borough TEXT, population_2017 INTEGER, young_18_30_2017 INTEGER, older_65_plus_2017 INTEGER,
      uber_mean_seconds_2017 REAL, uber_destinations_assigned INTEGER);
    CREATE TABLE IF NOT EXISTS sensor_observation(event_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
      node_id TEXT NOT NULL, zone_id TEXT NOT NULL, subsystem TEXT NOT NULL, sensor TEXT NOT NULL,
      parameter TEXT NOT NULL, unit TEXT NOT NULL, original_ts TEXT NOT NULL, simulated_ts TEXT NOT NULL,
      window_start_epoch INTEGER NOT NULL, value REAL NOT NULL, out_of_range INTEGER, received_at_utc TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS rejected_events(id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id INTEGER,
      event_id TEXT, reason TEXT NOT NULL, raw_payload TEXT NOT NULL, rejected_at_utc TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS processed_batches(batch_id INTEGER PRIMARY KEY, received INTEGER NOT NULL,
      accepted INTEGER NOT NULL, rejected INTEGER NOT NULL, committed_at_utc TEXT NOT NULL);
    CREATE VIEW IF NOT EXISTS fact_sensor_5min AS
      SELECT zone_id, window_start_epoch, node_id, subsystem, sensor, parameter, unit,
        count(*) observation_count, avg(value) avg_value, min(value) min_value, max(value) max_value,
        sum(CASE WHEN out_of_range=1 THEN 1 ELSE 0 END) outside_range_count,
        sum(CASE WHEN out_of_range IS NOT NULL THEN 1 ELSE 0 END) assessed_count
      FROM sensor_observation GROUP BY zone_id,window_start_epoch,node_id,subsystem,sensor,parameter,unit;
    CREATE VIEW IF NOT EXISTS gold_zone_sensor_5min AS
      SELECT s.*, m.trip_count, m.total_usd, m.total_km, m.taxi_usd_per_km, m.avg_duration_min
      FROM fact_sensor_5min s LEFT JOIN mobility_5min m
        ON s.zone_id=m.zone_id AND s.window_start_epoch=m.window_start_epoch;
    CREATE VIEW IF NOT EXISTS gold_zone_context_5min AS
      SELECT g.*, z.zone_name, z.borough, z.population_2017, z.young_18_30_2017,
        z.older_65_plus_2017, z.uber_mean_seconds_2017, z.uber_destinations_assigned
      FROM gold_zone_sensor_5min g LEFT JOIN dim_zone z ON g.zone_id=z.zone_id;
    ''')
    if con.execute('SELECT count(*) FROM mobility_5min').fetchone()[0] == 0:
        duck = duckdb.connect()
        rows = duck.execute(f"SELECT * FROM read_parquet('{q(batch_file)}')").fetchall()
        con.executemany('INSERT INTO mobility_5min VALUES (?,?,?,?,?,?,?)', rows)
        duck.close()
    if con.execute('SELECT count(*) FROM dim_zone').fetchone()[0] == 0:
        duck = duckdb.connect()
        rows = duck.execute(f"""SELECT datalandia_zone_id,zone_id,zone_name,borough,population_2017,
             young_18_30_2017,older_65_plus_2017,uber_mean_seconds_2017,uber_destinations_assigned
             FROM read_parquet('{q(V1 / 'batch_reference.parquet')}')""").fetchall()
        con.executemany('INSERT INTO dim_zone VALUES (?,?,?,?,?,?,?,?,?)', rows)
        duck.close()
    con.commit()
    con.close()


def catalog():
    d = duckdb.connect()
    nodes = dict(d.execute(f"SELECT node_id,datalandia_zone_id FROM read_parquet('{q(V1 / 'bridge_streaming.parquet')}')").fetchall())
    rows = d.execute(f"""SELECT subsystem,sensor,parameter,hrf_unit,hrf_minval,hrf_maxval
        FROM read_csv_auto('{q(RAW / 'array_of_things/sensors.csv')}', all_varchar=true)""").fetchall()
    sensors = {}
    for subsystem, sensor, parameter, unit, lower, upper in rows:
        key = (subsystem, sensor, parameter)
        if key in sensors:
            raise ValueError(f'Catálogo de sensores no único: {key}')
        def number(x):
            try:
                return float(x) if x not in (None, '', 'NA') else None
            except ValueError:
                return None
        sensors[key] = (unit, number(lower), number(upper))
    d.close()
    return nodes, sensors


def write_batch(batch, batch_id):
    """Commit transaccional por microbatch; SQLite es un destino local de demostración."""
    nodes, sensors = catalog()
    con = sqlite3.connect(DB, timeout=30)
    now = dt.datetime.now(UTC).isoformat()
    received = accepted = rejected = 0
    try:
        con.execute('BEGIN IMMEDIATE')
        if con.execute('SELECT 1 FROM processed_batches WHERE batch_id=?', (batch_id,)).fetchone():
            con.rollback()
            return
        for row in batch.toLocalIterator():
            received += 1
            raw = row['value']
            event_id = None
            try:
                e = json.loads(raw)
                if not isinstance(e, dict):
                    raise ValueError('json_no_es_objeto')
                event_id = e.get('event_id')
                if not isinstance(event_id, str) or not event_id.strip():
                    raise ValueError('event_id_ausente')
                node = e.get('node_id')
                if node not in nodes:
                    raise ValueError('nodo_no_homologado')
                key = tuple(e.get(k) for k in ('subsystem', 'sensor', 'parameter'))
                if key not in sensors:
                    raise ValueError('sensor_no_catalogado')
                unit, low, high = sensors[key]
                if not unit or unit == 'id':
                    raise ValueError('metrica_no_numerica')
                original = parse_utc(e.get('event_timestamp_original'))
                simulated = parse_utc(e.get('event_timestamp_simulado'))
                if simulated - original != SHIFT:
                    raise ValueError('desplazamiento_temporal_invalido')
                if not dt.datetime(2024,1,1,5,tzinfo=UTC) <= simulated < dt.datetime(2024,1,2,5,tzinfo=UTC):
                    raise ValueError('evento_fuera_ventana_simulada')
                try:
                    value = float(e.get('value'))
                except (TypeError, ValueError) as exc:
                    raise ValueError('valor_no_numerico') from exc
                if not math.isfinite(value):
                    raise ValueError('valor_no_finito')
                if e.get('unit') != unit:
                    raise ValueError('unidad_no_coincide_catalogo')
                payload_hash = hashlib.sha256(json.dumps(e, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
                previous = con.execute('SELECT payload_hash FROM sensor_observation WHERE event_id=?', (event_id,)).fetchone()
                if previous:
                    raise ValueError('duplicado' if previous[0] == payload_hash else 'event_id_conflictivo')
                outside = None if low is None and high is None else int((low is not None and value < low) or (high is not None and value > high))
                epoch = int(simulated.timestamp())
                con.execute('INSERT INTO sensor_observation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (event_id, payload_hash, node, nodes[node], *key, unit, original.isoformat(), simulated.isoformat(),
                     epoch - epoch % 300, value, outside, now))
                accepted += 1
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                reason = 'json_invalido' if isinstance(exc, json.JSONDecodeError) else str(exc)
                con.execute('INSERT INTO rejected_events(batch_id,event_id,reason,raw_payload,rejected_at_utc) VALUES(?,?,?,?,?)',
                            (batch_id, event_id, reason, raw, now))
                rejected += 1
        con.execute('INSERT INTO processed_batches VALUES(?,?,?,?,?)', (batch_id, received, accepted, rejected, now))
        con.commit()
        print(f'microbatch={batch_id} recibidos={received} aceptados={accepted} rechazados={rejected}', flush=True)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def serve():
    initialize_db()
    INBOX.mkdir(parents=True, exist_ok=True)
    from pyspark.sql import SparkSession
    spark = (SparkSession.builder.master('local[2]').appName('Lumina-P2-Streaming')
             .config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','2').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    stream = spark.readStream.option('maxFilesPerTrigger',1).text(str(INBOX))
    query = (stream.writeStream.foreachBatch(write_batch).option('checkpointLocation',str(CHECKPOINT))
             .trigger(processingTime='5 seconds').start())
    print('Streaming activo. Publica archivos JSONL con publish o inject. Ctrl+C para detener.', flush=True)
    try:
        query.awaitTermination()
    except KeyboardInterrupt:
        query.stop()
    finally:
        spark.stop()


def atomic_publish(events):
    INBOX.mkdir(parents=True, exist_ok=True)
    # El temporal está fuera del directorio observado para evitar lecturas parciales.
    parent = INBOX.parent
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=parent, prefix='.pending_', delete=False) as f:
        tmp = Path(f.name)
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False, separators=(',', ':'))+'\n')
    dest = INBOX / (tmp.name.removeprefix('.pending_') + '.jsonl')
    os.replace(tmp, dest)
    return dest


def source_event(row, sensors):
    original = dt.datetime.strptime(row['timestamp'], '%Y/%m/%d %H:%M:%S').replace(tzinfo=UTC)
    if not dt.datetime(2018,1,1,5,tzinfo=UTC) <= original < dt.datetime(2018,1,2,5,tzinfo=UTC):
        return None
    key = (row['subsystem'],row['sensor'],row['parameter'])
    unit = sensors.get(key, (None,None,None))[0]
    content = {k: row[k] for k in ('timestamp','node_id','subsystem','sensor','parameter','value_raw','value_hrf')}
    return {'event_id': hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest(),
            'event_timestamp_original':original.isoformat(), 'event_timestamp_simulado':(original+SHIFT).isoformat(),
            'node_id':row['node_id'], 'subsystem':key[0], 'sensor':key[1], 'parameter':key[2],
            'value':row['value_hrf'], 'unit':unit}


def publish(limit, chunk_size, delay):
    _, sensors = catalog()
    events = []
    sent = 0
    with (RAW / 'array_of_things/data_sample_1m.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            event = source_event(row, sensors)
            if event is None:
                continue
            events.append(event)
            sent += 1
            if len(events) >= chunk_size:
                print(f'Publicado {atomic_publish(events)} ({len(events)} eventos)',flush=True)
                events = []
                if delay:
                    time.sleep(delay)
            if sent >= limit:
                break
    if events:
        print(f'Publicado {atomic_publish(events)} ({len(events)} eventos)',flush=True)
    print(f'Publicados: {sent}')


def inject():
    """Publica datos inválidos reproducibles y un evento válido para comprobar actualización."""
    nodes, sensors = catalog()
    node = sorted(nodes)[0]
    unit = sensors[('metsense','htu21d','temperature')][0]
    e = {'event_id': 'demo-valid-001', 'event_timestamp_original':'2018-01-01T05:00:00+00:00',
         'event_timestamp_simulado':'2024-01-01T05:00:00+00:00', 'node_id':node,
         'subsystem':'metsense','sensor':'htu21d','parameter':'temperature','value':'10.0','unit':unit}
    bad_node = dict(e, event_id='demo-bad-node-001', node_id='nodo-inexistente')
    bad_value = dict(e, event_id='demo-bad-value-001', value='error')
    bad_time = dict(e, event_id='demo-bad-time-001', event_timestamp_simulado='sin-fecha')
    print('Archivo publicado:',atomic_publish([e, bad_node, bad_value, bad_time, e]))


def status():
    if not DB.exists():
        raise FileNotFoundError('Primero ejecuta batch')
    con = sqlite3.connect(DB)
    for label, sql in [
        ('microbatches', 'SELECT count(*),coalesce(sum(received),0),coalesce(sum(accepted),0),coalesce(sum(rejected),0) FROM processed_batches'),
        ('rechazos', 'SELECT reason,count(*) FROM rejected_events GROUP BY reason ORDER BY count(*) DESC'),
        ('ultimas_ventanas', "SELECT zone_id,datetime(window_start_epoch,'unixepoch') AS utc,sensor,parameter,unit,observation_count,round(avg_value,2) FROM fact_sensor_5min ORDER BY window_start_epoch DESC LIMIT 10")]:
        print(label, con.execute(sql).fetchall())
    con.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('batch'); sub.add_parser('serve'); sub.add_parser('inject'); sub.add_parser('status')
    p=sub.add_parser('publish')
    p.add_argument('--limit',type=int,default=1000); p.add_argument('--chunk-size',type=int,default=250); p.add_argument('--delay',type=float,default=1)
    args=parser.parse_args()
    if args.command=='batch': run_batch()
    elif args.command=='serve': serve()
    elif args.command=='inject': inject()
    elif args.command=='status': status()
    elif args.command=='publish':
        if args.limit <= 0 or args.chunk_size <= 0 or args.delay < 0: parser.error('limit y chunk-size deben ser positivos; delay debe ser no negativo')
        publish(args.limit,args.chunk_size,args.delay)


if __name__=='__main__':
    main()
