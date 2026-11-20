# Dependencias

Mantener entornos separados: Spark y Beam utilizan versiones distintas de PyArrow y NumPy.

- `local.in`: dependencias directas del procesamiento local.
- `local.txt`: resolución fijada existente, trasladada sin cambiar versiones.
- `cloud.in`: dependencias directas de Beam y Pub/Sub.
- `cloud.txt`: instantánea del entorno `.venv_beam` para P3, incluido setuptools para construir el paquete propio.

Instalación desde la raíz:

```bash
uv venv --python 3.12 .venv_bigdata
uv pip install --python .venv_bigdata/bin/python -r requirements/local.txt

uv venv --python 3.12 .venv_beam
uv pip install --python .venv_beam/bin/python -r requirements/cloud.txt
```

La preparación de muestras cloud requiere las salidas locales y se ejecuta con `.venv_bigdata`.
La instantánea cloud procede de macOS con Python 3.12; validar la compatibilidad del entorno
de workers antes de crear un paquete para Dataflow.
