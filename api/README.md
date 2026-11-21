# API y tablero Lumina

FastAPI consulta BigQuery y sirve el nuevo consumidor en `/`. Fuente canónica:
`api/static/index.html`; `consumer/index.html` es una copia para revisión y respaldo.
Cloud Run `lumina-api`, us-central1, autenticación IAM y cuenta de servicio de solo lectura.

## Contrato vigente

| GET | Respuesta |
|---|---|
| `/health` | `status, proyecto, dataset, ultima_ingesta`; conserva `project, simulation` por compatibilidad. No hace consultas; última ingesta es null. |
| `/kpis` | `aceptadas, rechazadas, recibidas, latencia_e2e_s, latencia_meta_s, zonas_activas, ultima_ingesta` |
| `/batch/ultimo` | `batch_id, estado, entradas, validos, rechazados, zonas, consolidado, workers_solicitados, iniciado, actualizado, dataflow_job_id`; sin ejecuciones registradas: HTTP 200 y `{}`. |
| `/latencia` | `etapas: [{nombre, servicio, segundos}], total_s` |
| `/zonas` | `ventana_inicio, ventana_fin, zonas: [{zona_id, lecturas, viajes, importe_km, valor_medio, unidad}]` |
| `/eventos/por-minuto?min=15` | `minutos: [{minuto, aceptadas, rechazadas}]`; entre 1 y 60, ascendente, exactamente min filas con ceros; último minuto en curso. |
| `/eventos/ultimo` | `event_id, zona_id, node_id, sensor, parameter, value, unit, published_at, processed_at, latencia_s, ahora`; sin eventos responde HTTP 200 y `{}`. |
| `/rechazos?limit=5` | `rechazos: [{processed_at, motivo, detalle}]`; limit entre 1 y 50, orden descendente, detalle de hasta 80 caracteres. |
| `/docs` | Swagger/OpenAPI. |

No existe la ruta de ventanas antigua. Se conservan `/api/zones`, `/api/metrics`, `/api/quality`
y `/api/events/{id}` para el controlador de demo anterior y trazabilidad de conflictos (HTTP 409).
Los parámetros antiguos mantienen validación de zona, periodo máximo de 31 días y límite de filas.
Fechas UTC en JSON, valores numéricos como números y ausencia de medición como null.

## Definiciones y límites

El bloque batch lee `batch_ejecuciones`, una tabla de control aprovisionada con Terraform.
`demo_batch.py` registra las entradas esperadas y las transiciones observadas por el controlador.
Tras `DONE`, los válidos y zonas se cuentan en staging por `batch_id`; los rechazos por ID único
en `rechazados_raw`, con filtro de inicio de ejecución. Los conteos permanecen null mientras
no se hayan calculado; cero significa un conteo observado de cero. La consolidación solo se
marca tras completar el MERGE. Los válidos no equivalen a nuevas inserciones: puede haber IDs
preexistentes. Los workers son solicitados, no una medida de trabajo distribuido.
La última ejecución se elige por inicio, incluso si falló o fue cancelada. El controlador local
debe permanecer activo para actualizar el estado; una caída abrupta puede dejarlo desactualizado.
El timestamp visible permite detectar esto. No se afirma que sea monitoreo independiente de la laptop.
Este endpoint tiene caché propia de cuatro segundos y consulta limitada a 128 MiB.
El consumidor consulta ahora siete endpoints por ciclo; los seis originales conservan su consulta compartida.

Sesión por `processed_at`, últimos 120 minutos por defecto. Aceptadas: IDs únicos de sensores,
con primera recepción dentro del horizonte de consulta de 24 h y sin conflictos conocidos en Gold.
Rechazadas: filas de la vista `rechazados`, que deduplica por rejection_id; incluye fuentes batch y sensores.
Recibidas = aceptadas + rechazadas: es el total lógico mostrado, no un contador de entregas Pub/Sub.
Los duplicados válidos se conservan en Silver y se excluyen de Gold, no se envían a cuarentena.
El texto del HTML «duplicados e inválidos» describe posibilidades del diseño; no implica que este pipeline rechace duplicados.

La serie por minuto usa processed_at real, con deduplicación de aceptadas y ceros. La caché comparte
un horizonte de sesenta minutos para atender cualquier min entre 1 y 60; usa el mismo corte y sesión
que el resto de indicadores, y rellena nuevamente al responder si cambió el minuto.

`/zonas` usa la ventana MÁS RECIENTE existente en `gold_zona_5min` (event_ts histórico 2024).
Suma lecturas, conserva viajes/importes una vez por zona mediante MAX y calcula SUM(total_usd)/SUM(distance_km)
en su granularidad original. El parámetro representativo es temperature por defecto: promedio ponderado
por lecturas, sin mezclar unidades; si hay varias, usa la unidad con más lecturas. Sin dato devuelve null.
Zonas activas del KPI se cuentan en la sesión por processed_at: su horizonte difiere de la tabla histórica.

`/eventos/ultimo` selecciona la última fila válida de Silver dentro de 24 h, incluida una copia repetida
o un ID que después tenga conflicto. Esto respeta ORDER BY processed_at DESC sobre sensores_validos;
no equivale al último ID canónico de Gold. La zona viene del puente, con null si no tiene asociación.
Latencia del evento = (processed_at − published_at) con precisión de microsegundos.
`ahora` usa reloj UTC del servidor, se recalcula siempre y no se almacena en caché.

Latencia KPI = promedio(processed_at − published_at) de lecturas deduplicadas procesadas en cinco minutos
+ duración observada de la consulta compartida. Si no hay muestra reciente es null.
El desglose usa ese promedio, el tiempo real de la consulta (incluye transporte del cliente BigQuery)
y preparación medida del handler, sin atribuir tiempos ficticios a etapas individuales.
El dato de consulta procede del último llenado de caché; no se finge ejecutar una consulta en cada hit.
No mide latencia exacta hasta pintar el navegador ni incluye arranque del worker, polling, serialización completa
ni tránsito de la respuesta HTTP. El KPI de disponibilidad del controlador se registra por separado.

## Costo, particiones y escritura

Los seis endpoints comparten UNA consulta BigQuery y una caché con bloqueo, TTL por defecto 4 s.
Esto evita seis jobs separados por ciclo. Se mantiene maximum_bytes_billed de 128 MiB por job,
caché BigQuery y timeout. No es un tope monetario global. Al crecer tablas o abrir muchas pestañas,
revisar frecuencia y planes de consulta. API privada, mínimo cero, máximo una instancia, 0,25 vCPU/256 MiB.

`sensores_validos` está particionada por **event_ts**, no processed_at; por tanto el filtro temporal
real por sí solo no poda sus particiones. `rechazados` es una vista; `rechazados_raw` está particionada
por processed_at, pero su deduplicación puede limitar la poda efectiva. No se recrearon tablas.
Migrar a processed_at requeriría una tabla nueva y migración explícita, previa confirmación.

Pipeline streaming: **STREAMING_INSERTS**, sin triggering_frequency configurado; Beam hace buffering
interno, no se promete flush por mensaje ni latencia fija. Batch: FILE_LOADS para lote finito.
No se modificó el método ni frecuencia. No hace falta cambiar a Storage Write API para esta demo funcional.

Variables: `LUMINA_PROJECT_ID`, `LUMINA_DATASET`, `LUMINA_REGION`, `LUMINA_MAX_BYTES_BILLED`,
`VENTANA_SESION_MIN=120`, `CACHE_TTL_S=4`, `LATENCIA_META_S=60`, `PARAMETRO_SENSOR=temperature`.
Autenticación ADC local y cuenta de servicio en Cloud Run. No descargar llaves ni desactivar TLS.

## Acceso y prueba

```bash
gcloud run services proxy lumina-api --project=proyecto-datalandia --region=us-central1 --port=8080
curl 'http://127.0.0.1:8080/eventos/por-minuto?min=15'
curl 'http://127.0.0.1:8080/eventos/ultimo'
```

Abrir `http://127.0.0.1:8080/` para datos reales y `http://127.0.0.1:8080/?demo=1` para el modo simulado.
El badge «Pipeline en vivo» del diseño significa que respondieron los endpoints; no comprueba que Dataflow
esté encendido. Revisar el tiempo «hace X» y el estado del job para verificar actividad real.
El modo demo está rotulado y funciona sin API; las fuentes web pueden caer y se usan fuentes del sistema.

Para desarrollo:

```bash
python3.12 -m venv .venv_api
.venv_api/bin/pip install -r api/requirements.txt
.venv_api/bin/uvicorn api.app.main:app --host 127.0.0.1 --port 8081
.venv_api/bin/python -m unittest tests.test_monitoring tests.test_api tests.test_cloud_contracts -v
```

Para construir: `.venv_api/bin/python scripts/build_api.py`; solo empaqueta API y api/static.
El digest queda en `referencias_locales/api_build/image.txt`. Actualizar api_image en el tfvars ignorado,
revisar plan Terraform (solo imagen del servicio) y aplicar. No se habilita allUsers.
