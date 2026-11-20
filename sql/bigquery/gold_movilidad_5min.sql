SELECT FORMAT('DL-%03d', origin_id) zone_id,
  TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(TIMESTAMP(pickup_local, 'America/New_York')), 300)*300) window_start_utc,
  COUNT(*) viajes, SUM(total_usd) total_usd, SUM(distance_km) total_km,
  SAFE_DIVIDE(SUM(total_usd), SUM(distance_km)) tarifa_usd_km
FROM `__PROJECT__.__DATASET__.viajes_validos`
GROUP BY 1, 2
