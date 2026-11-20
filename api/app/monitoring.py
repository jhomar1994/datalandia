"""Contrato del tablero: una consulta compartida, caché y reloj UTC del servidor."""
import datetime as dt
import json
import threading
import time

from .repository import BigQueryRepository

UTC = dt.timezone.utc


class MonitoringRepository(BigQueryRepository):
    def __init__(self, settings):
        super().__init__(settings)
        self._snapshot_lock = threading.Lock()
        self._snapshot = None
        self._expires = 0

    def snapshot(self):
        with self._snapshot_lock:
            if self._snapshot is not None and time.monotonic() < self._expires:
                return self._snapshot
            from google.cloud import bigquery
            # El horizonte compartido cubre sesión, gráfico (hasta 60 min) y último evento (24 h).
            sql = f"""
WITH recent AS (
 SELECT event_id,payload_hash,node_id,sensor,parameter,value,unit,published_at,processed_at
 FROM {self.table('sensores_validos')}
 WHERE processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 24 HOUR)
), canonical AS (
 SELECT * EXCEPT(pos,variants) FROM (
  SELECT *,ROW_NUMBER() OVER(PARTITION BY event_id ORDER BY processed_at,published_at) pos,
   COUNT(DISTINCT payload_hash) OVER(PARTITION BY event_id) variants FROM recent
 ) WHERE pos=1 AND variants=1
 AND event_id NOT IN (SELECT event_id FROM {self.table('conflictos_sensores')})
), rejected AS (
 SELECT source,reason,raw_payload,processed_at FROM {self.table('rechazados')}
 WHERE processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL @session MINUTE)
), gold AS (
 SELECT * FROM {self.table('gold_zona_5min')}
 WHERE window_start_utc=(SELECT MAX(window_start_utc) FROM {self.table('gold_zona_5min')})
), representative AS (
 SELECT zone_id,unit,SAFE_DIVIDE(SUM(valor_promedio*lecturas),SUM(lecturas)) value,
  ROW_NUMBER() OVER(PARTITION BY zone_id ORDER BY SUM(lecturas) DESC,unit) pos
 FROM gold WHERE parameter=@parameter GROUP BY zone_id,unit
), zones AS (
 SELECT g.zone_id zona_id,SUM(g.lecturas) lecturas,MAX(g.viajes) viajes,
  SAFE_DIVIDE(MAX(g.total_usd),MAX(g.total_km)) importe_km,
  ANY_VALUE(r.value) valor_medio,ANY_VALUE(r.unit) unidad
 FROM gold g LEFT JOIN representative r ON g.zone_id=r.zone_id AND r.pos=1 GROUP BY g.zone_id
), accepted_minutes AS (
 SELECT TIMESTAMP_TRUNC(processed_at,MINUTE) minuto,COUNT(*) aceptadas FROM canonical
 WHERE processed_at>=TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 60 MINUTE) GROUP BY minuto
), rejected_minutes AS (
 SELECT TIMESTAMP_TRUNC(processed_at,MINUTE) minuto,COUNT(*) rechazadas FROM {self.table('rechazados')}
 WHERE processed_at>=TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 60 MINUTE) GROUP BY minuto
), minutes AS (
 SELECT minuto,COALESCE(a.aceptadas,0) aceptadas,COALESCE(r.rechazadas,0) rechazadas
 FROM UNNEST(GENERATE_TIMESTAMP_ARRAY(
  TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(),MINUTE),INTERVAL 59 MINUTE),
  TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(),MINUTE),INTERVAL 1 MINUTE)) minuto
 LEFT JOIN accepted_minutes a USING(minuto) LEFT JOIN rejected_minutes r USING(minuto)
), latest AS (
 SELECT s.event_id,p.datalandia_zone_id zona_id,s.node_id,s.sensor,s.parameter,s.value,s.unit,
  s.published_at,s.processed_at,TIMESTAMP_DIFF(s.processed_at,s.published_at,MICROSECOND)/1000000.0 latencia_s
 FROM recent s LEFT JOIN {self.table('puente_stream')} p ON s.node_id=p.node_id
 ORDER BY s.processed_at DESC,s.event_id LIMIT 1
)
SELECT
 (SELECT COUNT(*) FROM canonical WHERE processed_at>=TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL @session MINUTE)) aceptadas,
 (SELECT COUNT(*) FROM rejected) rechazadas,
 (SELECT COUNT(DISTINCT p.datalandia_zone_id) FROM canonical c
  LEFT JOIN {self.table('puente_stream')} p ON c.node_id=p.node_id
  WHERE processed_at>=TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL @session MINUTE)) zonas_activas,
 (SELECT MAX(processed_at) FROM recent) ultima_ingesta,
 (SELECT AVG(TIMESTAMP_DIFF(processed_at,published_at,MICROSECOND))/1000000.0 FROM canonical
  WHERE processed_at>=TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 5 MINUTE)) ingestion_seconds,
 (SELECT MAX(window_start_utc) FROM gold) ventana_inicio,
 ARRAY(SELECT TO_JSON_STRING(z) FROM zones z ORDER BY lecturas DESC,zona_id) zones_json,
 ARRAY(SELECT TO_JSON_STRING(m) FROM minutes m ORDER BY minuto) minutes_json,
 (SELECT TO_JSON_STRING(l) FROM latest l) latest_json,
 ARRAY(SELECT TO_JSON_STRING(STRUCT(processed_at,reason AS motivo,raw_payload))
  FROM rejected ORDER BY processed_at DESC LIMIT 50) rejections_json
"""
            started = time.perf_counter()
            params = [bigquery.ScalarQueryParameter('session', 'INT64', self.settings.session_minutes),
                      bigquery.ScalarQueryParameter('parameter', 'STRING', self.settings.sensor_parameter)]
            row = self.query(sql, params)[0]
            row['query_seconds'] = time.perf_counter() - started
            self._snapshot = row
            self._expires = time.monotonic() + self.settings.cache_ttl
            return row

    def dashboard_kpis(self):
        row = self.snapshot()
        ingestion = row['ingestion_seconds']
        return {'aceptadas': row['aceptadas'], 'rechazadas': row['rechazadas'],
                'recibidas': row['aceptadas'] + row['rechazadas'],
                'latencia_e2e_s': None if ingestion is None else ingestion + row['query_seconds'],
                'latencia_meta_s': self.settings.latency_target,
                'zonas_activas': row['zonas_activas'], 'ultima_ingesta': row['ultima_ingesta']}

    def dashboard_latency(self):
        row = self.snapshot()
        # Medir preparación después de obtener el snapshot evita contar dos veces
        # la espera por el lock cuando otro endpoint está ejecutando la consulta.
        started = time.perf_counter()
        ingestion = row['ingestion_seconds']
        stages = [
            {'nombre': 'Ingesta y validación', 'servicio': 'Pub/Sub + Dataflow', 'segundos': ingestion},
            {'nombre': 'Consulta', 'servicio': 'BigQuery (consulta compartida)', 'segundos': row['query_seconds']}]
        overhead = time.perf_counter() - started
        stages.append({'nombre': 'Preparación de respuesta', 'servicio': 'API Cloud Run', 'segundos': overhead})
        return {'etapas': stages,
            'total_s': None if ingestion is None else ingestion + row['query_seconds'] + overhead}

    def dashboard_zones(self):
        row = self.snapshot()
        start = row['ventana_inicio']
        return {'ventana_inicio': start, 'ventana_fin': start + dt.timedelta(minutes=5) if start else None,
                'zonas': [json.loads(x) for x in row['zones_json']]}

    def dashboard_minutes(self, minutes):
        row = self.snapshot()
        buckets = {x['minuto']: x for x in map(json.loads, row['minutes_json'])}
        now = dt.datetime.now(UTC).replace(second=0, microsecond=0)
        result = []
        # Recalcular serie al responder también cubre un cambio de minuto durante la caché.
        for i in range(minutes - 1, -1, -1):
            stamp = (now - dt.timedelta(minutes=i)).isoformat().replace('+00:00', 'Z')
            item = buckets.get(stamp, {'minuto': stamp, 'aceptadas': 0, 'rechazadas': 0})
            result.append(item)
        return {'minutos': result}

    def dashboard_latest(self):
        raw = self.snapshot()['latest_json']
        if not raw:
            return {}
        return {**json.loads(raw), 'ahora': dt.datetime.now(UTC)}

    def dashboard_rejections(self, limit):
        rows = []
        for raw in self.snapshot()['rejections_json'][:limit]:
            r = json.loads(raw)
            try:
                payload = json.loads(r.pop('raw_payload'))
                parts = [str(payload[k]) for k in ('node_id','sensor','event_id','trip_id') if payload.get(k)]
                detail = ' · '.join(parts) or 'Registro separado para revisión'
            except (ValueError, TypeError, AttributeError):
                detail = 'Payload inválido; revisar cuarentena'
            rows.append({'processed_at': r['processed_at'], 'motivo': r['motivo'],
                         'detalle': ''.join(c for c in detail if c.isprintable())[:80]})
        return {'rechazos': rows}
