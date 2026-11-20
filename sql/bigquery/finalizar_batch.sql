-- @batch_id se suministra como parámetro BigQuery. Destinos validados antes de renderizar.
BEGIN TRANSACTION;

ASSERT EXISTS (
  SELECT 1 FROM `__PROJECT__.__DATASET__.viajes_staging` WHERE batch_id = @batch_id
) AS 'El batch no tiene viajes válidos en staging';

ASSERT NOT EXISTS (
  SELECT trip_id FROM `__PROJECT__.__DATASET__.viajes_staging`
  WHERE batch_id = @batch_id GROUP BY trip_id HAVING COUNT(DISTINCT payload_hash) > 1
) AS 'El batch contiene IDs con contenidos conflictivos';

ASSERT NOT EXISTS (
  SELECT 1 FROM `__PROJECT__.__DATASET__.viajes_staging` s
  JOIN `__PROJECT__.__DATASET__.viajes_validos` t USING (trip_id)
  WHERE s.batch_id = @batch_id AND s.payload_hash != t.payload_hash
) AS 'El batch contradice un viaje ya consolidado';

MERGE `__PROJECT__.__DATASET__.viajes_validos` t
USING (
  SELECT * EXCEPT (batch_id, position) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY trip_id ORDER BY processed_at, payload_hash) position
    FROM `__PROJECT__.__DATASET__.viajes_staging` WHERE batch_id = @batch_id
  ) WHERE position = 1
) s
ON t.trip_id = s.trip_id
WHEN NOT MATCHED THEN INSERT (
  trip_id, payload_hash, origin_id, destination_id, pickup_local, dropoff_local,
  distance_km, total_usd, processed_at
) VALUES (
  s.trip_id, s.payload_hash, s.origin_id, s.destination_id, s.pickup_local, s.dropoff_local,
  s.distance_km, s.total_usd, s.processed_at
);

COMMIT TRANSACTION;
