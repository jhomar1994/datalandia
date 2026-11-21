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

La entrega pública incluye código, contratos, SQL, Terraform y guías. La prueba principal procesó 1.000.000 entradas reales y produjo 937.453 válidas y 62.547 rechazos en 255 zonas, con dos VMs observadas. La fuente abarca 260 códigos de origen; los inválidos explican la menor cobertura válida. El streaming abarca once zonas. Se mitiga la muestra reducida con cien veces más volumen cloud; todavía faltan comparaciones controladas de escalamiento y recuperación 24/7.

Fuentes: docs/evidencias/batch_1m.json; docs/revision_observaciones_p2.md.

## 4. KPI (02:30–03:45)

Conciliación: (937.453 + 62.547) / 1.000.000 = 100%. Se contrastaron IDs distintos y filas físicas. La duración Dataflow fue 324,595 s; el controlador, 352 s. El rendimiento bruto 3080,8 entradas/s incluye arranque y cargas BigQuery, excluyendo MERGE posterior. Repetir MERGE conservó 937.453 viajes y USD 24.490.375,32. El evento streaming de control del 20/11 tardó 11,006 s con worker preparado; no es p95 ni SLA. Se comprobó cero jobs/VMs al cierre.

Fuentes: docs/evidencias/batch_1m.json; informe final, evidencia streaming del 20/11/2026.

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

La proyección empresarial usa 500 sensores con un evento de 1 KiB cada quince segundos, veinte mil viajes diarios y batch de dos workers durante treinta minutos al día. El millón de esta prueba es una carga puntual y no reemplaza ese supuesto diario. El escenario con un job streaming 24/7 y archivo regional estima USD 3.436,16 al año. La propuesta redundante tiene dos jobs en zonas distintas, dos suscripciones y archivo nam4; estima USD 5.749,79 al año, incluida contingencia del 25%. No está desplegada. No se promete recuperación regional completa. Sin impuestos, créditos ni descuentos. La factura real sigue NO VERIFICADO.

Fuentes: costs/enterprise_estimate.json; costs/primer_ano_redundancia.md; tarifas oficiales enlazadas en esos archivos.

## 9. Demo en vivo (08:30–11:30)

Preparación: seguir presentation/demo_15min.md. Al comenzar la exposición, otro integrante inicia scripts/run_dataflow.py en una terminal con límite de 15 minutos y archivo de stop nuevo. Publica el warmup preparado y comprueba su ID en la API antes de este bloque. No lanzar un segundo job. Minuto 0: mostrar job y su worker. Publicar los 62 mensajes preparados a un evento por segundo mientras el tablero se actualiza cada cinco segundos. Minuto 1: observar barras azules/naranjas y último ID, explicar ahora del servidor. Minuto 2: mostrar /eventos/ultimo y /eventos/por-minuto?min=15 en Swagger, y la cuarentena. Solicitar drain al terminar, continuar con resultados mientras cierra, verificar cero jobs/VMs al final. Si no está listo a tiempo, usar evidencia real guardada y declarar cualquier uso de modo simulado. El modo preparar/publicar/cerrar integrado en demo_e2e.py aún no está implementado: este guion utiliza los CLI existentes por separado.

Fuentes: demo/README.md; scripts/run_dataflow.py; pipelines/cloud/publicar_eventos.py; api/README.md; presentation/demo_15min.md.

## 10. Evidencias (11:30–12:30)

Batch principal: 1.000.000 entradas, 937.453 válidas, 62.547 rechazos, 255 zonas, dos VMs observadas y DONE. Los conteos están filtrados por batch_id. Streaming del 20/11: 287 mensajes incluyen 220 de replay, cinco controles, sesenta eventos nuevos y dos fixtures inválidos; no son 287 lecturas únicas nuevas. Se confirmó el último ID y las barras de aceptadas/rechazadas. Hay veintiuna pruebas de API/contratos y nueve de controladores registradas, además de integraciones SQL reales. El reproceso del millón volvió a comprobarse en BigQuery sin filas nuevas.

Fuentes: docs/evidencias/batch_1m.json; docs/evidencias/tablero_batch.md; tests/README.md.

## 11. Conclusiones (12:30–13:30)

Se conectaron ingesta, procesamiento en GCP y consumidor. La calidad y la idempotencia permiten auditar el resultado. La evidencia batch amplía el volumen a un millón con dos workers y mediciones explícitas. Esto no permite afirmar escalamiento lineal ni capacidad productiva garantizada. La ejecución bajo demanda y el cierre acotan consumo; la operación continua y la recuperación automática siguen pendientes.

Fuentes: docs/evidencias/batch_1m.json; docs/revision_observaciones_p2.md.

## 12. Next steps (13:30–15:00)

La siguiente etapa consiste en validar cargas representativas y comparar el mismo lote con uno y dos workers; definir retención y objetivos de servicio; implementar orquestación administrada, alertas, recuperación y CI/CD. Mantener trazabilidad por commit y evidencia de cada ejecución. La propuesta redundante del presupuesto requiere implementación y pruebas de fallos. Cerrar comprobando jobs y VMs, y confirmar las contribuciones individuales con el equipo.

Fuentes: docs/evidencias/batch_1m.json; costs/primer_ano_redundancia.md; docs/revision_observaciones_p2.md.
