# Consumo del primer año de Lumina en GCP

Para una operación de movilidad con 500 unidades conectadas, la proyección base es
**USD 3.436,16 durante 365 días**, incluido un margen del 25 %. Equivale a USD 286,35
mensuales en promedio. Se recomienda redondear la partida anual a USD 3.500.

Región: **Iowa, us-central1**, como los servicios del proyecto. Tarifas públicas consultadas
el 20/11/2026. Es una proyección con parámetros reproducibles para contrastar con la
[calculadora de GCP](https://cloud.google.com/products/calculator), no una cotización guardada
en su interfaz ni la factura de `proyecto-datalandia`.
Se calcula a tarifa bruta, sin descuentos, créditos, franquicias gratuitas ni impuestos.

## Supuestos del negocio y de capacidad

Son hipótesis de planificación para una empresa, no estadísticas sectoriales ni volúmenes medidos.

| Parámetro | Hipótesis |
|---|---|
| Unidades de movilidad | 500, con 40 viajes diarios por unidad como promedio supuesto. |
| Batch | 20.000 viajes/día; un lote diario; 7,3 millones de entradas/año. |
| Streaming | Una lectura por unidad cada 15 segundos, durante todo el día: 33,33 eventos/s, 2,88 millones/día y 1.051,2 millones/año. |
| Tamaño | 1 KiB por viaje y por mensaje, incluidos los atributos facturables estimados. No se incluyen video, audio o imágenes. |
| Batch Dataflow | Dos n1-standard-1, cada uno con 1 vCPU y 3,75 GiB; treinta minutos presupuestados por lote, incluido arranque y escrituras. Son 365 horas-worker/año. |
| Streaming Dataflow | Un n1-standard-2, 2 vCPU y 7,5 GiB; 8.760 horas/año. Capacidad pendiente de validar con carga representativa. |
| Discos | 30 GiB por worker, Standard Persistent Disk. Si el tipo efectivo cambia, actualizar la tarifa. |
| BigQuery | Detalle lógico 90 días; staging 7 días; referencias 5 GiB; agregados retenidos el año, creciendo 2 GiB/mes. Factor de tamaño 1,05 para cuarentena y copias. |
| Storage | Archivos batch retenidos un año en Standard regional; 20 GiB medios adicionales de staging/temporales; 50.000 operaciones A y 200.000 B mensuales. |
| Tablero | Cinco usuarios, ocho horas/día, 22 días/mes, actualización cada treinta segundos; siete endpoints por ciclo. |
| API | 739.200 solicitudes/mes, duración facturable media supuesta de 0,5 s, 0,25 vCPU y 256 MiB, mínimo cero. Aproximadamente 102,67 horas-instancia facturables/mes. |
| Observabilidad y operación | 20 GiB de logs/mes, 30.000 pasos internos de Workflows/mes, tres jobs Scheduler y veinte builds de cinco minutos/mes; imágenes medias de 5 GiB. |
| Riesgos | Reserva de USD 10/mes para métricas, alertas y salida de red moderada; además, margen global del 25 %. |

La ventana batch presupuestada no es una duración medida ni una garantía de finalización.
Un worker continuo no acredita alta disponibilidad. La gestión remota del ciclo de vida, el
productor real y los contratos de las unidades requieren completar la adaptación productiva.

## Streaming Engine y consultas

La base utiliza facturación de Streaming Engine por datos procesados a **USD 0,018/GiB**,
con amplificación supuesta de tres veces la entrada. El factor incorpora pasos internos y
salidas; debe sustituirse por la métrica real. Son aproximadamente 250,63 GiB procesados/mes.
La [documentación de Streaming Engine](https://docs.cloud.google.com/dataflow/docs/streaming-engine)
indica que el cobro por recursos requiere activar una opción adicional. El lanzador del proyecto
no la especifica. La modalidad efectiva de la factura sigue NO VERIFICADO.

Si se adopta cobro SECU, se reemplaza esa partida por unidades consumidas × horas ×
USD 0,089; nunca se suman ambos modelos. No existe una equivalencia fija entre worker y SECU.
Los escenarios de dos o cuatro SECU/h son hipótesis de sensibilidad.

Para consultas, se supone un llenado de caché por ciclo de cada usuario: 105.600 ciclos/mes,
64 MiB leídos por la consulta compartida de streaming y 10 MiB por control batch; más 2 TiB/mes
para consolidaciones, mantenimiento y análisis. Total: **9,4524 TiB/mes**. No se descuenta
la caché de resultados de BigQuery ni la coincidencia de caché entre usuarios.

Este presupuesto exige particiones que permitan filtrar el tiempo de procesamiento,
retención y agregados de consumo materializados. **Esas mejoras no están aplicadas a las
tablas de la demo.** Hoy sensores se particiona por `event_ts`, el gráfico filtra `processed_at`
y Gold utiliza vistas. Ejecutar esas consultas sobre el histórico creciente puede superar el
límite de 128 MiB por job y producir errores; no debe extrapolarse su consumo como constante.
El tamaño de 64 MiB es una meta de dimensionamiento, no una medida del SQL actual.

## Estimación por componente

| Componente | USD al mes en promedio | USD primer año |
|---|---:|---:|
| Dataflow streaming, CPU y memoria | 120,21 | 1.442,57 |
| Streaming Engine por volumen | 4,51 | 54,14 |
| Dataflow batch, CPU y memoria | 2,11 | 25,31 |
| Discos Dataflow y shuffle batch | 1,24 | 14,94 |
| BigQuery consultas | 59,08 | 708,93 |
| BigQuery almacenamiento | 5,66 | 67,97 |
| BigQuery streaming inserts | 4,49 | 53,89 |
| Pub/Sub, publicación y entrega | 6,53 | 78,32 |
| Cloud Storage y operaciones | 0,80 | 9,60 |
| Cloud Run, API y consumidor | 2,74 | 32,93 |
| Cloud Logging | 10,00 | 120,00 |
| Cloud Build y Artifact Registry | 1,10 | 13,20 |
| Workflows y Scheduler | 0,59 | 7,13 |
| Reserva de Monitoring y red | 10,00 | 120,00 |
| **Subtotal** | **229,08** | **2.748,93** |
| **Margen del 25 %** | **57,27** | **687,23** |
| **Presupuesto** | **286,35** | **3.436,16** |

Los totales se calculan antes de redondear. El almacenamiento se integra desde cero a lo
largo del primer año, no como doce veces el stock final: BigQuery promedia 246,26 GiB y
Storage 23,48 GiB. El volumen acumulado de entrada no equivale al almacenamiento retenido.
Los vCPU/memoria de Dataflow ya incluyen el cómputo de sus VMs: no sumar Compute Engine.
La entrada batch a BigQuery usa cargas de archivos, sin cargo de inserción streaming.
Pub/Sub contabiliza una publicación y una entrega por evento; se supone entrega dentro
de un día, sin retención de mensajes reconocidos y recursos en la misma región.

## Sensibilidad del presupuesto

Cada fila cambia solo los parámetros indicados respecto de la base; no implica capacidad validada.

| Escenario | USD primer año con margen |
|---|---:|
| Base: un worker streaming y cobro por volumen | 3.436,16 |
| Dos workers streaming, mismo volumen | 5.257,12 |
| Un worker streaming, cobro alternativo de 2 SECU/h | 5.317,59 |
| Dos workers streaming y cobro alternativo de 4 SECU/h | 9.087,65 |
| Base con refresco del tablero cada 5 s | 7.135,29 |

El escenario de refresco cada cinco segundos supone suficientes instancias API para la carga;
no afirma que el máximo actual de una instancia pueda atenderla. Nuevas instancias reducen
el beneficio de caché compartida. Tampoco modela un pico simultáneo como carga promedio.

Con el supuesto editable **S/4 por USD**, la base equivale a **S/13.744,64/año**. No es una
cotización cambiaria. Para dos workers streaming se recomienda presupuestar aproximadamente
USD 5.500/año bajo facturación por volumen, y recalcular si cambia el modelo de Streaming Engine.

Quedan fuera personal, hardware y conectividad de sensores, licencias externas, capacitación,
soporte empresarial, recuperación en otra región y un segundo entorno completo. Los beneficios
gratuitos podrían reducir la factura si están disponibles; no se ha verificado su consumo por cuenta.

## Tarifas y reproducción

Tarifas de lista y parámetros, no una cotización negociada:

- [Dataflow](https://cloud.google.com/dataflow/pricing): batch USD 0,056/vCPU-h; streaming 0,069/vCPU-h; memoria 0,003557/GiB-h; discos 0,000054/GiB-h; shuffle batch 0,011/GiB.
- [BigQuery](https://cloud.google.com/bigquery/pricing): USD 6,25/TiB consultado; almacenamiento lógico activo 0,000031507/GiB-h; inserts REST 0,01/200 MiB, con mínimo por fila. El modelo conserva `STREAMING_INSERTS`.
- [Pub/Sub](https://cloud.google.com/pubsub/pricing): USD 40/TiB de publicación y entrega, antes de franquicias.
- [Storage](https://cloud.google.com/storage/pricing): Standard Iowa 0,000027397/GiB-h; clase A 0,005/1.000 operaciones y clase B 0,0004/1.000.
- [Cloud Run](https://cloud.google.com/run/pricing): cobro por solicitudes, USD 0,000024/vCPU-s, 0,0000025/GiB-s y 0,40/millón de solicitudes.
- [Logging](https://cloud.google.com/products/observability/pricing): USD 0,50/GiB, incluidos treinta días de retención.
- [Cloud Build](https://cloud.google.com/build/pricing): e2-standard-2, USD 0,006/minuto. [Artifact Registry](https://cloud.google.com/artifact-registry/pricing): USD 0,000136986/GiB-h.
- [Workflows](https://cloud.google.com/workflows/pricing): USD 0,01/1.000 pasos internos, antes de franquicias. [Scheduler](https://cloud.google.com/scheduler/pricing): USD 0,10/job/31 días.

```bash
python3 costs/enterprise_calculator.py --output costs/enterprise_estimate.json
```

Los supuestos se modifican en `Assumptions` de `enterprise_calculator.py`. El resultado JSON
incluye tarifas, consumos, subtotal y escenarios. Para contrastar en la calculadora, usar los
promedios mensuales de consumo: 730 horas streaming, 30,42 horas-worker batch, 83,54 GiB
de publicación y la misma entrega, 9,4524 TiB consultados y 246,26 GiB medios de BigQuery.
Mantener región us-central1 y distinguir tarifas brutas de descuentos/franquicias automáticos.
