# P2: procesamiento híbrido de Lumina

La implementación local utiliza las fuentes actuales, las homologaciones simuladas de `data/silver/datalandia_v1` y una fecha simulada del 1 de enero de 2024 en Nueva York. El batch usa DuckDB; el replay continuo usa Spark Structured Streaming. SQLite almacena las observaciones, rechazos y vistas analíticas de la demostración local. No hay servicios de GCP desplegados.

## Ejecución

Desde la raíz del proyecto, usando el entorno existente:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py batch
```

El batch ya fue ejecutado. El comando protege sus resultados y no sobrescribe `data/p2/silver/batch` si ya existe. Para una ejecución independiente use una copia del proyecto o cambie las rutas de salida. La entrada incluye las referencias y puentes de v1; no está diseñado para ejecutarse sin ellos.

En una terminal, iniciar el streaming y dejarlo activo:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py serve
```

En otra terminal, publicar lecturas de la muestra histórica:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py publish --limit 1000 --chunk-size 250 --delay 1
```

Para publicar datos de prueba con errores intencionales:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py inject
```

Para consultar avance, rechazos y ventanas:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py status
```

`serve` no termina automáticamente. Cada archivo JSONL nuevo publicado en `data/p2/stream/input` activa un microbatch. El publicador escribe temporalmente fuera de esa carpeta y mueve el archivo completo de forma atómica. Para detener, use Ctrl+C; al reiniciar se reutilizan el checkpoint y la base. Mantenga juntos `data/p2/stream/checkpoint`, `data/p2/stream/input` y `data/p2/gold/lumina.sqlite`; no reinicie el checkpoint manteniendo la misma base, ya que los números de lote dejarían de identificar la misma ejecución.

## Contrato de eventos

Un evento es un objeto JSON por línea con `event_id`, `node_id`, `subsystem`, `sensor`, `parameter`, `value`, `unit`, `event_timestamp_original` y `event_timestamp_simulado`. Los dos timestamps deben incluir zona horaria; la reproducción mantiene un desplazamiento fijo de 2.191 días y acepta únicamente la ventana original 2018-01-01 05:00 UTC a 2018-01-02 05:00 UTC, límite superior exclusivo. Las ventanas simuladas se expresan en UTC y corresponden al 1 de enero de 2024 en Nueva York.

El publicador deriva un ID estable del contenido de la lectura original. Si dos registros de origen fueran idénticos en todos esos campos, compartirían ID y uno se trataría como duplicado. Para una fuente operativa debe emplearse un identificador único generado por el productor. Eventos válidos fuera de orden dentro del día admitido actualizan su ventana existente; no hay watermark ni vencimiento de ventanas. Este es un modelo local de día fijo, no una política de lateness para producción.

El mismo `event_id` y contenido se rechaza como `duplicado`; el mismo ID con contenido diferente se rechaza como `event_id_conflictivo`. Otros rechazos incluyen nodo sin puente, sensor desconocido, timestamp inválido, valor no numérico y unidad distinta del catálogo. Las lecturas numéricas fuera de los límites del catálogo se conservan y marcan, porque no necesariamente indican una falla física. Los sensores de identificación y los valores no numéricos no ingresan a la fact numérica.

## Salidas y modelo

| Ruta o tabla | Contenido |
|---|---|
| `data/p2/silver/batch/nyc_valid.parquet` | Viajes que pasan las reglas. |
| `data/p2/silver/batch/nyc_rejected.parquet` | Viajes rechazados con una o varias causas. |
| `data/p2/silver/batch/batch_metrics.json` | Conteos y versión de reglas. |
| `data/p2/silver/batch/fact_mobility_5min.parquet` | Viajes del 1 de enero, por zona de origen y ventana de 5 minutos. |
| `data/p2/gold/lumina.sqlite`: `mobility_5min`, `dim_zone` | Hechos y referencias históricas de batch. |
| `sensor_observation` | Mediciones aceptadas con timestamp original, simulado, unidad y marca de rango. |
| `rejected_events` | Cuarentena streaming con evento original y motivo. |
| `processed_batches` | Conteos de cada microbatch confirmado. |
| `fact_sensor_5min` | Vista dinámica por zona, ventana, nodo, subsistema, sensor, parámetro y unidad. |
| `gold_zone_context_5min` | Vista que une las mediciones con viajes, Censo y Uber por zona y ventana. Una fila representa una métrica de sensor en una ventana, no un viaje individual. |

Las vistas se recalculan sobre observaciones persistidas: al llegar otro evento aceptado para la misma clave, cambian automáticamente el conteo y el promedio. Los valores de movilidad se repiten para cada sensor en una misma zona y ventana; no se deben sumar directamente después de esa unión sin deduplicar a la granularidad de movilidad.

Ejemplo de consulta con Python:

```python
import sqlite3
import pandas as pd

con = sqlite3.connect('data/p2/gold/lumina.sqlite')
rechazos = pd.read_sql_query('SELECT reason, count(*) total FROM rejected_events GROUP BY reason', con)
indicadores = pd.read_sql_query('SELECT * FROM gold_zone_context_5min LIMIT 20', con)
```

## Reglas y límites

Batch valida pickup dentro de enero de 2024, duración positiva de hasta 4 horas, distancia de 0.3 a 120 millas, importe positivo y zona origen/destino entre 1 y 263. Son umbrales de calidad propuestos, no garantías de calidad TLC. Las razones pueden acumularse y su conteo por motivo puede superar el total de filas rechazadas. Las fechas de pickup se interpretan en `America/New_York`. La tarifa por km se calcula como suma de importes dividida por suma de distancias válidas; no es costo de operación de Lumina.

Los puentes y referencias de v1 son simulados; se conservan los años originales de Uber y Censo. `data/p2/stream/input` y la base incluyen eventos sintéticos `demo-*` utilizados para verificar aceptación, rechazos, deduplicación y actualización. Están etiquetados por su `event_id`.

SQLite y `foreachBatch` son un destino local, de un solo proceso, adecuado para la demostración y no para un servicio distribuido o alta disponibilidad. La transacción de SQLite confirma observaciones, rechazos y número de batch en conjunto; con el mismo checkpoint un batch repetido no se inserta dos veces. No se afirma una garantía de exactamente una vez para sistemas externos. Para GCP deberá diseñarse un sink idempotente distribuido, política de lateness, límites de estado, métricas reales de latencia y recuperación, y un procesador compatible con la arquitectura elegida.
