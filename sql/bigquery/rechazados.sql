SELECT * EXCEPT (position) FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY rejection_id ORDER BY processed_at) position
  FROM `__PROJECT__.__DATASET__.rechazados_raw`
) WHERE position = 1
