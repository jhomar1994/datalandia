WITH unique_events AS (
  SELECT * EXCEPT (position) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY processed_at, published_at) position
    FROM `__PROJECT__.__DATASET__.sensores_validos`
    WHERE event_id NOT IN (SELECT event_id FROM `__PROJECT__.__DATASET__.conflictos_sensores`)
  ) WHERE position = 1
)
SELECT zone_id,
  TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(event_ts), 300)*300) window_start_utc,
  subsystem, sensor, parameter, unit, COUNT(*) lecturas, AVG(value) valor_promedio,
  COUNTIF(out_of_range) lecturas_fuera_rango,
  AVG(TIMESTAMP_DIFF(processed_at, published_at, MILLISECOND))/1000.0 latencia_procesamiento_seg
FROM unique_events
GROUP BY 1, 2, 3, 4, 5, 6
