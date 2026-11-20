# Pruebas

Pruebas puras de calidad, IDs, reintentos, nodos múltiples, límites temporales y parámetros SQL:

```bash
.venv_bigdata/bin/python -m unittest discover -s tests -p 'test_cloud_*.py' -v
```

Se completaron 12 pruebas. La validación DirectRunner de los scripts completos se documenta
en `docs/pipelines_p3.md`.

Las dos pruebas de integración utilizan BigQuery real con tablas temporales, no tablas de negocio ni Dataflow:

```bash
RUN_GCP_TESTS=1 .venv_beam/bin/python -m unittest discover -s tests -p 'test_bigquery_merge.py' -v
```

Comprueban que duplicados y reintentos mantengan dos viajes y su importe, que un conflicto no modifique el destino,
y que Gold de sensores excluya duplicados y conflictos al calcular conteos y promedios.
Cada prueba establece un máximo de 512 MiB facturables para su consulta multisentencia; no representa el consumo real.
Sin `RUN_GCP_TESTS=1` estas pruebas se omiten.

`fixtures/viajes_errores_demo.jsonl` conserva los eventos inválidos originales de P2, sin `trip_id`.
Para utilizarlos con el contrato P3, añadir un ID de fuente; de lo contrario serán rechazados por falta de ese campo.


Contrato HTTP, filtros antes de consultar BigQuery, errores 404/409/503 y consumidor estático:

```bash
.venv_api/bin/python -m unittest tests.test_api tests.test_cloud_contracts -v
```

Quince pruebas aprobadas. El repositorio falso se inyecta solo en tests; producción usa BigQuery.
Las pruebas reales Dataflow y Cloud Run se documentan en `docs/evidencias/demo_final.json`.
La comprobación HTTP y de sintaxis JavaScript no sustituye la revisión visual pendiente en navegador.


Nuevo contrato de monitoreo: `tests.test_monitoring`. El conjunto con test_api y test_cloud_contracts
suma dieciocho pruebas; comprueba respuestas vacías 200, serie 1/15/60 minutos ordenada y rellena,
parámetros fuera de rango, una consulta compartida entre rutas y reloj actualizado sin invalidar caché.
