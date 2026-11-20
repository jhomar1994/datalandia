# Reorganización del repositorio

La estructura nueva se aplica en el repositorio existente, en la rama `feat/p3-entrega-final`.
Los datos, checkpoints y resultados bajo `data/` mantienen sus ubicaciones.

| Ubicación anterior | Ubicación actual |
|---|---|
| `notebooks/01_ETL_Medallion_Homologacion.py` | `pipelines/local/etl_medallion.py` |
| `notebooks/02_puentes_batch_streaming.py` | `pipelines/local/puentes_batch_streaming.py` |
| `notebooks/03_p2_hibrido.py` | `pipelines/local/hibrido.py` |
| `notebooks/README_P2.md` | `docs/ejecucion_local.md` |
| `infraestructura_gcp/pipeline_beam.py` | `pipelines/cloud/pipeline_beam.py` |
| `infraestructura_gcp/preparar_muestras.py` | `pipelines/cloud/preparar_muestras.py` |
| `infraestructura_gcp/publicar_eventos.py` | `pipelines/cloud/publicar_eventos.py` |
| `infraestructura_gcp/gold.sql` | `sql/bigquery/gold_zona_5min.sql` |
| `infraestructura_gcp/verificar_workflow.yaml` | `workflows/verificar.yaml` |
| `infraestructura_gcp/viajes_errores_demo.jsonl` | `tests/fixtures/viajes_errores_demo.jsonl` |
| `infraestructura_gcp/README.md` | `docs/despliegue_gcp_p2.md` |
| `requirements.in` | `requirements/local.in` |
| `requirements.txt` | `requirements/local.txt` |
| `setup_project.py` | `scripts/setup_local.py` |
| `informe_p2/Lumina_informe_p1.pdf` | `reports/parte_1/Lumina_informe_p1.pdf` |
| `informe_p2/Informe P2_ Datalandia.pdf` | `reports/parte_2/Informe P2_ Datalandia.pdf` |

Los notebooks `.ipynb` permanecen en `notebooks/`. Los informes originales y el material de
evaluación siguen excluidos de Git; los scripts cloud, SQL, workflow y fixtures sintéticos son versionables.

Los scripts trasladados resuelven las rutas de datos desde la raíz del repositorio.
El comando de preparación es `python3 scripts/setup_local.py`; la instalación local usa
`requirements/local.txt` y la instalación de Beam usa `requirements/cloud.txt` en otro entorno.

## Estado de P3

Las carpetas `infra/terraform/`, `api/`, `consumer/`, `demo/`, `schemas/`, `costs/` y `presentation/`
establecen los destinos de los siguientes entregables. Sus README distinguen los componentes
existentes de las implementaciones pendientes.

La infraestructura Terraform base ya está aplicada y verificada; su [plan y estado](plan_infraestructura.md) tienen evidencia de comprobación.
El destino previsto de P3 es `proyecto-datalandia`, número `637872675138`.
El código cloud fue adaptado al proyecto nuevo; SQL y workflow reciben el destino desde configuración.
Consultar [pipelines P3](pipelines_p3.md) para las pruebas y el estado de ejecución. Reorganizar archivos no inicia jobs,
crea recursos ni modifica los proyectos de GCP.
