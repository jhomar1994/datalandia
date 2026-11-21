# Esquema actualizado de la sustentación P3

Duración: **15 minutos**, doce diapositivas, con tres minutos de demo streaming.
El [guion ejecutivo](guion_ejecutivo_15min.md) contiene las notas de cada diapositiva;
el [speech para cuatro integrantes](speech_4_integrantes_15min.md) contiene la narración literal.

| Diapositiva | Contenido principal |
|---|---|
| 1 | Presentación del proyecto y equipo. |
| 2 | Resumen ejecutivo, alcance y valor propuesto. |
| 3 | Observaciones P2: código auditable, un millón en cloud, continuidad pendiente. |
| 4 | Conciliación 100 %, rendimiento bruto 3.080,8 entradas/s, control streaming 11,006 s, reproceso sin filas nuevas y cierre. |
| 5 | Storage, Pub/Sub, Beam/Dataflow, BigQuery, FastAPI/Cloud Run, Terraform y Workflows. |
| 6 | Fuentes históricas, homologación simulada y límites del ensayo. |
| 7 | Batch con dos workers y streaming con uno, convergencia en BigQuery y exposición. |
| 8 | Escenarios empresariales: USD 3.436,16/año base y USD 5.749,79 con redundancia propuesta. |
| 9 | Demo streaming real: publicar, observar gráfico y último evento, comprobar y cerrar. |
| 10 | Evidencia batch: 1.000.000 entradas, 937.453 válidos, 62.547 rechazos y 255 zonas. |
| 11 | Factibilidad técnica, calidad y límites de escalamiento/continuidad. |
| 12 | Evolución a producción: cargas representativas, orquestación, alertas, recuperación y CI/CD. |

El job Dataflow del millón duró 324,595 s; el controlador, 352 s. El rendimiento incluye
arranque y cargas BigQuery, sin el MERGE posterior. Dos VMs observadas no prueban reparto
uniforme ni escalamiento lineal. Repetir el MERGE mantuvo 937.453 viajes y USD 24.490.375,32.

El batch se ejecuta antes de sustentar; se muestra su job DONE y la tarjeta consolidada.
Luego se prepara streaming. El controlador impide jobs simultáneos. Mostrar en vivo
Pub/Sub → Dataflow → BigQuery → API → tablero. Las 287 publicaciones de la prueba streaming
incluyeron replay, controles, 60 eventos nuevos y dos fixtures; no son 287 lecturas nuevas.

La propuesta anual supone 500 sensores con un evento cada 15 segundos y 20.000 viajes/día.
El millón es un ensayo puntual. La redundancia presupuestada requiere despliegue y pruebas.
El gasto real acumulado sigue NO VERIFICADO. Ver [evidencia del millón](../docs/evidencias/batch_1m.md).
