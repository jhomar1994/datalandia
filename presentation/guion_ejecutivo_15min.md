# Lumina P3: guion ejecutivo de 15 minutos

12 diapositivas. Tiempo total: 15:00, incluida demo de 3:00.
La atribución de aportes individuales debe confirmarse con el equipo.

## 1. Lumina: resumen y equipo (00:00–00:30)

Presentar al equipo de la plantilla: Christian Cajusol, Hugo Ángeles, Jhomar Yurivilca y Francisco Meza. Explicar que es un prototipo académico de movilidad. Iniciar el controlador de streaming al comenzar la exposición desde una segunda terminal, siguiendo el guion de preparación. No ejecutar demo_e2e.py anticipadamente: ese script termina solo y podría cerrarse antes de la demo.

Fuentes: Plantilla del usuario; README.md; demo/README.md.

## 2. Resumen ejecutivo (00:30–01:30)

El objetivo es exponer datos procesados hacia una aplicación consumidora. La migración cubre el flujo de procesamiento y exposición, no una migración corporativa completa. El operador puede revisar zonas activas, calidad y el último evento. El beneficio de negocio es propuesto: no atribuir ahorros ni causalidad al prototipo.

Fuentes: README.md; docs/pipelines_p3.md; api/README.md.

## 3. Situación actual (01:30–02:30)

Responder a cada observación sin exagerar. La trazabilidad mejora con código, contratos, guías y evidencias. El repositorio público existe, pero el commit final debe publicarse antes de entregar. La prueba batch real usó 10.000 entradas y produjo viajes válidos en 255 zonas. Los sensores cubren once zonas. Un batch DONE es correcto; detener streaming después de una prueba es control de costos, pero no operación 24/7.

Fuentes: docs/revision_observaciones_p2.md; docs/evidencias/demo_final.json; docs/evidencias/actualizacion_tablero.json.

## 4. KPI (02:30–03:45)

Contabilidad: (8.459 + 1.541) / 10.000 = 100%. La tasa de aceptación 84,59% es un resultado de muestra, no una meta. La disponibilidad 1,35 s corresponde a un único evento con worker ya listo en el job lumina-p3-stream-20261120110633. No confundir con el KPI promedio del tablero ni incluirlo como percentil. La repetición serial del MERGE mantiene 8.459 viajes. El cierre verificado quedó en cero jobs y VMs. Las metas son de demo y no un SLA contractual.

Fuentes: docs/evidencias/demo_final.json; docs/evidencias/actualizacion_tablero.json; tests/test_bigquery_merge.py.

## 5. Tecnologías (03:45–04:30)

Explicar responsabilidades sin enumerar todos los servicios GCP. Terraform aprovisiona. El controlador Python opera Dataflow y cierra workers. Workflows comprueba conteos. Cloud Run sirve la API y el HTML desde el mismo origen, con autenticación IAM. No se usa Dataproc, Composer ni Kubernetes propio.

Fuentes: infra/terraform/; pipelines/cloud/pipeline_beam.py; api/app/; workflows/verificar.yaml.

## 6. Dependencias y alcance (04:30–05:30)

Las fuentes son reales pero su unión entre ciudades es simulada. Los eventos se desplazan al calendario 2024, mientras processed_at conserva tiempo real. El tablero usa processed_at para el gráfico y event_ts para la ventana histórica de zonas. Dependemos de internet e identidades GCP. El controlador local debe seguir abierto para vigilar el cierre. La partición de sensores es event_ts y no se migró sin autorización. No prometer forecast, Vertex, sensores físicos ni 24/7.

Fuentes: README.md; api/README.md; docs/evidencias/actualizacion_tablero.json.

## 7. Arquitectura (05:30–07:00)

Leer dos rutas que convergen en BigQuery. En batch se cargan archivos desde Storage y se consolida por MERGE transaccional serial. Streaming recibe replay por Pub/Sub y aplica validación antes de STREAMING_INSERTS. Silver conserva copias, Gold deduplica y excluye IDs conflictivos. La API usa vistas Gold y tablas recientes con máximo de 128 MiB por consulta y caché compartida. El navegador accede a la API desplegada en GCP mediante un proxy autenticado local: localhost no significa que el backend esté corriendo en la laptop. Vincular cada recurso con las horas y volúmenes de la estimación anual.

Fuentes: infra/terraform/; sql/bigquery/; api/README.md; costs/calculator.py.

## 8. Calculadora (07:00–08:30)

Estimación de planificación, no cotización ni factura. El escenario bajo demanda reserva diez horas mensuales de streaming y diez de batch. El continuo modela 730 horas de streaming con el mismo worker, sin garantizar capacidad o SLA. Ambos asumen 0,1 TiB de consultas, 10 GiB medios BigQuery, 2 GiB Pub/Sub, dos SECU por hora de streaming como supuesto NO VERIFICADO, reservas por discos, Storage, inserts, Cloud Run, build, imágenes y logging. El modelo aplica 30% de contingencia. Los importes anuales se calculan antes de redondear mensual, por eso pueden diferir unos centavos de 12 por el mensual mostrado. El tipo de cambio de S/4 por USD del archivo es supuesto, no cotización. La retención debe revisarse para sostener almacenamiento medio. El gasto real de Cloud Billing sigue NO VERIFICADO. No afirmar que S/50 cubre operación anual.

Fuentes: costs/calculator.py; costs/estimate.json; costs/README.md. Tarifas consultadas 20/11/2026: https://cloud.google.com/dataflow/pricing ; https://cloud.google.com/bigquery/pricing ; https://cloud.google.com/pubsub/pricing ; https://cloud.google.com/run/pricing .

## 9. Demo en vivo (08:30–11:30)

Preparación: seguir presentation/demo_15min.md. Al comenzar la exposición, otro integrante inicia scripts/run_dataflow.py en una terminal con límite de 15 minutos y archivo de stop nuevo. Publica el warmup preparado y comprueba su ID en la API antes de este bloque. No lanzar un segundo job. Minuto 0: mostrar job y su worker. Publicar los 62 mensajes preparados a un evento por segundo mientras el tablero se actualiza cada cinco segundos. Minuto 1: observar barras azules/naranjas y último ID, explicar ahora del servidor. Minuto 2: mostrar /eventos/ultimo y /eventos/por-minuto?min=15 en Swagger, y la cuarentena. Solicitar drain al terminar, continuar con resultados mientras cierra, verificar cero jobs/VMs al final. Si no está listo a tiempo, usar evidencia real guardada y declarar cualquier uso de modo simulado. El modo preparar/publicar/cerrar integrado en demo_e2e.py aún no está implementado: este guion utiliza los CLI existentes por separado.

Fuentes: demo/README.md; scripts/run_dataflow.py; pipelines/cloud/publicar_eventos.py; api/README.md; presentation/demo_15min.md.

## 10. Evidencias (11:30–12:30)

Las cifras pertenecen a ejecuciones documentadas y no deben compararse como si fueran una sola carga. Batch: 10.000 entradas y 255 zonas de origen válidas. Streaming: 257 mensajes incluyen 220 de replay, cinco controles, treinta eventos nuevos y dos fixtures inválidos. Muchos IDs históricos ya existían: no son 257 nuevas lecturas únicas. Durante la ráfaga el KPI pasó de 185 a 215. Dieciocho pruebas de API y contratos, más dos integraciones SQL de BigQuery documentadas aparte. Se revisó visualmente el modo real y el simulado en Chrome. El cierre quedó DRAINED y cero workers/VMs en el corte observado.

Fuentes: docs/evidencias/demo_final.json; docs/evidencias/actualizacion_tablero.json; tests/README.md.

## 11. Conclusiones (12:30–13:30)

Cerrar el argumento: se logró la exposición y el consumidor con una ruta real de extremo a extremo. La calidad y la idempotencia son decisiones centrales para confiar en los agregados. El presupuesto condicionó una prueba funcional de un worker. Detener el cómputo después de demostrarlo es una decisión operativa defendible, pero no reemplaza observabilidad y recuperación en producción. No prometer ahorros, SLA ni horizontalidad no medidos.

Fuentes: docs/evidencias/actualizacion_tablero.json; docs/revision_observaciones_p2.md.

## 12. Next steps (13:30–15:00)

Primero cerrar el entregable, sin afirmar que el código local ya está publicado. Compartir el enlace al commit final cuando se haga push. Distribuir la exposición entre los cuatro integrantes y confirmar aportes reales: no inventar autorías ni responsabilidades. La separación preparar/publicar/cerrar es una mejora pendiente del controlador integrado. Para producción hacen falta capacidad, retención por processed_at, alertas, recuperación automática y backend de estado compartido. Retomar el presupuesto y una cotización con mediciones. Finalizar comprobando que Dataflow y las VMs quedaron en cero.

Fuentes: README.md; docs/revision_observaciones_p2.md; costs/README.md; https://github.com/jhomar1994/datalandia.
