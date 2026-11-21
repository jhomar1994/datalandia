# Primer año con redundancia de procesamiento y archivos replicados

El presupuesto es **USD 5.749,79/año**, incluido un margen del 25 %, con tarifas brutas
de lista y sin impuestos, créditos ni franquicias gratuitas. Equivale a USD 479,15/mes
en promedio. Para planificación, redondear a USD 6.000/año.

Es una arquitectura proyectada para producción. No modifica ni describe como ya desplegada
la configuración de la demo. El escenario anterior sin esta redundancia permanece en
[primer_ano_empresa.md](primer_ano_empresa.md).

## Supuestos de negocio y redundancia

| Elemento | Supuesto del presupuesto |
|---|---|
| Carga | 500 unidades; 20.000 viajes batch/día; una lectura por unidad cada quince segundos, equivalente a 2,88 millones de eventos/día. Tamaño medio facturable de 1 KiB. |
| Región de procesamiento | us-central1, con dos zonas distintas para los jobs streaming. Tarifas consultadas el 20/11/2026. |
| Redundancia streaming | Dos jobs independientes activos-activos, un n1-standard-2 por job (2 vCPU y 7,5 GiB), 24/7. No son dos workers repartiendo una sola carga: ambos procesan toda la entrada. |
| Mensajería | Un topic y dos suscripciones independientes, una por job. Una publicación y dos entregas por evento; retención de no reconocidos de 24 h. Las réplicas zonales internas del servicio no se cobran como nuevas suscripciones. |
| BigQuery | Un dataset regional. La redundancia zonal gestionada por BigQuery está incluida en la tarifa. No se presupuestan dos datasets ni una réplica regional adicional. |
| Recepciones duplicadas | Ambos jobs escriben en Silver; el modelo cuenta dos recepciones físicas por evento y dos escrituras facturables. Gold deduplica por identidad y contenido. El almacenamiento lógico medio sube a 473,82 GiB por esas copias de aplicación, no por la redundancia zonal interna. |
| Replicación de archivos | Solo el archivo batch permanente pasa a Storage Standard dual-region nam4, que abarca us-central1 y us-east1. Temporales/staging permanecen regionales. La tarifa suma los componentes de ambas regiones y el tráfico de replicación. |
| Batch | Dos n1-standard-1 durante treinta minutos diarios. Un único job batch; recuperación mediante reintento idempotente, sin duplicar permanentemente su procesamiento. |
| API | Cloud Run regional administrado, mínimo cero y máximo uno como base. La disponibilidad gestionada del servicio no se representa como una segunda VM facturada manualmente. Se conserva la carga total de solicitudes y tiempo activo estimados. |
| Retención y consultas | Detalle 90 días, staging 7 días y archivos batch un año. Cinco usuarios, 8 h/día, 22 días/mes y refresco cada 30 s. Se mantienen 9,4524 TiB/mes de consultas como objetivo tras materializar agregados y optimizar particiones. No es una medición del SQL de la demo. |
| Observabilidad | Logs aumentan de 20 a 40 GiB/mes. La reserva de métricas, alertas y red sube de USD 10 a USD 15/mes. |
| Streaming Engine | Facturación por datos procesados: factor tres sobre la entrada de cada job. Los dos jobs suman aproximadamente 501,25 GiB procesados/mes; no se agrega SECU al mismo cálculo. |
| Alcance de continuidad | Redundancia de procesamiento frente a fallas zonales y archivo batch replicado. No se promete conmutación automática de toda la plataforma ante pérdida total de us-central1 ni RPO/RTO garantizados. |

La [documentación de Dataflow](https://docs.cloud.google.com/dataflow/docs/guides/pipeline-workflows)
describe el uso de pipelines paralelos y suscripciones independientes para tolerancia a fallos.
Ambos deben desplegarse efectivamente en zonas distintas: aumentar workers por sí solo no
garantiza esa separación. Se necesitan pruebas de fallos y monitoreo de la salud de cada job.

BigQuery [mantiene copias en dos zonas dentro de la ubicación](https://docs.cloud.google.com/bigquery/docs/reliability-intro).
Se cobra el volumen lógico de las tablas de acuerdo con el modelo elegido; no multiplicar
el precio por la cantidad de copias internas del servicio.

## Costos ordenados de mayor a menor

| Recurso | USD/mes promedio | USD/año |
|---|---:|---:|
| Dataflow streaming, CPU y memoria de dos jobs | 240,43 | 2.885,15 |
| BigQuery consultas | 59,08 | 708,93 |
| Cloud Logging | 20,00 | 240,00 |
| Reserva de Monitoring y red | 15,00 | 180,00 |
| BigQuery almacenamiento | 10,90 | 130,77 |
| Pub/Sub, una publicación y dos entregas | 9,79 | 117,48 |
| Streaming Engine de dos jobs | 9,02 | 108,27 |
| BigQuery inserciones streaming de dos jobs | 8,98 | 107,79 |
| Cloud Run, API y consumidor | 2,74 | 32,93 |
| Discos Dataflow y shuffle batch | 2,43 | 29,13 |
| Dataflow batch, CPU y memoria | 2,11 | 25,31 |
| Cloud Storage dual-region, temporales y operaciones | 1,15 | 13,74 |
| Cloud Build y Artifact Registry | 1,10 | 13,20 |
| Workflows y Scheduler | 0,59 | 7,13 |
| **Subtotal** | **383,32** | **4.599,83** |
| **Margen del 25 %** | **95,83** | **1.149,96** |
| **Presupuesto total** | **479,15** | **5.749,79** |

Los recursos se ordenan por importe anual; subtotal y margen no son recursos y se muestran
al pie. Los cálculos usan valores sin redondear. A S/4 por USD como supuesto, el total es
aproximadamente **S/23.000/año**; no es una cotización de tipo de cambio.

## Tarifas adicionales y límites del modelo

Los componentes regionales conservan las [tarifas del escenario base](primer_ano_empresa.md#tarifas-y-reproducción).
En [Cloud Storage](https://cloud.google.com/storage/pricing), el almacenamiento dual-region
se factura por ambas regiones subyacentes: 2 × USD 0,000030137/GiB-h para el archivo.
La replicación estándar de nam4 cuesta USD 0,02/GiB escrito; las operaciones A son
USD 0,01/1.000. Se presupuesta esa tarifa A para las 50.000 operaciones mensuales del modelo.
No se duplica otra vez el volumen físico al aplicar la tarifa compuesta de almacenamiento.

Esta propuesta no utiliza la función Dataflow Streaming High Availability en Preview,
que requiere cobro por recursos. Utiliza dos jobs ordinarios con su propia suscripción.
Si se adopta aquella función o cambia el cobro a SECU, reemplazar la partida de Engine.

La réplica de archivos no es un backup inmutable contra borrado o corrupción. Versionado,
retención bloqueada y restauraciones requerirían política y capacidad adicionales. Tampoco
se incluye una réplica cross-region de BigQuery: esa función cobra almacenamiento y tráfico
adicional y tiene limitaciones de promoción durante una caída regional completa. Una
estrategia DR regional integral requiere diseño y presupuesto aparte.

## Reproducir el cálculo

```bash
python3 costs/enterprise_calculator.py --output costs/enterprise_estimate.json
```

El escenario `redundancia_zonal_y_archivo_dual` contiene los parámetros y el detalle.
Usa 17.520 horas-worker de streaming anuales, dos copias de recepciones de sensores,
tres flujos Pub/Sub por evento y una única carga de consultas analíticas optimizadas.
No se ha guardado una cotización en la interfaz de la calculadora ni desplegado estos recursos.
