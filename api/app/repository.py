"""Consultas predefinidas con parámetros y límite de procesamiento por job."""
import datetime as dt
import json
import logging
import threading
import time

from .settings import Settings


class DataUnavailable(RuntimeError):
    pass


class BigQueryRepository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._cache = {}
        self._lock = threading.Lock()

    def table(self, name):
        return f"`{self.settings.project}.{self.settings.dataset}.{name}`"

    def query(self, sql, parameters=()):
        from google.cloud import bigquery
        with self._lock:
            if self._client is None:
                self._client = bigquery.Client(project=self.settings.project)
        config = bigquery.QueryJobConfig(
            query_parameters=list(parameters), maximum_bytes_billed=self.settings.max_bytes_billed,
            use_query_cache=True,
        )
        job = None
        try:
            job = self._client.query(sql, location=self.settings.region, job_config=config)
            return [dict(row) for row in job.result(timeout=15)]
        except Exception as error:
            if isinstance(error, TimeoutError) and job:
                try:
                    job.cancel()
                except Exception:
                    pass
            logging.error("BigQuery query failed: %s; job=%s", type(error).__name__, getattr(job, "job_id", None))
            raise DataUnavailable("Los indicadores no están disponibles temporalmente") from error

    def cached(self, key, seconds, fetch):
        with self._lock:
            cached = self._cache.get(key)
            if cached and time.monotonic() < cached[0]:
                return cached[1]
        result = fetch()
        with self._lock:
            if len(self._cache) > 100:
                self._cache.clear()
            self._cache[key] = (time.monotonic() + seconds, result)
        return result

    def zones(self):
        return self.cached("zones", 3600, lambda: self.query(
            f"SELECT datalandia_zone_id zone_id,zone_name,borough,population_2017 FROM {self.table('referencia_zona')} ORDER BY zone_id"))

    def dashboard_batch(self):
        def fetch():
            rows = self.query(f"""SELECT batch_id,state estado,expected_records entradas,
                accepted validos,rejected rechazados,zones zonas,consolidated consolidado,
                workers_requested workers_solicitados,started_at iniciado,updated_at actualizado,
                dataflow_job_id FROM {self.table('batch_ejecuciones')}
                ORDER BY started_at DESC,batch_id DESC LIMIT 1""")
            return rows[0] if rows else {}
        return self.cached("batch_latest", self.settings.cache_ttl, fetch)

    def metrics(self, zone, start, end, limit):
        from google.cloud import bigquery
        def fetch():
            condition = "zone_id=@zone AND window_start_utc>=@start AND window_start_utc<@end"
            sql = f"""
WITH mobility AS (
  SELECT * FROM {self.table('gold_movilidad_5min')} WHERE {condition}
), sensors AS (
  SELECT * FROM {self.table('gold_sensores_5min')} WHERE {condition}
)
SELECT
  TO_JSON_STRING((SELECT AS STRUCT COALESCE(SUM(viajes),0) trips,
    COALESCE(SUM(total_usd),0) total_usd, COALESCE(SUM(total_km),0) total_km,
    SAFE_DIVIDE(SUM(total_usd),SUM(total_km)) usd_per_km FROM mobility)) mobility_json,
  ARRAY(SELECT TO_JSON_STRING(x) FROM (SELECT window_start_utc,viajes trips FROM mobility ORDER BY window_start_utc LIMIT 288) x) mobility_series,
  TO_JSON_STRING((SELECT AS STRUCT COALESCE(SUM(lecturas),0) readings,
    COALESCE(SUM(lecturas_fuera_rango),0) outside_range,COUNT(*) metric_windows FROM sensors)) sensor_summary_json,
  ARRAY(SELECT TO_JSON_STRING(x) FROM (SELECT * FROM sensors ORDER BY window_start_utc DESC,sensor,parameter LIMIT @limit) x) sensors_json,
  (SELECT MAX(processed_at) FROM {self.table('sensores_validos')}
    WHERE zone_id=@zone AND event_ts>=@start AND event_ts<@end) latest_received_at
"""
            params = [bigquery.ScalarQueryParameter("zone", "STRING", zone),
                      bigquery.ScalarQueryParameter("start", "TIMESTAMP", start),
                      bigquery.ScalarQueryParameter("end", "TIMESTAMP", end),
                      bigquery.ScalarQueryParameter("limit", "INT64", limit)]
            row = self.query(sql, params)[0]
            return {
                "zone_id": zone, "start": start, "end": end,
                "mobility": json.loads(row["mobility_json"]),
                "mobility_series": [json.loads(x) for x in row["mobility_series"]],
                "sensor_summary": json.loads(row["sensor_summary_json"]),
                "sensors": [json.loads(x) for x in row["sensors_json"]],
                "latest_received_at": row["latest_received_at"],
                "queried_at": dt.datetime.now(dt.timezone.utc),
                "simulation": True, "historical_reference_year": 2017,
            }
        return self.cached((zone, start.isoformat(), end.isoformat(), limit), 2, fetch)

    def quality(self):
        def fetch():
            sql = f"""
SELECT ARRAY(SELECT TO_JSON_STRING(x) FROM (
  SELECT source,reason,COUNT(*) records FROM {self.table('rechazados')} GROUP BY source,reason ORDER BY records DESC
) x) reasons,
(SELECT COUNT(*) FROM {self.table('conflictos_sensores')}) conflicting_ids
"""
            row = self.query(sql)[0]
            return {"reasons": [json.loads(x) for x in row["reasons"]], "conflicting_ids": row["conflicting_ids"]}
        return self.cached("quality", 5, fetch)

    def event(self, event_id):
        from google.cloud import bigquery
        sql = f"""
SELECT COUNT(*) copies_received,COUNT(DISTINCT payload_hash) variants,
  ARRAY_AGG(TO_JSON_STRING(STRUCT(event_id,node_id,zone_id,sensor,parameter,unit,value,
    original_ts,event_ts,published_at,processed_at,out_of_range)) ORDER BY processed_at LIMIT 1)[SAFE_OFFSET(0)] event_json
FROM {self.table('sensores_validos')} WHERE event_id=@event_id
"""
        row = self.query(sql, [bigquery.ScalarQueryParameter("event_id", "STRING", event_id)])[0]
        event = json.loads(row["event_json"]) if row["event_json"] else None
        return {"event": event, "copies_received": row["copies_received"], "variants": row["variants"]}
