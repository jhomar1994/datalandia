# Pipelines cloud de P3

Destino por defecto: `proyecto-datalandia`, región `us-central1`, dataset `lumina_demo`.
Los CLI reciben `--project` y `--dataset`; no cargan `.env` automáticamente.

## Preparación y validación local

Desde la raíz, manteniendo separados los entornos Spark/DuckDB y Beam:

```bash
.venv_bigdata/bin/python -m pipelines.cloud.preparar_muestras --trip-limit 100000 --sensor-limit 11000
.venv_beam/bin/python -m pipelines.cloud.publicar_eventos --dry-run --errores --output data/p3/validation/sensores_publicados.jsonl

.venv_beam/bin/python -m pipelines.cloud.pipeline_beam --mode batch --input data/p3/input/viajes.jsonl --batch-id prueba-local-01 --local-output data/p3/validation/batch

.venv_beam/bin/python -m pipelines.cloud.pipeline_beam --mode stream --local-input data/p3/validation/sensores_publicados.jsonl --node-map data/p3/input/puente_stream.jsonl --sensor-catalog data/p3/input/catalogo_sensores.jsonl --local-output data/p3/validation/stream
```

La entrada preparada ya existe en este equipo. Para repetir la preparación, usar otra ruta con `--output`.
No se sobrescribe una carpeta de entrada con contenido. Para exportar todos los viajes, usar
`--trip-limit 0 --output data/p3/full`; `--sensor-limit 0` selecciona todo el replay disponible.

Se seleccionan viajes sin prevalidarlos, con cobertura equilibrada entre zonas. Los resultados de
calidad de esa muestra no estiman directamente la tasa de errores del archivo completo.
El ID de viaje combina el SHA256 del archivo original y su posición Parquet; dos filas iguales
siguen siendo viajes distintos. El mismo archivo conserva los IDs al reintentarlo.
Una nueva versión física del archivo produce otra identidad de fuente y necesita una política de sustitución.

El manifiesto incluye hashes de los seis archivos y un `bundle_id` de contenido.
El publicador añade la fecha real de publicación; los tiempos de evento siguen siendo históricos simulados.
`--dry-run` no publica mensajes. El replay local de sensores es una prueba acotada con DirectRunner,
no un streaming Pub/Sub ni una ejecución distribuida.

## Preparación de GCP

Las tablas y vistas se definen en Terraform y sus esquemas en `schemas/bigquery/`.
Para subir el bundle y cargar las tres referencias agregadas:

```bash
.venv_beam/bin/python scripts/stage_inputs.py --load-references
```

El destino se obtiene del estado Terraform y se contrasta con el proyecto autorizado.
Los objetos se guardan en `p3/inputs/<bundle_id>/`, sin sobrescribir objetos de contenido diferente.
La carga de referencias reemplaza solo `puente_batch`, `puente_stream` y `referencia_zona`.
Las URIs y jobs de carga quedan en `referencias_locales/p3_staging.json`.

## Batch y reintentos

Beam valida los viajes y escribe con cargas de archivos en `viajes_staging`, identificados por `batch_id`.
Los rechazos van a `rechazados_raw`. Tras comprobar que el job terminó en `DONE`, consolidar:

```bash
.venv_beam/bin/python scripts/finalize_batch.py --batch-id ID_DEL_BATCH_TERMINADO
```

El SQL comprueba conflictos y ejecuta un MERGE transaccional por `trip_id`.
Repetir el mismo batch no añade viajes ni importes al destino. Staging conserva copias de reintentos.
Un ID con otro contenido bloquea la consolidación; el operador puede auditarlo en staging.
Ejecutar una sola consolidación batch a la vez. No se ofrece una garantía de exactamente una vez
para escritores concurrentes o para fuentes con distintas versiones físicas.

## Sensores y Gold

La validación carga el puente completo de nodos y el catálogo de sensores; no existe un nodo fijo.
Valida unidad, número finito, timestamps con zona, desplazamiento y periodo simulado.
Los valores físicos fuera de rango se conservan con marca `out_of_range`.

Silver conserva copias recibidas. Gold deduplica por `event_id` y hash de contenido, excluyendo IDs
conflictivos que se exponen en `conflictos_sensores`. El hash ignora la hora de republicación.
Los rechazos se consultan deduplicados por `rejection_id` en `rechazados`.

`gold_movilidad_5min` mantiene la granularidad de movilidad, `gold_sensores_5min` la de métricas,
y `gold_zona_5min` cruza ambas con el contexto. No sumar viajes repetidos entre métricas de sensores.

## Ejecución distribuida verificada

El paquete `setup.py` se distribuye con `--setup_file` y fue instalado en workers privados reales.
`scripts/run_dataflow.py` aplica un worker, tiempo máximo y cierre controlado, sin IP pública ni NAT.
Batch y streaming completaron las pruebas; ver `docs/evidencias/demo_final.json`.
No se necesita un clúster Dataproc. Para ejecutar y comprobar el cierre, seguir `demo/README.md`.

Para una demo posterior, republicar IDs ya procesados demuestra deduplicación y conserva los conteos.
Para demostrar datos nuevos se deberán generar eventos de prueba con IDs nuevos y marcados como sintéticos.

La guía histórica P2 permanece en [docs/despliegue_gcp_p2.md](../../docs/despliegue_gcp_p2.md).
