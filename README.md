# DataLandia — pipeline híbrido de datos para Lumina

Proyecto de integración y analítica que combina información de movilidad, sensores y contexto demográfico mediante una arquitectura medallón **Raw/Bronze → Silver → Gold**.

**¿Primera vez en el proyecto?** Leer la [guía de onboarding técnico](docs/onboarding_tecnico.md): explica la evolución desde las fuentes originales y el procesamiento local hasta Terraform, los pipelines GCP, la API y la demo final, con resultados y pendientes.

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
- Aprovisionamiento reproducible de la infraestructura base GCP con Terraform.

> **Importante:** las homologaciones entre ciudades y algunos datos del caso DataLandia son simulados con fines académicos. No representan equivalencias geográficas reales.

## Arquitectura del procesamiento local

La [guía de onboarding](docs/onboarding_tecnico.md#5-arquitectura-final-y-aprovisionamiento) incluye el diagrama de la implementación final en GCP.

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

## Estado del proyecto

| Componente | Estado |
|---|---|
| Procesamiento local | Implementado con DuckDB, Spark y SQLite. |
| Histórico GCP de P2 | Registro de la demostración en el proyecto anterior `datalandia`. |
| Pipelines cloud P3 | Batch y streaming ejecutados en Dataflow; validación end-to-end con API realizada. |
| Destino de P3 | `proyecto-datalandia`, número `637872675138`, región `us-central1`. |
| Infraestructura GCP | Terraform: red, IAM, buckets, Pub/Sub, ocho tablas (incluido control batch), cinco vistas, workflow y Cloud Run. |
| API y consumidor P3 | FastAPI y tablero desplegados en Cloud Run privado; mínimo cero y máximo una instancia. |

El código cloud está en `pipelines/cloud/`, el SQL en `sql/bigquery/` y el workflow en `workflows/`.
El destino por defecto ya es `proyecto-datalandia`. Los CLI admiten parámetros de destino; `.env.example`
no se carga automáticamente. Consultar [pipelines P3](docs/pipelines_p3.md),
[infraestructura](infra/terraform/README.md) y [evidencia inicial](docs/evidencias/infraestructura_base.md).

La demostración del 8 de noviembre de 2026 utilizó muestras y los jobs se detuvieron tras
las pruebas. Ese resultado histórico no implica que hoy exista un job activo.

## Demo final P3

Los siguientes conteos describen la prueba inicial. Las repeticiones añaden eventos; la actualización del tablero está documentada en [evidencias de monitoreo](docs/evidencias/actualizacion_tablero.md).

- Batch real de 10.000 registros: 8.459 viajes válidos, 1.541 rechazos y 255 zonas válidas de origen.
- Streaming de 225 mensajes: 184 recepciones válidas, 41 rechazos, once zonas y 181 eventos únicos en Gold.
- Evento de control disponible en la API en aproximadamente doce segundos con el worker listo; medición de un caso, no un SLA.
- Duplicados y conflictos comprobados; quince pruebas unitarias/HTTP y dos integraciones SQL en BigQuery aprobadas.

Acceso al tablero privado:

```bash
gcloud run services proxy lumina-api --project=proyecto-datalandia --region=us-central1 --port=8080
```

Abrir `http://127.0.0.1:8080`. Para la demo en vivo, en otra terminal:

```bash
.venv_beam/bin/python scripts/demo_e2e.py --visible-seconds 30
```

Consultar [guion y apagado](demo/README.md), [API](api/README.md),
[evidencias](docs/evidencias/demo_final.json), [observaciones P2](docs/revision_observaciones_p2.md),
[costos](costs/README.md) y [borrador para Slides](presentation/guion_slides.md).
Presupuesto total de pruebas y demo: S/50; gasto facturado NO VERIFICADO.
La ejecución se realiza bajo demanda, sin mantener streaming 24/7.
El tablero nuevo se revisó en Chrome en modo simulado y con la API. La presentación ejecutiva de quince minutos está disponible en `presentation/output/` (PPTX y PDF). La entrega P3 se mantiene en la rama `feat/p3-entrega-final`; usar su historial para identificar la versión auditada.

## Estructura del repositorio

```text
datalandia/
├── pipelines/
│   ├── local/                   # ETL medallón, puentes y procesamiento híbrido
│   └── cloud/                   # Beam P3, contratos y publicador configurable
├── notebooks/                   # Notebooks interactivos originales
├── infra/terraform/             # Infraestructura base aplicada y verificada
├── api/                         # FastAPI y contenedor Cloud Run
├── consumer/                    # Tablero consumidor de la API
├── sql/bigquery/                # Vista Gold
├── workflows/                   # Verificación P3 en el proyecto actual
├── schemas/                     # Esquemas BigQuery compartidos
├── scripts/                     # Preparación y futuras operaciones
├── requirements/                # Dependencias local y cloud separadas
├── tests/                       # Reglas, MERGE real y fixtures históricos
├── demo/                        # Guion de demostración
├── costs/                       # Presupuesto y calculadora anual preliminar
├── presentation/                # Presentación ejecutiva PPTX/PDF y guion de 15 min
├── docs/                        # Guías y evidencias publicables
├── reports/                     # Informes locales, PDF fuera de Git
├── data/                        # Datos y checkpoints locales, fuera de Git
├── referencias_locales/         # Rúbrica y observaciones, fuera de Git
├── .env.example
└── README.md
```

Los datos no se versionan. Los archivos `.gitkeep` conservan la estructura de `data/` en Git sin subir CSV, Parquet, JSONL, bases SQLite ni checkpoints.

## Requisitos

- Python 3.12 recomendado.
- Java instalado y disponible en `PATH`, requerido por PySpark.
- Memoria y almacenamiento suficientes para procesar el archivo mensual de NYC TLC.

Las dependencias principales son PySpark 4.3, DuckDB 2.0, PyArrow, pandas y NumPy.

## Instalación

Las dependencias cloud se instalan en otro entorno; consultar [requirements/README.md](requirements/README.md).

Ejecute los comandos desde la raíz del proyecto:

```bash
python3.12 -m venv .venv_bigdata
source .venv_bigdata/bin/activate
python -m pip install --upgrade pip
pip install -r requirements/local.txt
python scripts/setup_local.py
```

En Windows, la activación del entorno cambia por:

```powershell
.venv_bigdata\Scripts\Activate.ps1
```

## Fuentes de datos

El ejercicio `pipelines/local/etl_medallion.py` descarga automáticamente el catálogo de zonas y los viajes amarillos de enero de 2024 de NYC TLC. Si no encuentra las otras fuentes, genera muestras sintéticas compatibles con ese ejercicio.

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

Estas fuentes deben descargarse o copiarse localmente después de clonar el repositorio. No están incluidas en Git. El ETL medallón es un ejercicio independiente: sus fuentes sintéticas no sustituyen los archivos ni los catálogos requeridos por puentes y P2.

## Ejecución

### 1. ETL medallón y homologación espacial

Este ejercicio descarga NYC TLC, prepara las fuentes auxiliares y construye una tabla Gold horaria con Spark:

```bash
.venv_bigdata/bin/python pipelines/local/etl_medallion.py
```

También puede ejecutarse de forma interactiva con:

```bash
jupyter lab
```

### 2. Puentes batch y replay streaming

Requiere las fuentes originales indicadas anteriormente. Construye las tablas puente, procesa el replay de sensores con Spark Structured Streaming y genera el Gold de cinco minutos:

```bash
.venv_bigdata/bin/python pipelines/local/puentes_batch_streaming.py
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
.venv_bigdata/bin/python pipelines/local/hibrido.py batch
```

Iniciar el consumidor streaming en una terminal:

```bash
.venv_bigdata/bin/python pipelines/local/hibrido.py serve
```

Publicar 1,000 lecturas históricas desde otra terminal:

```bash
.venv_bigdata/bin/python pipelines/local/hibrido.py publish \
  --limit 1000 \
  --chunk-size 250 \
  --delay 1
```

Inyectar eventos de prueba válidos e inválidos:

```bash
.venv_bigdata/bin/python pipelines/local/hibrido.py inject
```

Consultar microbatches, rechazos y ventanas procesadas:

```bash
.venv_bigdata/bin/python pipelines/local/hibrido.py status
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

Consulte [docs/ejecucion_local.md](docs/ejecucion_local.md) para el contrato de eventos, reglas de validación y detalles operativos de la demostración híbrida.

La [guía de reorganización](docs/reestructuracion.md) relaciona las rutas anteriores con las actuales.
