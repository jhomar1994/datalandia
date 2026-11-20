# Consultas SQL

Los archivos de `bigquery/` son la fuente de las vistas desplegadas por Terraform.
Los marcadores `__PROJECT__` y `__DATASET__` se sustituyen por identificadores validados.
Los valores de datos, como `batch_id`, se suministran como parámetros BigQuery.

- `finalizar_batch.sql`: validaciones de conflicto y MERGE transaccional desde staging.
- `gold_movilidad_5min.sql`: indicadores de viajes a su propia granularidad.
- `gold_sensores_5min.sql`: métricas de eventos únicos y sin conflictos.
- `gold_zona_5min.sql`: cruce de métricas, movilidad y contexto.
- `conflictos_sensores.sql`: IDs con distintos contenidos.
- `rechazados.sql`: rechazos únicos, manteniendo el historial raw separado.

No sumar indicadores de viajes después de unirlos a varias métricas sin volver a zona y ventana.
