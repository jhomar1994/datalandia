# Bloque de última ejecución batch

## Resultado principal actualizado: un millón

El 21/11/2026 se ejecutó y consolidó `lumina-p3-scale-20261121050254-fc9795`:
1.000.000 de entradas, 937.453 válidas, 62.547 rechazos, 255 zonas válidas y dos VMs
del job observadas. El endpoint `/batch/ultimo` sirve este resultado real.
La API y los demás endpoints se comprobaron con HTTP 200 conservando el límite de 128 MiB.
Ver [detalle y reproducción](batch_1m.md) y [consultas y métricas](batch_1m.json).

Las secciones siguientes describen el despliegue inicial y las pruebas anteriores;
sus conteos de 10.000 no representan la última ejecución.

Despliegue verificado el 20/11/2026 (Lima), revisión Cloud Run `lumina-api-00004-vlb`.
Imagen: `us-central1-docker.pkg.dev/proyecto-datalandia/lumina-images/lumina-api@sha256:9767b982af89535afa686f149b3e9389e58691a2de8364181e2f828a54f48e9b`.
Cloud Build: `79b31bf1-686b-42ba-aaf6-8acc0f6957f1`, `SUCCESS`.

Terraform creó solo `batch_ejecuciones` y actualizó únicamente la imagen de Cloud Run.
Se mantienen autenticación IAM y configuración de recursos. No se iniciaron jobs Dataflow.

El endpoint `/batch/ultimo` devolvió `{}` con HTTP 200 antes de registrar datos. Se comprobó
el job histórico `lumina-p3-batch-20261120093854` en Dataflow, estado `JOB_STATE_DONE`,
ID `2026-11-20_01_39_13-17840352199966583616`. Se contrastaron conteos en BigQuery y la
presencia de los IDs y hashes de staging en `viajes_validos`, antes de incorporar su resumen.

Resultado servido por la API desplegada:

| Campo | Valor |
|---|---:|
| Entradas de la prueba histórica | 10.000 |
| Válidos únicos del batch | 8.459 |
| Rechazos únicos del batch | 1.541 |
| Zonas de origen válidas | 255 |
| Consolidado | Sí |
| Workers solicitados de aquella prueba | 1 |

Los dos workers son la configuración predeterminada de la próxima demo batch, no una
característica atribuida retroactivamente al job histórico. Cada demo nueva reemplaza
la tarjeta como última ejecución según su inicio, conservando el historial en la tabla.

Validaciones: 21 pruebas API/contratos/monitoreo y nueve de demos/controladores, correctas.
JavaScript: sintaxis correcta. Se verificó HTTP 200 en `/batch/ultimo`, `/health`, `/`
y `/eventos/por-minuto?min=15`; la serie conserva quince elementos. El HTML desplegado
incluye el bloque y su llamada API. Consumidor canónico y copia son idénticos.
En aquella verificación no estuvo disponible el navegador. La revisión visual se completó
posteriormente el 20/11/2026 mediante Chrome, con la API real y la consola de GCP.

Al finalizar se comprobaron cero jobs Dataflow activos en us-central1 y cero VMs del proyecto.
El bloque usa siete endpoints por ciclo: los seis de streaming conservan su consulta compartida;
batch añade una consulta pequeña a su registro con caché de cuatro segundos y límite por job.
El modo `?demo=1` conserva datos simulados y un ejemplo batch explícitamente bajo ese modo.

## Prueba posterior de dos workers

Job `lumina-p3-scale-20261121013943-6fad30`, ID Dataflow
`2026-11-20_17_40_13-14018000482179640194`, región `us-central1`:
`JOB_STATE_DONE`, dos workers `n1-standard-1` configurados, disco de 30 GB por worker,
sin IP pública. La API muestra 10.000 entradas, 8.459 válidos, 1.541 rechazos,
255 zonas válidas y consolidación completada. El controlador registró 278 segundos;
la consola muestra 4 min 15 s de ejecución del job: son intervalos diferentes.
Esta prueba acredita funcionalidad con dos workers, no rendimiento masivo ni escalamiento lineal.

El informe final conserva capturas reales y las salidas de consultas en su paquete editable
local, bajo `output/pdf/` (ignorado por Git). Las credenciales y los estados Terraform no
forman parte de las evidencias publicables.
