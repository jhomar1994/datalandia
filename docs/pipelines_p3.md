# Adaptación y validación de pipelines P3

El código cloud usa `proyecto-datalandia` y catálogos completos de nodos y sensores.
La preparación, validación local, comprobaciones SQL y pruebas reales de batch y streaming en Dataflow están realizadas.
Se demostró integración funcional con un worker, sin acreditar escalabilidad horizontal ni capacidad masiva.

## Entradas preparadas

La muestra P3 se guarda en `data/p3/input/`, fuera de Git, y no modifica las fuentes ni los resultados P2.

| Entrada | Cantidad |
|---|---:|
| Viajes sin prevalidar | 100.000 |
| Zonas de origen en la entrada | 260 |
| Lecturas históricas de sensores | 11.000 |
| Nodos y zonas de sensores | 11 |
| Asociaciones del puente batch | 2.694 |
| Asociaciones de nodos | 11 |
| Referencias de zonas | 263 |
| Definiciones del catálogo de sensores | 193 |

Los viajes se seleccionan por zona a partir del Parquet original, sin filtrar primero los inválidos.
Los IDs combinan hash del archivo original y posición de fila. La preparación acepta límite cero
para exportar todo el archivo; esa exportación completa no se ejecutó en esta etapa.
Las asociaciones y desplazamientos temporales siguen siendo simulados.

## Calidad y reintentos

Las reglas están separadas en `pipelines/cloud/validaciones.py` y se comparten con Beam.
Se comprueban tipos, fechas, zonas, valores finitos y contratos de sensores.
Los valores físicos fuera de rango se marcan; las unidades incompatibles o métricas no numéricas se rechazan.

El batch escribe a `viajes_staging`. Después de un job terminado, `finalize_batch.py` ejecuta
un MERGE transaccional con controles de conflicto y deja una fila canónica por viaje.
La repetición se probó con el SQL real de BigQuery y tablas temporales.
Staging conserva copias. La consolidación se ejecuta de forma serial; no se garantiza exactamente una vez
para escritores concurrentes ni equivalencia entre distintas versiones físicas de la fuente.

En sensores, Silver conserva copias y Gold deduplica por identidad y contenido.
Un ID con varios hashes se expone en `conflictos_sensores` y no entra en los promedios Gold.
El timestamp de republicación no cambia el hash de negocio.

## Resultados de validación local

Los scripts completos se ejecutaron con DirectRunner y salida a archivos, sin Dataflow ni escritura de hechos en BigQuery.

| Proceso | Recibidos | Aceptados | Rechazados | Zonas aceptadas |
|---|---:|---:|---:|---:|
| Viajes | 100.000 | 86.368 | 13.632 | 255 |
| Replay de sensores, incluido un error inyectado | 11.001 | 9.376 | 1.625 | 11 |

Los rechazos de viajes incluyen distancia, zonas, importe, duración y periodo.
Los de sensores incluyen valores no numéricos y métricas de identificación.
Estas tasas corresponden a una muestra equilibrada por zona y no representan tasas del archivo completo.

Se completaron doce pruebas unitarias y dos pruebas de integración en BigQuery con tablas temporales
para verificar la consolidación y el comportamiento de Gold; ver [pruebas](../tests/README.md).
El paquete para workers se construyó y se comprobó que no contiene datos ni archivos privados.
El paquete se instaló y ejecutó correctamente dentro de los workers privados de ambas pruebas.

## Recursos y datos en GCP

Terraform añadió siete tablas, cinco vistas y el workflow de verificación, sin modificar ni eliminar recursos existentes.
Las tablas son `viajes_staging`, `viajes_validos`, `sensores_validos`, `rechazados_raw`,
`puente_batch`, `puente_stream` y `referencia_zona`.
Las vistas son `conflictos_sensores`, `rechazados`, `gold_movilidad_5min`, `gold_sensores_5min` y `gold_zona_5min`.

Las tablas de hechos se particionan diariamente; los esquemas y clustering están en Terraform.
Las tablas contienen los hechos de la muestra de demo; no son datos de producción de una ciudad real.

El bundle se subió a:

```text
gs://proyecto-datalandia-637872675138-data/p3/inputs/a3453d3048051f31aa78fd5b52bb8e9e81ba2463374b8ecd7bd495d9dc668d3d/
```

Los objetos son inmutables por contenido. Se cargaron 2.694 filas en `puente_batch`, 11 en `puente_stream`
y 263 en `referencia_zona`. El workflow `lumina-verificar` terminó en `SUCCEEDED`, con hechos y cruces en cero.
Este workflow verifica; aún no orquesta el ciclo de vida de Dataflow.

## Pruebas reales del 20/11/2026

| Proceso | Entrada | Válidos en Silver | Rechazados | Cobertura |
|---|---:|---:|---:|---:|
| Batch Dataflow | 10.000 | 8.459 | 1.541 | 255 zonas válidas de origen |
| Streaming Dataflow | 225 mensajes | 184 copias / 182 IDs | 41 | 11 zonas |

Gold sensores conserva 181 IDs: elimina la copia duplicada y excluye un ID con dos contenidos conflictivos.
Los conteos observados coinciden con las reglas compartidas de validación. La API devuelve HTTP 409 para el conflicto.
El MERGE batch se ejecutó dos veces; el total canónico permaneció en 8.459 viajes y USD 301.703,37.

Batch: `lumina-p3-batch-20261120093854`, finalizó en DONE, un `n1-standard-1`, disco 30 GB.
Streaming: `lumina-p3-stream-20261120095819`, un `n1-standard-2`, Streaming Engine y disco 30 GB.
Ambos usan subred propia, IP privada y autoescalado deshabilitado.
La advertencia de max_workers ignorado refleja que autoscaling está deshabilitado; num_workers permanece en uno.
Se añadió acceso de lectura de configuración Pub/Sub a la suscripción tras observar una advertencia de permiso get;
la lectura y procesamiento de mensajes funcionaron durante la prueba.

La disponibilidad del evento de control se observó aproximadamente doce segundos después de publicarlo,
con el worker preparado. La medición incluye sondeo y consultas de comprobación; no es p95 ni SLA.
El arranque inicial del worker y replay tardó varios minutos y no debe omitirse al planificar la demo.

## Operación y siguiente paso

La API FastAPI y consumidor están desplegados en Cloud Run con autenticación IAM y escalado de cero a uno.
Los controladores de demo solicitan cierre de Dataflow y registran la terminación. Las comprobaciones finales
están en [evidencias](evidencias/demo_final.json); no mantener un worker activo entre sesiones.

Para repetir la ejecución, seguir [la demo](../demo/README.md). Requiere el bundle y catálogos ya cargados;
la preparación reproducible y staging se documentan en `pipelines/cloud/README.md` y `scripts/README.md`.
La vigilancia de tiempo es local y requiere mantener el equipo y proceso activos.

El workflow `lumina-verificar` comprueba conteos; no administra el ciclo de vida de jobs ni recuperación automática.
La revisión visual posterior está documentada en [actualización del tablero](evidencias/actualizacion_tablero.md).
La presentación ejecutiva PPTX/PDF y sus guiones están en [presentation](../presentation/README.md);
no se creó una presentación nativa de Google Slides. Quedan pendientes publicación de cambios y ensayo grupal.
El presupuesto acordado es S/50 para pruebas y demo; la facturación real no se ha verificado.
