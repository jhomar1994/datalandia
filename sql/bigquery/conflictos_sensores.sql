SELECT event_id, COUNT(*) copias, COUNT(DISTINCT payload_hash) contenidos_distintos
FROM `__PROJECT__.__DATASET__.sensores_validos`
GROUP BY event_id HAVING COUNT(DISTINCT payload_hash) > 1
