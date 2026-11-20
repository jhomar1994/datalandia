# Herramientas de operación

Desde la raíz:

```bash
python3 scripts/setup_local.py
```

Crea las carpetas locales faltantes sin sobrescribir datos.

Para verificar la infraestructura base aplicada, usando el entorno Python 3.12 de cloud:

```bash
.venv_beam/bin/python scripts/verify_infra.py
```

El verificador consulta APIs habilitadas, buckets, cuentas sin claves de usuario, dataset,
mensajería, red, cuotas y ausencia de cómputo activo. No crea recursos ni procesa datos.
Guarda su resultado en `referencias_locales/terraform/verificacion.json`, fuera de Git.
El ejecutor necesita permisos de lectura de esos recursos; la comprobación de cero jobs y VMs
corresponde a la pausa antes o después del procesamiento, no al estado esperado durante una demo activa.

Operación implementada:

- `run_dataflow.py`: un worker privado, vigilancia y cierre; requiere entorno Beam.
- `demo_e2e.py`: lanza streaming, publica y verifica API/BigQuery, solicita cierre.
- `build_api.py`: empaqueta API/consumidor y construye en Cloud Build; requiere entorno API.

Comandos y límites en `demo/README.md` y `api/README.md`.

Preparación del bundle y referencias:

```bash
.venv_beam/bin/python scripts/stage_inputs.py --load-references
```

Valida hashes, sube entradas al bucket del proyecto obtenido de Terraform y reemplaza únicamente
las tres tablas de referencias. No inicia workers. Conservar el manifiesto para reproducir la ejecución.

Consolidación posterior a un batch Dataflow terminado:

```bash
.venv_beam/bin/python scripts/finalize_batch.py --batch-id ID_DEL_BATCH_TERMINADO
```

No lanzar la consolidación antes de confirmar el estado `DONE` del job.
