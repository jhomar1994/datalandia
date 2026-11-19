"""DataLandia: homologación simulada, batch y replay de sensores.

Ejecutar desde la raíz: .venv_bigdata/bin/python notebooks/02_puentes_batch_streaming.py
Las salidas se guardan en directorios nuevos; no se modifican las fuentes raw.
"""

from pathlib import Path
import csv
import datetime as dt
import json

import duckdb
from pyspark.sql import SparkSession, functions as F, types as T

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SILVER = ROOT / "data" / "silver" / "datalandia_v1"
GOLD = ROOT / "data" / "gold" / "datalandia_v1"
REPLAY = SILVER / "replay_input"
STREAM_OUTPUT = SILVER / "aot_stream_batches"
CHECKPOINT = SILVER / "checkpoint_aot"
SIM_START = dt.datetime(2024, 1, 1, 5, 0, 0)  # Medianoche de Nueva York en UTC.
ORIGINAL_START = dt.datetime(2018, 1, 1, 5, 0, 0)
ORIGINAL_END = dt.datetime(2018, 1, 2, 5, 0, 0)
TIME_SHIFT = SIM_START - ORIGINAL_START


def sql_path(path):
    return str(path).replace("'", "''")


def has_generated_content(path):
    """Ignora el marcador usado por Git al comprobar salidas existentes."""
    return path.exists() and any(item.name != '.gitkeep' for item in path.iterdir())


def build_batch():
    """Agrega cada fuente antes de construir puentes auditables."""
    con = duckdb.connect()
    con.execute("SET threads=4")
    con.execute("SET TimeZone='America/New_York'")
    nyc = sql_path(RAW / "nyc_tlc" / "yellow_tripdata_2024-01.parquet")
    zones = sql_path(RAW / "nyc_tlc" / "taxi_zone_lookup.csv")
    uber = sql_path(RAW / "uber_movement" / "Travel_Times.csv")
    census = sql_path(RAW / "ine" / "Microdato_Censo-Personas.csv")
    nodes = sql_path(RAW / "array_of_things" / "nodes.csv")
    readings = sql_path(RAW / "array_of_things" / "data_sample_1m.csv")

    con.execute(f"""
        CREATE TEMP TABLE zones AS
        SELECT LocationID zone_id, printf('DL-%03d', LocationID) datalandia_zone_id,
               Borough borough, Zone zone_name
        FROM read_csv_auto('{zones}') WHERE LocationID BETWEEN 1 AND 263
    """)
    con.execute(f"""
        CREATE TEMP TABLE trips AS
        SELECT PULocationID zone_id, tpep_pickup_datetime pickup_local,
               trip_distance * 1.609344 distance_km, total_amount amount_usd
        FROM read_parquet('{nyc}')
        WHERE tpep_pickup_datetime >= TIMESTAMP '2024-01-01'
          AND tpep_pickup_datetime < TIMESTAMP '2024-02-01'
          AND tpep_dropoff_datetime > tpep_pickup_datetime
          AND date_diff('second', tpep_pickup_datetime, tpep_dropoff_datetime) <= 14400
          AND trip_distance > 0 AND total_amount > 0
          AND PULocationID BETWEEN 1 AND 263 AND DOLocationID BETWEEN 1 AND 263
    """)
    con.execute("""
        CREATE TEMP TABLE zone_rank AS
        SELECT z.*, coalesce(t.n, 0) trip_count,
               row_number() OVER (ORDER BY coalesce(t.n, 0) DESC, z.zone_id) rank_id
        FROM zones z LEFT JOIN (SELECT zone_id, count(*) n FROM trips GROUP BY 1) t USING (zone_id)
    """)
    con.execute(f"""
        CREATE TEMP TABLE census AS
        SELECT COMUNA comuna, count(*) population,
               count(*) FILTER (WHERE P09 BETWEEN 18 AND 30) young,
               count(*) FILTER (WHERE P09 BETWEEN 65 AND 100) older,
               count(*) FILTER (WHERE AREA = 1) urban
        FROM read_csv('{census}', delim=';', header=true, auto_detect=true, sample_size=100000)
        GROUP BY COMUNA
    """)
    con.execute(f"""
        CREATE TEMP TABLE uber AS
        SELECT "Destination Movement ID" destination_id,
               "Mean Travel Time (Seconds)" mean_seconds,
               "Range - Lower Bound Travel Time (Seconds)" lower_seconds,
               "Range - Upper Bound Travel Time (Seconds)" upper_seconds
        FROM read_csv_auto('{uber}')
    """)
    # Rangos reproducibles: población comunal y demanda NYC; accesibilidad Uber y demanda NYC.
    # Cada comuna/destino tiene exactamente una asignación, sin duplicar conteos.
    con.execute("""
        CREATE TEMP TABLE bridge_batch AS
        SELECT 'nyc_tlc' source_system, 'taxi_zone' source_zone_type,
               cast(zone_id AS VARCHAR) source_id, datalandia_zone_id,
               'identidad_tlc' mapping_method, 1.0::DOUBLE mapping_weight,
               false is_simulated, 'v1' mapping_version FROM zone_rank
        UNION ALL
        SELECT 'ine', 'comuna', cast(comuna AS VARCHAR), z.datalandia_zone_id,
               'rango_poblacion_vs_demanda_nyc', 1.0, true, 'v1'
        FROM (SELECT *, row_number() OVER (ORDER BY population DESC, comuna) rn,
                     count(*) OVER () n FROM census) c
        JOIN zone_rank z ON z.rank_id = 1 + floor((c.rn - 1) * 263.0 / c.n)::INTEGER
        UNION ALL
        SELECT 'uber_movement', 'destination', cast(destination_id AS VARCHAR), z.datalandia_zone_id,
               'rango_accesibilidad_vs_demanda_nyc', 1.0, true, 'v1'
        FROM (SELECT *, row_number() OVER (ORDER BY mean_seconds ASC, destination_id) rn,
                     count(*) OVER () n FROM uber) u
        JOIN zone_rank z ON z.rank_id = 1 + floor((u.rn - 1) * 263.0 / u.n)::INTEGER
    """)
    con.execute(f"""
        CREATE TEMP TABLE bridge_streaming AS
        WITH sample_nodes AS (
            SELECT DISTINCT node_id FROM read_csv_auto('{readings}', all_varchar=true)
        ), ranked AS (
            SELECT s.node_id, n.lat latitude, n.lon longitude,
                   row_number() OVER (ORDER BY s.node_id) rn
            FROM sample_nodes s LEFT JOIN read_csv_auto('{nodes}', all_varchar=true) n USING (node_id)
        )
        SELECT r.node_id, z.datalandia_zone_id, r.latitude, r.longitude,
               'nodo_ordenado_a_zona_mayor_demanda' mapping_method, 'v1' mapping_version,
               true is_simulated, DATE '2024-01-01' valid_from, DATE '2024-01-02' valid_to_exclusive
        FROM ranked r JOIN zone_rank z ON z.rank_id = r.rn
    """)
    con.execute("""
        CREATE TEMP TABLE batch_reference AS
        WITH dem AS (
            SELECT b.datalandia_zone_id, sum(c.population) population_2017,
                   sum(c.young) young_18_30_2017, sum(c.older) older_65_plus_2017,
                   sum(c.urban) urban_population_2017, count(*) communes_assigned
            FROM bridge_batch b JOIN census c ON b.source_system='ine' AND b.source_id=cast(c.comuna AS VARCHAR)
            GROUP BY 1
        ), travel AS (
            SELECT b.datalandia_zone_id, avg(u.mean_seconds) uber_mean_seconds_2017,
                   count(*) uber_destinations_assigned
            FROM bridge_batch b JOIN uber u ON b.source_system='uber_movement' AND b.source_id=cast(u.destination_id AS VARCHAR)
            GROUP BY 1
        )
        SELECT z.datalandia_zone_id, z.zone_id, z.zone_name, z.borough,
               d.population_2017, d.young_18_30_2017, d.older_65_plus_2017,
               d.urban_population_2017, d.communes_assigned,
               t.uber_mean_seconds_2017, t.uber_destinations_assigned
        FROM zones z LEFT JOIN dem d USING (datalandia_zone_id)
                     LEFT JOIN travel t USING (datalandia_zone_id)
    """)
    con.execute("""
        CREATE TEMP TABLE trip_windows AS
        SELECT printf('DL-%03d', zone_id) datalandia_zone_id,
               timezone('America/New_York', time_bucket(INTERVAL '5 minutes', pickup_local)) window_start_utc,
               count(*) trip_count, sum(amount_usd) total_usd, sum(distance_km) total_km,
               sum(amount_usd) / sum(distance_km) taxi_usd_per_km
        FROM trips WHERE pickup_local >= TIMESTAMP '2024-01-01' AND pickup_local < TIMESTAMP '2024-01-02'
        GROUP BY 1,2
    """)
    for name, table in [("dim_datalandia_zone", "zones"), ("bridge_batch", "bridge_batch"),
                        ("bridge_streaming", "bridge_streaming"), ("batch_reference", "batch_reference"),
                        ("nyc_trip_windows", "trip_windows")]:
        con.execute(f"COPY {table} TO '{sql_path(SILVER / (name + '.parquet'))}' (FORMAT PARQUET)")
    print("Puentes:", con.execute("SELECT source_system,count(*) FROM bridge_batch GROUP BY 1 ORDER BY 1").fetchall(),
          "nodos:", con.execute("SELECT count(*) FROM bridge_streaming").fetchone()[0])
    con.close()


def prepare_replay():
    """Crea archivos incrementales de replay en Silver, conservando timestamp UTC original."""
    REPLAY.mkdir(exist_ok=True)
    source = RAW / "array_of_things" / "data_sample_1m.csv"
    writer = None
    output = None
    count = 0
    try:
        with source.open(newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = dt.datetime.strptime(row['timestamp'], '%Y/%m/%d %H:%M:%S')
                if not ORIGINAL_START <= timestamp < ORIGINAL_END:
                    continue
                if count % 100000 == 0:
                    if output:
                        output.close()
                    output = (REPLAY / f"events_{count // 100000:04d}.csv").open('x', newline='', encoding='utf-8')
                    fields = ['event_timestamp_original', 'event_timestamp_simulated', 'node_id',
                              'subsystem', 'sensor', 'parameter', 'value_raw', 'value_hrf']
                    writer = csv.DictWriter(output, fieldnames=fields)
                    writer.writeheader()
                writer.writerow({'event_timestamp_original': timestamp.isoformat(sep=' '),
                                 'event_timestamp_simulated': (timestamp + TIME_SHIFT).isoformat(sep=' '),
                                 **{k: row[k] for k in fields[2:]}})
                count += 1
    finally:
        if output:
            output.close()
    if not count:
        raise RuntimeError('No hay eventos AoT en la ventana seleccionada')
    print(f'Eventos preparados para replay: {count:,}')


def run_stream():
    """Structured Streaming procesa archivos incrementalmente, con checkpoint y ventanas de 5 min."""
    spark = (SparkSession.builder.master('local[2]').appName('DataLandia-AoT-Replay')
             .config('spark.sql.session.timeZone', 'UTC')
             .config('spark.sql.shuffle.partitions', '4').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    schema = T.StructType([T.StructField(name, T.StringType()) for name in [
        'event_timestamp_original', 'event_timestamp_simulated', 'node_id', 'subsystem',
        'sensor', 'parameter', 'value_raw', 'value_hrf']])
    source = (spark.readStream.schema(schema).option('header', True)
              .option('maxFilesPerTrigger', 1).csv(str(REPLAY)))
    bridge = spark.read.parquet(str(SILVER / 'bridge_streaming.parquet'))
    sensor = (spark.read.option('header', True).option('inferSchema', True)
              .csv(str(RAW / 'array_of_things' / 'sensors.csv'))
              .select('subsystem', 'sensor', 'parameter', 'hrf_unit', 'hrf_minval', 'hrf_maxval'))
    outside_range = (F.col('value_numeric').isNotNull() & (
        (F.col('hrf_minval').isNotNull() & (F.col('value_numeric') < F.col('hrf_minval'))) |
        (F.col('hrf_maxval').isNotNull() & (F.col('value_numeric') > F.col('hrf_maxval')))))
    enriched = (source.withColumn('event_timestamp_original', F.to_timestamp('event_timestamp_original'))
                .withColumn('event_timestamp_simulated', F.to_timestamp('event_timestamp_simulated'))
                .withColumn('value_numeric', F.expr('try_cast(value_hrf as double)'))
                .join(F.broadcast(bridge.select('node_id', 'datalandia_zone_id')), 'node_id', 'left')
                .join(F.broadcast(sensor), ['subsystem', 'sensor', 'parameter'], 'left')
                .withColumn('out_of_range', F.when(outside_range, F.lit(True)).otherwise(F.lit(False))))
    # Guardar eventos enriquecidos permite recalcular agregados sin depender del estado de la ventana.
    query = (enriched.writeStream.format('parquet').outputMode('append')
             .option('path', str(STREAM_OUTPUT)).option('checkpointLocation', str(CHECKPOINT))
             .trigger(availableNow=True).start())
    query.awaitTermination()
    spark.stop()
    print('Replay Structured Streaming completado')


def build_gold():
    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")
    stream = sql_path(STREAM_OUTPUT / '*.parquet')
    trips = sql_path(SILVER / 'nyc_trip_windows.parquet')
    reference = sql_path(SILVER / 'batch_reference.parquet')
    con.execute(f"""
        CREATE TEMP TABLE sensors AS
        SELECT datalandia_zone_id, time_bucket(INTERVAL '5 minutes', event_timestamp_simulated) window_start_utc,
               count(*) sensor_observations, count(*) FILTER (WHERE out_of_range) sensor_out_of_range,
               min(event_timestamp_original) first_original_event_utc,
               max(event_timestamp_original) last_original_event_utc
        FROM read_parquet('{stream}')
        WHERE datalandia_zone_id IS NOT NULL GROUP BY 1,2
    """)
    con.execute(f"""
        COPY (
          WITH windows AS (
             SELECT datalandia_zone_id, window_start_utc FROM read_parquet('{trips}')
             UNION SELECT datalandia_zone_id, window_start_utc FROM sensors
          )
          SELECT w.*, r.zone_name, r.borough, t.trip_count, t.total_usd, t.total_km, t.taxi_usd_per_km,
                 s.sensor_observations, s.sensor_out_of_range, s.first_original_event_utc, s.last_original_event_utc,
                 r.population_2017, r.young_18_30_2017, r.older_65_plus_2017,
                 r.uber_mean_seconds_2017, r.uber_destinations_assigned,
                 '2017-09-30/2017-12-31' uber_source_period, 2017 census_source_year,
                 true cross_source_mapping_is_simulated
          FROM windows w LEFT JOIN read_parquet('{trips}') t USING(datalandia_zone_id,window_start_utc)
               LEFT JOIN sensors s USING(datalandia_zone_id,window_start_utc)
               LEFT JOIN read_parquet('{reference}') r USING(datalandia_zone_id)
        ) TO '{sql_path(GOLD / 'zone_5min.parquet')}' (FORMAT PARQUET)
    """)
    print('Gold filas:', con.execute(f"SELECT count(*) FROM read_parquet('{sql_path(GOLD / 'zone_5min.parquet')}')").fetchone()[0])
    con.close()


def main():
    for path in (SILVER, GOLD):
        if has_generated_content(path):
            raise FileExistsError(f'La salida {path} ya existe; usa otra versión para preservarla.')
    SILVER.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)
    metadata = {'simulation_local_date': '2024-01-01', 'local_timezone': 'America/New_York',
                'event_timezone': 'UTC', 'aot_source_start_utc': str(ORIGINAL_START),
                'aot_source_end_exclusive_utc': str(ORIGINAL_END), 'aot_shift_seconds': int(TIME_SHIFT.total_seconds()),
                'uber_source_period': '2017-09-30/2017-12-31', 'census_source_year': 2017,
                'mapping_version': 'v1', 'mapping_is_simulated': True}
    (SILVER / 'run_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    build_batch()
    prepare_replay()
    run_stream()
    build_gold()


if __name__ == '__main__':
    main()
