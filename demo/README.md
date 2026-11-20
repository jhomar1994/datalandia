# Demo P3 bajo demanda

Preparar autenticación, Terraform y entradas según `docs/pipelines_p3.md`.
Presupuesto acordado para pruebas y demo: S/50. Gasto facturado: NO VERIFICADO.
No dejar Dataflow encendido entre sesiones.

## Batch

La prueba realizada procesó 10.000 registros y terminó en `JOB_STATE_DONE`.
El URI de la muestra está en `docs/evidencias/demo_final.json`.

```bash
.venv_beam/bin/python scripts/run_dataflow.py --mode batch --input gs://BUCKET/RUTA/viajes.jsonl --max-minutes 12
.venv_beam/bin/python scripts/finalize_batch.py --batch-id NOMBRE_DEL_JOB_TERMINADO
```

Reemplazar los placeholders. Consolidar solo un job terminado correctamente.
La repetición serial del MERGE no vuelve a sumar viajes con el mismo ID y contenido.

## Streaming y consumidor

Abrir el proxy autenticado en una terminal:

```bash
gcloud run services proxy lumina-api --project=proyecto-datalandia --region=us-central1 --port=8080
```

Desde la raíz, en otra terminal:

```bash
.venv_beam/bin/python scripts/demo_e2e.py --visible-seconds 30
```

El script inicia un worker privado `n1-standard-2`, Streaming Engine y disco de 30 GB.
Publica 220 eventos históricos, veinte por cada uno de once nodos. Espera su aparición en la API;
publica cinco mensajes de control: evento válido repetido, dos versiones conflictivas y un inválido.
La opción --visible-seconds 30 añade treinta eventos nuevos, uno por segundo, y los dos fixtures de viajes
como entrada inválida para el contrato de sensores. Así se observan barras azules/naranjas y cambia la tarjeta.
Genera un ID nuevo por ejecución y guarda mensajes, respuestas y tiempos en
`referencias_locales/demo/FECHA/`, fuera de Git. El controlador limita la sesión a doce minutos.

Durante la sustentación:

1. Mostrar el job en ejecución y su worker único en GCP.
2. Abrir `http://127.0.0.1:8080`. El nuevo tablero no necesita seleccionar zona ni fecha: muestra actividad por processed_at real y la última ventana histórica Gold.
3. Observar «Lecturas recibidas por minuto» y «Último evento»: la barra azul crece, aparece naranja y la tarjeta cambia de ID.
4. Mostrar las respuestas `/eventos/ultimo` (incluye ahora del servidor) y `/eventos/por-minuto?min=15` en Swagger o curl.
5. Explicar que Silver conserva copias y Gold deduplica; un ID conflictivo devuelve HTTP 409.
6. Mostrar el rechazo `valor_no_numerico` y su trazabilidad en BigQuery.
7. Esperar el cierre y verificar los recursos liberados.

El bloque de cierre solicita drain incluso si falla la comprobación. Si tarda más de dos minutos,
solicita cancelación, que puede dejar mensajes pendientes. La vigilancia depende de que el proceso
local siga activo; no garantiza apagado ante una caída del equipo.

## Comprobar el cierre

```bash
gcloud dataflow jobs list --project=proyecto-datalandia --region=us-central1 --status=active --format='table(id,name,state)'
gcloud compute instances list --project=proyecto-datalandia --format='table(name,status,machineType)'
```

Ambas listas deben quedar vacías. Ante una interrupción, identificar el job de esta demo y ejecutar
`gcloud dataflow jobs cancel ID --project=proyecto-datalandia --region=us-central1` y volver a comprobar.
Detener el proxy con Ctrl+C y cerrar el tablero. Se conservan datos e imagen para relanzar mañana.

Esta prueba acredita integración funcional; la capacidad masiva, operación 24/7 y SLA quedan pendientes.


El HTML nuevo actualiza seis endpoints cada cinco segundos. Pausar con el botón del tablero para evitar
consultas mientras se explica. El contador «hace X s» usa el reloj del servidor y avanza cada segundo.
Para el respaldo sin API, abrir la misma página con `?demo=1`: se rotula claramente como simulado.
No presentar esos valores simulados como resultados reales.

La tabla de zonas usa event_ts histórico y puede permanecer en otra zona/ventana; el gráfico por minuto
y la tarjeta usan processed_at actual y son la evidencia de movimiento. Los duplicados históricos del replay
pueden no incrementar el KPI; los IDs nuevos de la ráfaga sí lo hacen.
