SELECT s.*, v.viajes, v.total_usd, v.total_km, v.tarifa_usd_km,
  r.zone_name, r.population_2017, r.uber_mean_seconds_2017,
  TRUE homologacion_simulada
FROM `__PROJECT__.__DATASET__.gold_sensores_5min` s
LEFT JOIN `__PROJECT__.__DATASET__.gold_movilidad_5min` v USING (zone_id, window_start_utc)
LEFT JOIN `__PROJECT__.__DATASET__.referencia_zona` r ON r.datalandia_zone_id = s.zone_id
