# Speech para cuatro integrantes del equipo Lumina

Guion literal para las doce diapositivas de la presentación ejecutiva. Duración objetivo: **15 minutos**, incluidos **3 minutos de demostración**. Los relevos respetan los tiempos de las diapositivas. Las indicaciones entre corchetes son acciones y pausas: **no se leen**.

La duración requiere ensayo con cronómetro. El bloque de demo tiene menos texto para permitir publicar, navegar y observar. No acelerar para llenar un bloque: dejar que la profesora vea la evidencia.

| División | Diapositivas | Horario | Duración |
|---|---|---|---|
| Integrante 1 | 1 a 4 | 00:00–03:45 | 3 min 45 s |
| Integrante 2 | 5 a 8 | 03:45–08:30 | 4 min 45 s |
| Integrante 3 | 9, con pantalla de demo | 08:30–11:30 | 3 min |
| Integrante 4 | 10 a 12 | 11:30–15:00 | 3 min 30 s |

## Preparación que no se lee

- Confirmar antes de sustentar que el commit final esté publicado en GitHub. No afirmar que el código local ya está publicado si falta el push.
- Seguir `presentation/demo_15min.md`. Al comenzar la exposición, una persona que no está hablando inicia el controlador y publica el warmup. La disponibilidad de ese ID en la API confirma que el worker está preparado antes del minuto 08:30.
- Mantener listas las pestañas de Dataflow, tablero y Swagger. El consumidor debe estar conectado a la API real, sin `?demo=1`.
- El integrante 3 dirige la demo. Otra persona puede ejecutar comandos para que no se pierda tiempo escribiendo.
- Al terminar la demo, solicitar drain y mantener las terminales abiertas. Verificar el cierre durante los bloques siguientes. No afirmar cero jobs o cero VMs sin comprobarlo.
- El guion asigna temas para sustentar. No atribuye autoría del código ni aportes individuales que no estén confirmados.

## Integrante 1

**00:00–03:45. Diapositivas 1 a 4.**

### Diapositiva 1 — Presentación — 00:00–00:30

“Buen día, profesora y compañeros. Presentamos Lumina, un prototipo de monitoreo operativo que integra información de movilidad y sensores en Google Cloud.

Nuestro objetivo es mostrar que un dato puede ingresar al pipeline, pasar por controles de calidad y quedar disponible para una aplicación consumidora. Durante la exposición veremos la arquitectura, sus resultados y una demostración funcional.”

[Cambiar a la diapositiva 2. Otra persona inicia la preparación de Dataflow.]

### Diapositiva 2 — Resumen ejecutivo — 00:30–01:30

“El problema que abordamos es la fragmentación de la información. Los viajes y las lecturas de sensores llegan con estructuras y referencias temporales distintas, lo que dificulta consultarlos de manera consistente.

Lumina propone reunirlos mediante validaciones, homologación y agregaciones por zona. Así, un operador puede revisar actividad, reconocer lecturas que necesitan atención y consultar qué ocurrió con un evento.

El alcance de esta implementación comprende el paso del procesamiento local a servicios de GCP, desde la ingesta hasta BigQuery, una API y un tablero. El resultado que defendemos es la integración técnica del flujo. El impacto económico de las decisiones que podría apoyar todavía requiere una evaluación de negocio.”

[Señalar las tres partes del alcance y cambiar a la diapositiva 3.]

### Diapositiva 3 — Situación actual y correcciones de P2 — 01:30–02:30

“Para esta entrega tomamos como punto de partida las observaciones de la parte dos.

En trazabilidad, organizamos el código de pipelines, SQL, infraestructura y API, con instrucciones de ejecución y evidencias que permiten revisar el resultado más allá de una captura.

En cobertura, ampliamos la validación cloud: la muestra batch produjo viajes válidos en doscientas cincuenta y cinco zonas, y el flujo de sensores cubrió once zonas.

En operación, incorporamos un controlador con duración máxima y cierre verificable. Un batch que termina correctamente cumple su propósito; el streaming se mantiene activo durante la prueba y luego se cierra por presupuesto. La operación continua con recuperación automática sigue siendo una evolución pendiente.”

[Señalar la diferencia entre correcciones realizadas y pendientes. Cambiar a la diapositiva 4.]

### Diapositiva 4 — KPI — 02:30–03:45

“Definimos cuatro criterios de éxito que podemos contrastar con evidencia.

Primero, la contabilidad del lote: de diez mil entradas, ocho mil cuatrocientas cincuenta y nueve fueron válidas y mil quinientas cuarenta y una quedaron rechazadas. Ambas salidas explican el cien por ciento de las entradas. Esto demuestra trazabilidad, aunque existan datos de mala calidad.

Segundo, la disponibilidad del evento. La meta de demo es hasta sesenta segundos con el worker preparado. En una prueba, un evento estuvo disponible en la API en uno coma treinta y cinco segundos. Es una medición puntual, no un percentil ni una garantía de producción, y excluye el arranque del worker.

Tercero, repetir la consolidación serial mediante MERGE no aumentó los viajes canónicos. Cuarto, comprobamos el cierre con cero jobs activos y cero máquinas virtuales.

A continuación explicamos las decisiones técnicas que sostienen estos resultados.”

[Relevo al integrante 2 al minuto 03:45.]

## Integrante 2

**03:45–08:30. Diapositivas 5 a 8.**

### Diapositiva 5 — Productos tecnológicos — 03:45–04:30

“Seleccionamos los servicios por la función que cumplen en el flujo.

Cloud Storage conserva archivos y catálogos. Pub/Sub recibe los mensajes de sensores. Apache Beam define las transformaciones y Dataflow las ejecuta en GCP. BigQuery almacena los resultados y expone las vistas analíticas.

FastAPI y Cloud Run conectan esos datos con el tablero. Terraform permite reproducir la infraestructura. Workflows verifica conteos; actualmente no administra el reinicio ni la recuperación de los jobs. El ciclo de la demostración lo controla nuestro lanzador.”

[Cambiar a la diapositiva 6.]

### Diapositiva 6 — Dependencias y alcance — 04:30–05:30

“Para interpretar los resultados debemos distinguir las fuentes reales de las asociaciones simuladas.

Utilizamos viajes TLC de dos mil veinticuatro, sensores AoT de dos mil dieciocho y referencias históricas. Sin embargo, la correspondencia entre territorios y el desplazamiento de fechas son decisiones académicas. No representan equivalencias geográficas reales.

También diferenciamos el tiempo del evento y el tiempo de procesamiento. El primero permite consultar el escenario histórico; el segundo permite observar actividad que está llegando ahora.

Esta versión depende de conectividad e identidades GCP. La prueba usa un worker y no incluye sensores físicos, forecast ni alta disponibilidad. Hemos probado integración funcional; medir capacidad masiva requiere una prueba de carga adicional.”

[Cambiar a la arquitectura y señalar primero la ruta batch.]

### Diapositiva 7 — Arquitectura — 05:30–07:00

“La arquitectura tiene dos rutas que convergen en BigQuery.

En batch, los archivos ingresan desde Storage y Dataflow aplica las reglas de validación. Los registros válidos pasan por staging y una consolidación mediante MERGE. Los inválidos conservan el motivo del rechazo en cuarentena. Repetir la consolidación serial con el mismo identificador y contenido mantiene una sola fila canónica.

En streaming, el publicador envía mensajes a Pub/Sub. Dataflow valida el contrato y escribe los resultados en BigQuery mediante streaming inserts.

Silver conserva las recepciones para trazabilidad. Gold deduplica los eventos y excluye de los agregados los identificadores que tienen contenidos conflictivos. Además, separamos movilidad y sensores para evitar multiplicar viajes o importes al cruzar varias métricas.

La API consulta esos resultados y alimenta el tablero. Aunque accedemos mediante un proxy en la laptop, el backend está desplegado en Cloud Run y consulta BigQuery con su cuenta de servicio.

Para esta demo limitamos cada job a un worker, usamos discos de treinta gigabytes y evitamos IP públicas. Cloud Run escala entre cero y una instancia. Estos recursos y sus tiempos de uso forman la base de nuestra estimación.”

[Recorrer las dos rutas, BigQuery y el consumidor. Cambiar a la diapositiva 8.]

### Diapositiva 8 — Calculadora de consumo — 07:00–08:30

“Separaremos el presupuesto de la demostración del costo de operar la arquitectura durante un año.

El presupuesto acordado para pruebas y demo es de cincuenta soles. El gasto facturado debe contrastarse con Cloud Billing y no lo presentamos como cero ni como una cifra ya verificada.

Para el primer año construimos dos escenarios. Bajo demanda, con diez horas mensuales de streaming, el modelo estima aproximadamente ciento sesenta y cinco dólares anuales. Con streaming continuo, modelando setecientas treinta horas mensuales, estima aproximadamente cuatro mil treinta y siete dólares anuales.

Ambos consideran diez horas mensuales de batch, consultas, almacenamiento y tráfico. Incorporan reservas para otros servicios y treinta por ciento de contingencia. El consumo de Streaming Engine todavía necesita calibración, por lo que estas cifras son preliminares.

La principal decisión de costo es cuánto tiempo mantenemos el streaming encendido. Por eso operamos bajo demanda y verificamos el cierre. Esta configuración tampoco demuestra que un worker pueda sostener cualquier carga: el dimensionamiento requiere mediciones adicionales.

Ahora mostraremos el recorrido de un evento hasta la aplicación consumidora.”

[Relevo al integrante 3 al minuto 08:30.]

## Integrante 3

**08:30–11:30. Diapositiva 9 y pantallas de la demostración.**

### Primer minuto — Publicación — 08:30–09:30

[Mostrar Dataflow y el tablero. Confirmar previamente que el warmup llegó a la API. Reanudar el tablero y ejecutar la publicación preparada en `presentation/demo_15min.md`.]

“El worker ya está preparado: comprobamos que un evento de calentamiento llegó hasta la API.

Estamos usando la conexión real con GCP. Los mensajes son de prueba, pero recorren Pub/Sub, Dataflow, BigQuery y Cloud Run.

Ahora publicamos sesenta lecturas válidas y dos deliberadamente inválidas, aproximadamente a un mensaje por segundo. Cada evento tiene un identificador nuevo para distinguir esta ejecución de las anteriores.”

[Dar tiempo a la publicación. Señalar las barras y la tarjeta mientras cambian. No abrir otro job.]

### Segundo minuto — Actualización del consumidor — 09:30–10:30

“El tablero consulta la API automáticamente cada cinco segundos. Las barras azules representan lecturas aceptadas y las naranjas, registros rechazados.

Este gráfico usa el tiempo real de procesamiento, por eso permite observar el movimiento durante la demo. La tabla de zonas utiliza la última ventana histórica disponible y puede permanecer estable.

La tarjeta muestra el último evento, su valor y la diferencia entre publicación y procesamiento. El contador ‘hace cuánto’ utiliza el reloj del servidor. Esa latencia de procesamiento es distinta del tiempo completo hasta que el navegador muestra el dato.”

[Mostrar `/eventos/ultimo` y `/eventos/por-minuto?min=15` en Swagger. Mostrar el rechazo no numérico.]

### Tercer minuto — Evidencia y cierre — 10:30–11:30

“La respuesta JSON permite comprobar que el tablero consume una API y no valores escritos en la página. El registro inválido conserva su motivo en cuarentena, separado de las lecturas válidas.

Con esto verificamos la conexión de extremo a extremo: publicación, procesamiento, persistencia y consumo.

Solicitamos el cierre mediante drain para completar el trabajo en tránsito. Mientras termina, revisaremos las evidencias. El cierre se confirma consultando el estado del job y la ausencia de máquinas virtuales.”

[Crear el archivo de parada indicado en el runbook. Continuar la exposición mientras GCP libera recursos. Relevo al integrante 4 al minuto 11:30.]

## Integrante 4

**11:30–15:00. Diapositivas 10 a 12.**

### Diapositiva 10 — Evidencias — 11:30–12:30

“Además de la demostración, conservamos resultados de pruebas documentadas.

El batch procesó diez mil entradas. En otra ejecución streaming publicamos doscientos cincuenta y siete mensajes, incluyendo replay, controles e inválidos. Esa cifra no representa doscientas cincuenta y siete lecturas únicas nuevas, porque parte del replay ya existía.

En la ráfaga visible observamos que las aceptadas pasaron de ciento ochenta y cinco a doscientas quince. También verificamos el cambio de la tarjeta y las barras de aceptadas y rechazadas.

Completamos dieciocho pruebas de contratos y API, además de dos integraciones SQL en BigQuery. Probamos que un duplicado no se sume dos veces en Gold y que un identificador con contenidos conflictivos quede excluido de los agregados.”

[Señalar las evidencias y cambiar a la diapositiva 11.]

### Diapositiva 11 — Conclusiones — 12:30–13:30

“La primera conclusión es que la capa de exposición forma parte del flujo implementado: la aplicación consulta datos que pasaron por procesamiento en GCP.

La segunda es que la calidad de los agregados depende de decisiones explícitas sobre identidad, validación y reintentos. Conservar evidencia en Silver y separar cuarentena permite explicar lo aceptado, lo rechazado y lo excluido de Gold.

La tercera es que el control del consumo debe incorporarse a la operación. Encender recursos para demostrar el caso y cerrarlos después es adecuado para este prototipo.

El siguiente paso hacia producción exige probar volumen, concurrencia, continuidad y recuperación. La muestra demuestra factibilidad técnica, pero todavía no permite prometer capacidad masiva ni un nivel de servicio.”

[Cambiar a la diapositiva 12. Otra persona comprueba el cierre en GCP.]

### Diapositiva 12 — Next steps — 13:30–15:00

“Nuestras siguientes acciones tienen tres prioridades.

Primero, cerrar la trazabilidad del entregable: el código y sus instrucciones deben quedar asociados a un commit final verificable en GitHub, junto con las evidencias de las ejecuciones. Eso permite auditar y repetir el proyecto desde el repositorio.

Segundo, ampliar la validación: procesar el archivo completo, medir carga y concurrencia, revisar las particiones según las consultas reales y definir retención. Con esas mediciones podremos ajustar la estimación de consumo y el dimensionamiento.

Tercero, fortalecer la operación con alertas, recuperación, automatización del ciclo de vida y un estado Terraform compartido. También queremos integrar de forma más sencilla la preparación, publicación y cierre de la demo.

El resultado que presentamos conecta infraestructura reproducible, procesamiento con controles de calidad y una aplicación consumidora. Las siguientes iteraciones deben ampliar esa evidencia hacia una operación de mayor escala.”

[Reservar los últimos segundos para una de las dos frases siguientes. Leer solo la que corresponda al estado comprobado.]

**Si ambas listas están vacías:**

“Finalmente, confirmamos que no quedan jobs Dataflow activos ni máquinas virtuales en el proyecto. Con esto cerramos la demostración y quedamos atentos a sus preguntas. Muchas gracias.”

**Si el cierre aún está en progreso:**

“El cierre está solicitado y todavía está en progreso. Mantendremos la vigilancia hasta confirmar que no quedan jobs ni máquinas virtuales. Quedamos atentos a sus preguntas. Muchas gracias.”

## Respaldo si la demo falla

Este texto sustituye la narración de resultados en vivo. No se suma a los quince minutos:

“En este momento no estamos obteniendo la confirmación necesaria para mostrar el flujo en vivo. Para respetar el tiempo, mostraremos la evidencia de una ejecución real anterior. Si abrimos el modo simulado del tablero, lo indicaremos expresamente: sus valores son de demostración y no prueban una ejecución actual de Dataflow.”

[No afirmar que se observaron datos nuevos si la pantalla no lo confirma. Mostrar la evidencia guardada y continuar al minuto 11:30.]

## Enfoque de sustentación

El énfasis responde a la rúbrica compartida y a las observaciones P2: exposición mediante API, recorrido end-to-end, repositorio auditable, cobertura y operación verificable. No supone preferencias adicionales de la docente.

Evitar afirmar que el sistema ya procesa masivamente, que ofrece un SLA, que mantiene operación continua automática o que su gasto real es cero. Los aportes individuales deben explicarse según el trabajo real de cada integrante.
