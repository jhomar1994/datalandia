# Contratos y esquemas

`bigquery/*.json` contiene los siete esquemas compartidos por Terraform, cargas de referencia y Beam.
Los identificadores de viajes y eventos, hashes de contenido y `batch_id` de staging son obligatorios.

Las reglas puras se encuentran en `pipelines/cloud/validaciones.py`.
Los contratos actuales de ingesta cloud requieren:

- Viaje: `trip_id`, origen/destino, fechas locales, millas e importe.
- Sensor: `event_id`, nodo, subsistema, sensor, parámetro, unidad, valor, tiempos original/simulado
  y `published_at` con zona horaria.
- Rechazo: identidad determinista, fuente, razón, payload y momento de procesamiento.

El catálogo de nodos y sensores se prepara como JSONL versionado por hash de contenido.
Los contratos locales históricos se conservan en `docs/ejecucion_local.md`.
