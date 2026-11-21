# Batch de un millón: ejecución real en GCP

Prueba del **21/11/2026 (Lima)** en `proyecto-datalandia`, región `us-central1`.
Job: `lumina-p3-scale-20261121050254-fc9795`.
ID Dataflow: `2026-11-20_21_03_47-1124113057153420567`.
Estado final: **JOB_STATE_DONE**, consolidación completada.

| Comprobación | Resultado |
|---|---:|
| Entradas TLC reales, sin prevalidar | 1.000.000 |
| Bytes JSONL de viajes | 229.713.293 (219,07 MiB) |
| Códigos de origen en entrada | 260 |
| Filas staging / IDs válidos distintos | 937.453 / 937.453 |
| Rechazos físicos / IDs de rechazo distintos | 62.547 / 62.547 |
| Conciliación | (937.453 + 62.547) / 1.000.000 = 100 % |
| Zonas válidas de origen | 255 |
| Workers solicitados / VMs RUNNING observadas | 2 / 2 |
| Tipo por worker | n1-standard-1, disco 30 GB, IP privada |
| Duración entre startTime y DONE de Dataflow | 324,595 s |
| Duración del controlador | 352 s |
| RUNNING observado por sondeo | 311 s |
| Rendimiento bruto: entradas / duración Dataflow | 3.080,8 entradas/s |
| Rendimiento usando controlador como denominador | 2.840,9 entradas/s |
| Rendimiento usando RUNNING observado | 3.215,4 entradas/s |
| Cambio de filas al repetir MERGE serial | 0 |
| Viajes canónicos antes y después del reproceso | 937.453 |
| Importe antes y después | USD 24.490.375,32 |
| Jobs activos / VMs al finalizar | 0 / 0 |

El rendimiento bruto incluye arranque, lectura, validación y cargas BigQuery; el MERGE
posterior no forma parte de la duración del job Dataflow. El intervalo RUNNING procede
del sondeo del controlador, no de una medición exclusiva de transformación. No se infiere
escalamiento lineal comparando este ensayo con el anterior de 10.000 filas.

Dos workers en `us-central1-f` son paralelismo dentro de una zona, no redundancia zonal.
La lista de VMs guardada durante la ejecución contiene los dos nombres y la etiqueta
`dataflow_job_id` coincidente. Esto acredita recursos observados; no reparto uniforme de carga.

El bundle `4ad4e87bd7b427c388ed2697165db712481a4a00a70906b34ce6f3ec8c2d447c`
se conserva bajo `gs://proyecto-datalandia-637872675138-data/p3/inputs/`.
Los viajes conservan IDs derivados del hash del Parquet y su número de fila: no se generaron
copias artificiales para alcanzar el millón. La selección equilibra zonas y no estima
la calidad estadística del archivo TLC completo.

[JSON auditable con consultas, jobs y resultados](batch_1m.json).
Las capturas se incorporan al informe local bajo `output/pdf/`, ignorado por Git.
Las pruebas anteriores conservan sus fechas y conteos; no son el resultado de esta ejecución.

## Reproducción

```bash
.venv_beam/bin/python scripts/demo_batch.py --records 1000000 --workers 2 --max-minutes 30
```

El comando genera consumo y requiere mantener el controlador activo. Los parámetros son
los predeterminados actuales. No relanzar para ver el tablero: `/batch/ultimo` sirve el
último resultado persistido. Se verificó HTTP 200 en `/batch/ultimo`, `/kpis` y `/zonas`
después de consolidar, manteniendo el límite API de 128 MiB por consulta.

La factura y el costo real acumulado siguen **NO VERIFICADO**. Esta prueba aporta volumen
y cómputo distribuido, pero no acredita operación 24/7, recuperación ni capacidad productiva.
