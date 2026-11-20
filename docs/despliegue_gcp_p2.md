# Demostración GCP de Lumina en P2

Registro histórico de la demostración P2 del 8 de noviembre de 2026 en `datalandia`, región `us-central1`, con aprovisionamiento manual. Los comandos siguientes corresponden a ese proyecto anterior. El destino previsto de P3 es `proyecto-datalandia`; consultar [infraestructura Terraform](../infra/terraform/README.md).

| Servicio | Recurso actual |
|---|---|
| Cloud Storage | `gs://datalandia-lumina-prototipo` |
| Pub/Sub topic | `lumina-eventos` |
| Pub/Sub suscripción | `lumina-streaming` |
| BigQuery | `datalandia.lumina_demo` |
| Cuenta de servicio Dataflow | `lumina-dataflow@datalandia.iam.gserviceaccount.com` |
| Cuenta anterior para API | `lumina-api@datalandia.iam.gserviceaccount.com` |

Los recursos de esta tabla corresponden a la demostración histórica, no a una verificación del estado actual. La sección final registra los resultados de la prueba. Los comandos de creación no son idempotentes.

## 1. Requisitos y proyecto

Necesitas Google Cloud CLI (`gcloud` y `bq`), una cuenta autenticada, permisos para crear recursos y facturación habilitada. Configura alertas de presupuesto antes de ejecutar cómputo: las alertas por sí solas no detienen gastos.

```bash
gcloud version
bq version
gcloud auth list
```

Si no tienes sesión iniciada, utiliza `gcloud auth login`. No compartas tokens, claves ni datos de pago. Define variables para tu sesión y confirma el proyecto:

```bash
LUMINA_PROJECT_ID="datalandia"
LUMINA_REGION="us-central1"
LUMINA_BUCKET="datalandia-lumina-prototipo"

gcloud projects describe "$LUMINA_PROJECT_ID" --format='table(projectId,projectNumber,name)'
gcloud billing projects describe "$LUMINA_PROJECT_ID" --format='yaml(projectId,billingEnabled)'
```

Para otro proyecto, cambia las variables. Los nombres de buckets son globales: elige uno único y válido. Continúa si `billingEnabled` es `true`.

## 2. APIs

Las APIs principales ya estaban habilitadas en el proyecto actual. Para comprobar otro proyecto:

```bash
gcloud services list --enabled --project="$LUMINA_PROJECT_ID" --format='table(config.name)'
```

Si faltan y tienes autorización para habilitarlas:

```bash
gcloud services enable \
  dataflow.googleapis.com bigquery.googleapis.com pubsub.googleapis.com \
  storage.googleapis.com iam.googleapis.com compute.googleapis.com \
  --project="$LUMINA_PROJECT_ID"
```

## 3. Crear recursos en un proyecto nuevo

Los siguientes comandos crean un bucket con acceso uniforme y prevención de acceso público. No alteran automáticamente la configuración del bucket anterior:

```bash
gcloud storage buckets create "gs://${LUMINA_BUCKET}" \
  --project="$LUMINA_PROJECT_ID" \
  --location="$LUMINA_REGION" \
  --uniform-bucket-level-access \
  --public-access-prevention
```

Crea el topic y una suscripción con retención de mensajes de un día:

```bash
gcloud pubsub topics create lumina-eventos --project="$LUMINA_PROJECT_ID"

gcloud pubsub subscriptions create lumina-streaming \
  --project="$LUMINA_PROJECT_ID" \
  --topic=lumina-eventos \
  --message-retention-duration=1d
```

Crea el dataset y la cuenta de servicio:

```bash
bq --project_id="$LUMINA_PROJECT_ID" mk --dataset --location="$LUMINA_REGION" \
  "${LUMINA_PROJECT_ID}:lumina_demo"

gcloud iam service-accounts create lumina-dataflow \
  --project="$LUMINA_PROJECT_ID" \
  --display-name="Lumina Dataflow worker"
```

La cuenta no obtiene automáticamente los permisos del pipeline. Antes de ejecutar Dataflow, concede permisos mínimos al worker y autorización al ejecutor para usar esa cuenta. No es necesario crear ni descargar claves privadas. Los nombres y la separación de las futuras tablas Silver, Gold y cuarentena todavía deben definirse.

## 4. Verificación

```bash
gcloud storage buckets describe "gs://${LUMINA_BUCKET}" \
  --format='yaml(name,location,uniform_bucket_level_access,public_access_prevention,soft_delete_policy)'

gcloud pubsub topics describe lumina-eventos --project="$LUMINA_PROJECT_ID"

gcloud pubsub subscriptions describe lumina-streaming \
  --project="$LUMINA_PROJECT_ID" \
  --format='yaml(name,topic,messageRetentionDuration)'

bq --project_id="$LUMINA_PROJECT_ID" ls
bq --project_id="$LUMINA_PROJECT_ID" ls "${LUMINA_PROJECT_ID}:lumina_demo"

gcloud iam service-accounts describe \
  "lumina-dataflow@${LUMINA_PROJECT_ID}.iam.gserviceaccount.com" \
  --project="$LUMINA_PROJECT_ID"

gcloud dataflow jobs list --project="$LUMINA_PROJECT_ID" --region="$LUMINA_REGION" \
  --format='table(id,name,state)'
```

Confirma ubicación, acceso y política de eliminación reversible del bucket, relación topic-suscripción y estado de los jobs. Puede haber jobs anteriores cancelados o fallidos. Los objetos retenidos y recursos activos pueden generar cargos.

## Demostración ejecutada: 8 de noviembre de 2026

- Muestras en `gs://datalandia-lumina-prototipo/muestras/`, generadas por `pipelines/cloud/preparar_muestras.py`: 1.000 viajes, 1.000 lecturas, 1.000 personas, 8 destinos Uber y puentes/referencia para la zona simulada `DL-132`. La referencia demográfica proviene de la agregación v1 completa de 2017; las 1.000 personas no representan la población total. Los datos AoT de 2018 se reproducen en la ventana de 2024 y conservan la fecha original.
- `pipelines/cloud/pipeline_beam.py`: Dataflow batch valida viajes y Dataflow streaming consume Pub/Sub, valida sensores y escribe válidos/rechazados en `lumina_demo`. Se incluyen dos viajes inválidos sintéticos y un sensor inválido sintético para verificar cuarentena. Los 1.000 viajes de muestra provienen de un archivo previamente filtrado.
- Batch `lumina-batch-muestra-1108`: terminado; 1.000 viajes válidos.
- Streaming `lumina-stream-muestra-1108`: procesó 1.020 eventos válidos recibidos, de los que 1.000 son IDs únicos; los primeros 20 se volvieron a publicar para comprobar deduplicación de la vista Gold. El job se cancela tras la demostración para limitar costos.
- `lumina_demo.rechazados`: 3 eventos inválidos de prueba (dos viajes y un sensor). Los duplicados permanecen en Silver y **no se registran en cuarentena**: la vista Gold los deduplica por `event_id`; los casos de IDs conflictivos y deduplicación persistente en la ingesta quedan pendientes.
- `sql/bigquery/gold_zona_5min.sql` define la vista `lumina_demo.gold_zona_5min`: sensores agrupados por zona/ventana/sensor/unidad unidos a viajes de la misma zona/ventana y a la referencia histórica. Cada fila es una métrica por sensor; los totales de viajes se repiten entre sensores y no deben sumarse sin agrupar previamente. La latencia que muestra mide publicación a procesamiento Beam, no publicación a disponibilidad en BigQuery.
- `lumina-verificar` en Workflows ejecuta una consulta de conteos de BigQuery, y su definición está en `workflows/verificar.yaml`. Es un control manual bajo demanda, **no inicia ni detiene Dataflow** y todavía no constituye la orquestación completa. Para iniciar jobs desde Workflows se necesita, por ejemplo, una plantilla Flex y un workflow que la invoque; debe gestionarse aparte el inicio y fin del streaming.
- Ambos jobs se limitaron a un worker `n1-standard-1`, con la VPC `lumina-dataflow-net`, subnet `lumina-dataflow-subnet`, Private Google Access y sin IP pública. La cuenta `lumina-dataflow` tiene `roles/dataflow.worker` y `roles/bigquery.jobUser` en el proyecto; acceso de objetos al bucket; acceso de suscriptor a `lumina-streaming`; y acceso WRITER al dataset. La cuenta `lumina-orquestador` tiene `roles/bigquery.jobUser` en el proyecto y READER del dataset.
- El dataset `lumina_demo` tenía una expiración predeterminada de **48 horas para tablas nuevas**; revisar las fechas de expiración en BigQuery y capturar o exportar la evidencia antes de que venza. No se cambió esa configuración.

Para consultar los resultados:

```bash
bq --project_id=datalandia query --location=us-central1 --use_legacy_sql=false \
  'SELECT * FROM `datalandia.lumina_demo.gold_zona_5min` WHERE viajes IS NOT NULL LIMIT 20'

bq --project_id=datalandia query --location=us-central1 --use_legacy_sql=false \
  'SELECT source, reason, COUNT(*) total FROM `datalandia.lumina_demo.rechazados` GROUP BY 1,2'

gcloud workflows run lumina-verificar --project=datalandia --location=us-central1
gcloud dataflow jobs list --project=datalandia --region=us-central1 --format='table(id,name,state)'
```

Reejecutar `pipelines/cloud/publicar_eventos.py` vuelve a publicar los mismos IDs; Gold los deduplica, aunque Silver acumula copias. Los dos scripts Beam se ejecutan con el entorno aislado `.venv_beam` (Apache Beam 2.71.0), y la preparación de muestras utiliza DuckDB en `.venv_bigdata`. Antes de volver a ejecutar cualquier job, revisa costos, tablas existentes y estado de los workers; batch escribe en modo append, por lo que repetirlo duplicaría viajes.

Las rutas de código indicadas son relativas a la raíz del repositorio. Las dependencias cloud están en `requirements/cloud.txt`.
