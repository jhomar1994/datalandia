# Prueba batch de un millón de viajes en GCP

Configuración de la entrega: un millón de viajes reales, dos workers y máximo de treinta minutos.
Consultar la evidencia fechada de la ejecución para sus resultados; el comando por sí solo no los acredita.
La ejecución del 21/11/2026 terminó en `DONE`: 937.453 válidos, 62.547 rechazados,
255 zonas válidas y dos VMs observadas. [Resultados y límites](evidencias/batch_1m.md).
Objetivo: aumentar el volumen cloud frente a las 10.000 entradas anteriores y observar trabajo
en dos workers. Un millón de filas por sí solo no acredita escala productiva ni aceptación de la docente.

## Ejecución simplificada

Con los requisitos de abajo disponibles, toda la secuencia se ejecuta desde la raíz con:

```bash
.venv_beam/bin/python scripts/demo_batch.py --records 1000000 --workers 2 --max-minutes 30
```

Este comando genera consumo en GCP. Prepara un millón de viajes (o reutiliza la carpeta
local si su manifiesto tiene el conteo esperado), valida hashes al subir, ejecuta dos workers
durante un máximo solicitado de treinta minutos y consolida únicamente después de `DONE`.
Comprueba ausencia de cómputo antes y al terminar. No reemplaza las referencias BigQuery
ni el reporte de staging de la demo habitual. Mantener la laptop y la terminal activas.
Los reportes quedan en `referencias_locales/escala/NOMBRE/resultado.json`.
Una ejecución fallida no se relanza automáticamente. Antes de repetir, revisar sus logs.

El contador de workers del reporte es solicitado; guardar las métricas reales de GCP para
acreditar distribución. Los conteos de calidad por batch_id y la facturación se revisan después.
Las secciones siguientes documentan los pasos individuales para diagnóstico.

Ejecutar desde la raíz. Requiere fuentes y salidas locales previas, ADC, cuotas para dos workers
y el estado Terraform del proyecto `proyecto-datalandia`. La vigilancia depende de la laptop activa.

## 1. Preparación local

```bash
.venv_bigdata/bin/python -m pipelines.cloud.preparar_muestras --trip-limit 1000000 --sensor-limit 11000 --output data/p3/escala_1m
```

La carpeta debe ser nueva: el preparador no sobrescribe entradas existentes. Revisar
`data/p3/escala_1m/manifest.json`: `counts.viajes` debe ser 1.000.000. El comando simplificado
usa por defecto `data/p3/demo_batch_1000000/`; ambas rutas deben tener su propio manifiesto. Los viajes se seleccionan
sin prevalidar; no multiplicar filas artificialmente. Datos y manifiesto permanecen fuera de Git.

## 2. Subida a Storage

Este paso utiliza GCP y puede generar consumo. No reemplaza referencias BigQuery:

```bash
.venv_beam/bin/python scripts/stage_inputs.py --input data/p3/escala_1m --report referencias_locales/escala_1m/staging.json
```

El reporte independiente conserva la configuración de la demo anterior. Copiar su valor
`uris["viajes.jsonl"]` y sustituir `URI_GCS_DEL_REPORTE` en el siguiente comando.
Los objetos se versionan por hash. No añadir `--load-references` para esta prueba.

## 3. Ejecución con dos workers

Comprobar antes que no haya jobs activos y confirmar presupuesto disponible. Ejecutar:

```bash
.venv_beam/bin/python scripts/run_dataflow.py --mode batch --input URI_GCS_DEL_REPORTE --workers 2 --max-minutes 30 --staging-report referencias_locales/escala_1m/staging.json
```

Configuración: dos `n1-standard-1` fijos, disco de 30 GB por worker, IP privada,
`autoscaling_algorithm=NONE`. El máximo admitido en batch es 45 minutos y tres workers;
el valor predeterminado sigue siendo un worker y doce minutos. Streaming conserva sus límites.
El plazo incluye envío y arranque. Al vencer se solicita cancelación y se espera confirmación;
no es una garantía de terminación instantánea ni un límite monetario.

Guardar el nombre del job y observar en GCP los workers realmente creados y sus métricas de
trabajo. `workers_requested=2` en el reporte es configuración solicitada, no prueba de que
ambos procesaron datos. No prometer que dos workers duplican el rendimiento: el arranque,
el paralelismo de entrada y las cargas BigQuery también influyen.

## 4. Consolidación y evidencia

Solo si terminó en `JOB_STATE_DONE`, consolidar serialmente:

```bash
.venv_beam/bin/python scripts/finalize_batch.py --batch-id NOMBRE_DEL_JOB_TERMINADO
```

La entrada comparte identidades con muestras anteriores: el MERGE incorpora viajes nuevos
y conserva los existentes. El total acumulado de `viajes_validos` no equivale a los aceptados
de este job. Para calidad usar `viajes_staging` y `rechazados_raw` filtrados por el `batch_id`
de la prueba y contrastar con el manifiesto. Registrar filas y IDs distintos para advertir copias
debidas a reintentos. No estimar aceptados restando el total global de tablas.

Registrar entrada exacta y bytes, cobertura, válidos/rechazos, duración total y duración
`RUNNING`, throughput con denominador explícito, workers observados, utilización y estado final.
Para comparar rendimiento, repetir la misma entrada con uno y dos workers en sesiones separadas;
comparar 10.000 con un millón no permite atribuir una mejora al número de workers.
El reporte del controlador queda en `referencias_locales/dataflow/NOMBRE/result.json`.

Verificar el cierre:

```bash
gcloud dataflow jobs list --project=proyecto-datalandia --region=us-central1 --status=active
gcloud compute instances list --project=proyecto-datalandia
```

Las listas deben quedar vacías. Si el controlador cayó, seguir la cancelación por ID descrita
en [demo/README.md](../demo/README.md). Revisar Cloud Billing antes de repetir pruebas;
el presupuesto total acordado es S/50 y el consumo acumulado sigue NO VERIFICADO.
No se garantiza duración o costo a partir del número de registros.

Publicar únicamente evidencia revisada y sin credenciales en `docs/evidencias/`, después
de la ejecución. Actualizar slides y onboarding con resultados observados, sin sustituir
las mediciones anteriores por estimaciones.
