# Pipelines de DataLandia

El código ejecutable se separa de los notebooks interactivos.

| Directorio | Contenido |
|---|---|
| `local/` | ETL medallón, tablas puente y streaming local con Spark y SQLite. |
| `cloud/` | Código Beam y herramientas de la demostración P2 en GCP. |

Los scripts calculan la raíz desde su ubicación y conservan las rutas de `data/`.
Para ejecutar la versión documentada, usar los `.py`; los `.ipynb` conservan el ejercicio interactivo original.

Consultar [ejecución local](../docs/ejecucion_local.md) y [pipeline cloud](cloud/README.md).
