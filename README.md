# DataLandia — pipeline híbrido de datos para Lumina

Proyecto de integración y analítica que combina información de movilidad, sensores y contexto demográfico mediante una arquitectura medallón **Raw/Bronze → Silver → Gold**.

La implementación incluye procesamiento batch con DuckDB y Spark, microbatch con Spark Structured Streaming, homologación de fuentes heterogéneas y estructuras analíticas materializadas en Parquet y SQLite.

## Capacidades principales

- Limpieza y validación de viajes, sensores y referencias territoriales.
- Conversión y normalización de unidades, fechas y zonas horarias.
- Tablas puente para relacionar zonas de NYC TLC, Censo INE, Uber Movement y nodos Array of Things.
- Procesamiento batch de archivos completos.
- Procesamiento streaming mediante microbatches y checkpoint de Spark.
- Cuarentena de registros inválidos con el motivo del rechazo.
- Agregaciones analíticas por zona y ventanas de cinco minutos.
- Modelo Gold con hechos de movilidad, hechos de sensores y dimensión territorial.
- Aprovisionamiento manual de servicios administrados en Google Cloud mediante comandos de shell.

> **Importante:** las homologaciones entre ciudades y algunos datos del caso DataLandia son simulados con fines académicos. No representan equivalencias geográficas reales.

## Arquitectura

```text
Fuentes heterogéneas
  ├─ NYC TLC (viajes y zonas)
  ├─ Uber Movement (tiempos de viaje)
  ├─ Array of Things (sensores)
  └─ Censo INE (contexto demográfico)
             │
             ▼
data/raw  ── validación, limpieza y homologación
             │
             ▼
data/silver ── datos válidos, rechazados, puentes y ventanas
             │
             ├──────── batch: DuckDB / Spark
             └──── streaming: Spark Structured Streaming
             │
             ▼
data/gold / data/p2/gold
  └─ hechos, dimensiones y vistas listas para consulta
```

## Infraestructura en Google Cloud

Además de la ejecución local, se aprovisionó manualmente una arquitectura de demostración en **Google Cloud Platform** usando comandos `gcloud` y `bq`. No se utilizó Terraform.

Los recursos utilizados fueron:

| Servicio | Recurso o función |
|---|---|
| Cloud Storage | Bucket `gs://datalandia-lumina-prototipo` para muestras y entradas batch. |
| Pub/Sub | Topic `lumina-eventos` y suscripción `lumina-streaming` para eventos de sensores. |
| Dataflow | Pipelines Apache Beam para validación batch y consumo streaming. |
| BigQuery | Dataset `datalandia.lumina_demo` con datos válidos, rechazados y vista Gold. |
| Workflows | Workflow `lumina-verificar` para ejecutar controles de conteos en BigQuery. |
| IAM | Cuentas de servicio separadas para workers de Dataflow y orquestación. |
| VPC | Red y subred privadas para los workers, con Private Google Access y sin IP pública. |

El flujo desplegado fue:

```text
Batch:     Cloud Storage ──► Dataflow / Apache Beam ──► BigQuery
Streaming: Pub/Sub ────────► Dataflow / Apache Beam ──► BigQuery
                                                        │
                                                        ▼
                                               vista Gold de 5 minutos
                                                        │
                                                        ▼
                                             verificación con Workflows
```

La demostración registrada el **8 de noviembre de 2026** procesó una muestra de viajes y eventos de sensores, incluyó registros inválidos para comprobar la cuarentena y republicó eventos para validar la deduplicación de la vista Gold. Los jobs de Dataflow se cancelaron después de la prueba para limitar costos; por tanto, el repositorio no presupone que exista actualmente un job streaming activo.

El aprovisionamiento se realizó desde Cloud Shell con operaciones equivalentes a las siguientes:

```bash
# APIs
gcloud services enable \
  dataflow.googleapis.com bigquery.googleapis.com pubsub.googleapis.com \
  storage.googleapis.com iam.googleapis.com compute.googleapis.com

# Almacenamiento
gcloud storage buckets create gs://datalandia-lumina-prototipo \
  --location=us-central1 \
  --uniform-bucket-level-access \
  --public-access-prevention

# Mensajería
gcloud pubsub topics create lumina-eventos
gcloud pubsub subscriptions create lumina-streaming \
  --topic=lumina-eventos \
  --message-retention-duration=1d

# Almacén analítico
bq mk --dataset --location=us-central1 datalandia:lumina_demo

# Identidad de los workers
gcloud iam service-accounts create lumina-dataflow \
  --display-name="Lumina Dataflow worker"
```

Estos comandos documentan el procedimiento, pero no deben ejecutarse sin verificar previamente el proyecto activo, facturación, permisos, recursos existentes y posibles costos. Los nombres globales —como el del bucket— deben cambiarse al reproducir la solución en otro proyecto.

La carpeta local `infraestructura_gcp/` contiene los scripts de Beam, SQL Gold, publicación y verificación usados durante la demostración, pero está excluida de Git por la política actual del archivo `.gitignore`.

## Estructura del repositorio

```text
datalandia/
├── data/
│   ├── raw/                     # Fuentes originales
│   ├── silver/                  # Datos limpios, puentes y checkpoints
│   ├── gold/                    # Agregados analíticos
│   └── p2/                      # Demostración híbrida batch/streaming
├── notebooks/
│   ├── 01_ETL_Medallion_Homologacion.py
│   ├── 01_ETL_Medallion_Homologacion.ipynb
│   ├── 02_puentes_batch_streaming.py
│   ├── 02_Puentes_Batch_Streaming.ipynb
│   ├── 03_p2_hibrido.py
│   └── README_P2.md
├── requirements.in             # Dependencias directas
├── requirements.txt            # Dependencias fijadas
└── setup_project.py            # Creación de la estructura básica
```

Los datos no se versionan. Los archivos `.gitkeep` conservan la estructura de `data/` en Git sin subir CSV, Parquet, JSONL, bases SQLite ni checkpoints.

## Requisitos

- Python 3.12 recomendado.
- Java instalado y disponible en `PATH`, requerido por PySpark.
- Memoria y almacenamiento suficientes para procesar el archivo mensual de NYC TLC.

Las dependencias principales son PySpark 4.3, DuckDB 2.0, PyArrow, pandas y NumPy.

## Instalación

Ejecute los comandos desde la raíz del proyecto:

```bash
python3.12 -m venv .venv_bigdata
source .venv_bigdata/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python setup_project.py
```

En Windows, la activación del entorno cambia por:

```powershell
.venv_bigdata\Scripts\Activate.ps1
```

## Fuentes de datos

El primer pipeline descarga automáticamente el catálogo de zonas y los viajes amarillos de enero de 2024 de NYC TLC. Si no encuentra las otras fuentes, genera muestras sintéticas compatibles con ese ejercicio.

El pipeline de puentes y la demostración híbrida utilizan las siguientes rutas:

```text
data/raw/
├── nyc_tlc/
│   ├── yellow_tripdata_2024-01.parquet
│   └── taxi_zone_lookup.csv
├── uber_movement/
│   └── Travel_Times.csv
├── ine/
│   └── Microdato_Censo-Personas.csv
└── array_of_things/
    ├── data_sample_1m.csv
    ├── nodes.csv
    └── sensors.csv
```

Estas fuentes pesadas deben descargarse o copiarse localmente después de clonar el repositorio. No están incluidas en Git.

## Ejecución

### 1. ETL medallón y homologación espacial

Este ejercicio descarga NYC TLC, prepara las fuentes auxiliares y construye una tabla Gold horaria con Spark:

```bash
.venv_bigdata/bin/python notebooks/01_ETL_Medallion_Homologacion.py
```

También puede ejecutarse de forma interactiva con:

```bash
jupyter lab
```

### 2. Puentes batch y replay streaming

Requiere las fuentes originales indicadas anteriormente. Construye las tablas puente, procesa el replay de sensores con Spark Structured Streaming y genera el Gold de cinco minutos:

```bash
.venv_bigdata/bin/python notebooks/02_puentes_batch_streaming.py
```

Salidas principales:

- `data/silver/datalandia_v1/bridge_batch.parquet`
- `data/silver/datalandia_v1/bridge_streaming.parquet`
- `data/silver/datalandia_v1/batch_reference.parquet`
- `data/silver/datalandia_v1/nyc_trip_windows.parquet`
- `data/gold/datalandia_v1/zone_5min.parquet`

El script protege los resultados existentes. Si encuentra una ejecución anterior, solicita usar otra versión en vez de sobrescribirla.

### 3. Procesamiento híbrido local

Esta etapa depende de las tablas puente generadas por el paso anterior.

Crear el batch inicial y la base analítica:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py batch
```

Iniciar el consumidor streaming en una terminal:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py serve
```

Publicar 1,000 lecturas históricas desde otra terminal:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py publish \
  --limit 1000 \
  --chunk-size 250 \
  --delay 1
```

Inyectar eventos de prueba válidos e inválidos:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py inject
```

Consultar microbatches, rechazos y ventanas procesadas:

```bash
.venv_bigdata/bin/python notebooks/03_p2_hibrido.py status
```

Para detener el consumidor streaming, use `Ctrl+C`. El checkpoint permite continuar con los archivos que todavía no fueron procesados.

## Modelo analítico

La base `data/p2/gold/lumina.sqlite` contiene:

| Objeto | Tipo | Propósito |
|---|---|---|
| `dim_zone` | Dimensión | Zona, borough y atributos demográficos e históricos. |
| `mobility_5min` | Hecho batch | Viajes, importes, distancias y duración por zona y ventana. |
| `sensor_observation` | Hecho detallado | Eventos de sensores aceptados y deduplicados. |
| `rejected_events` | Cuarentena | Payload original y motivo de rechazo. |
| `processed_batches` | Control | Conteos y confirmación de cada microbatch. |
| `fact_sensor_5min` | Vista | Agregados de sensores por zona, ventana y métrica. |
| `gold_zone_context_5min` | Vista Gold | Cruce de sensores, movilidad, zona, Censo y Uber. |

Una fila de `gold_zone_context_5min` representa una métrica de sensor dentro de una zona y ventana, no un viaje individual. Los totales de movilidad se repiten entre sensores de la misma ventana y no deben sumarse sin regresar primero a la granularidad zona–ventana.

## Calidad y comportamiento del streaming

- Los eventos deben incluir identificador, nodo, sensor, unidad, valor y timestamps con zona horaria.
- Un `event_id` repetido con el mismo contenido se clasifica como duplicado.
- Un `event_id` repetido con contenido distinto se clasifica como conflicto.
- Los nodos no homologados, sensores desconocidos y valores no numéricos pasan a cuarentena.
- Los eventos aceptados se agrupan en ventanas UTC de cinco minutos.
- La transacción SQLite confirma observaciones, rechazos y control del microbatch en conjunto.

## Limitaciones

- Es una demostración académica local, no un servicio de alta disponibilidad.
- SQLite es un destino de un solo proceso.
- El streaming local funciona por microbatches de archivos.
- No existe watermark ni vencimiento de estado; la demostración usa un día histórico fijo.
- Las homologaciones entre ciudades son reproducibles y auditables, pero simuladas.
- No se afirma una garantía exactly-once para sistemas externos.
- El workflow de verificación consulta resultados, pero no constituye una orquestación completa del ciclo de vida de Dataflow.
- Los recursos cloud pueden generar costos y deben verificarse o detenerse después de cada prueba.

Consulte [notebooks/README_P2.md](notebooks/README_P2.md) para el contrato de eventos, reglas de validación y detalles operativos de la demostración híbrida.
