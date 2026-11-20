# Actualización del tablero de monitoreo

Fecha: 20 de noviembre de 2026. Fuente de diseño: HTML compartido por el usuario.
El diseño, CSS y estructura HTML se conservaron. Solo se corrigió num(null) en JavaScript
para que datos ausentes se muestren como «—» y no como cero.

El archivo canónico es `api/static/index.html`, con copia en `consumer/index.html`.
El empaquetador de Cloud Build incluye api/app, requirements y api/static, sin datos ni referencias privadas.

Contrato: /health, /kpis, /latencia, /zonas, /eventos/por-minuto, /eventos/ultimo y /rechazos.
La ruta /ventanas no existe. Las rutas /api/* anteriores se conservan para los controladores.

Validación: dieciocho pruebas de contrato, parámetros, caché, reloj fresco y casos vacíos aprobadas.
La API desplegada devolvió 200 para todos los endpoints nuevos y 404 para /ventanas;
se comprobó respuesta de quince minutos ascendentes y reloj actualizado en cada respuesta.
Se revisó el diseño en Google Chrome usando la interfaz nativa, incluido ?demo=1 sin API.
La prueba streaming y cierre se registran en la evidencia JSON complementaria.

Una consulta compartida y caché de cuatro segundos sirven los seis endpoints. El gráfico
se rellena al responder para conservar el minuto actual incluso cuando cambia durante la caché.
El horizonte compartido es de sesenta minutos para el gráfico y de 24 horas para último evento;
los contadores usan sesión configurable de 120 minutos. Mantiene límite de 128 MiB facturables por job.
Esto no es un presupuesto monetario ni garantiza bajo escaneo al crecer las tablas.

Verificación de metadatos GCP: sensores_validos particionada por event_ts; rechazados es vista
sobre rechazados_raw, particionada por processed_at. No se recreó ni se cambió ninguna tabla.
No se cambió pipeline_beam.py: streaming escribe con STREAMING_INSERTS y batch con FILE_LOADS,
sin frecuencia de disparo streaming configurada. El buffering interno no garantiza escritura instantánea.

Para apreciar el movimiento se añadió la opción --visible-seconds 30 al controlador de demo:
publica un nuevo ID por segundo y dos fixtures de viajes como mensajes deliberadamente incompatibles
con el contrato de sensores, de modo que generan cuarentena. No equivale a procesar esos viajes
por el pipeline batch. Conserva un solo worker, límite de tiempo y cierre con drain.

El rótulo «Pipeline en vivo» del diseño original refleja endpoints disponibles, no un chequeo
operativo de Dataflow. El texto «duplicados e inválidos» tampoco cambia la política real:
los duplicados válidos se conservan en Silver y se deduplican en Gold. Ver definiciones en api/README.md.

Resultado real: 257 mensajes publicados en la prueba (incluye replay y controles); treinta IDs nuevos
para la ráfaga visible y dos fixtures inválidos. Se observó el crecimiento automático de barras azules
y naranjas, cambio de valores en la tarjeta y aumento de aceptadas de 185 a 215 durante la ráfaga.
El evento de control se observó en 1,35 s con el worker listo (un caso, no SLA).
Job finalizado en DRAINED, cero jobs activos y cero VMs al verificar. Evidencia estructurada en
[actualizacion_tablero.json](actualizacion_tablero.json). La página quedó pausada y el servidor temporal
de revisión en puerto 8081 se detuvo; el acceso al servicio Cloud Run continúa mediante el proxy 8080.
