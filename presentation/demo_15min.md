# Preparación de la demo para una exposición de 15 minutos

Esta guía separa el uso de los CLI existentes. No añade los modos preparar/publicar/cerrar a demo_e2e.py.
No ejecutar demo_e2e.py en paralelo: crearía otra sesión y solicitaría cierre por su cuenta.
No se iniciaron recursos GCP al preparar esta presentación.

## Antes de exponer (sin cómputo Dataflow)

Desde la raíz, preparar una sesión nueva de archivos locales:

```bash
.venv_beam/bin/python presentation/preparar_eventos_exposicion.py
```

Guarda un ID de warmup y 62 mensajes (60 válidos y dos inválidos) en referencias_locales/exposicion/.
Si ya existe esa carpeta, usar otra con --out y sustituir las rutas siguientes. Conservar el ID impreso.
Los mensajes son controles sintéticos basados en el contrato del replay, no nuevos sensores físicos.

Iniciar el proxy en una terminal:

```bash
gcloud run services proxy lumina-api --project=proyecto-datalandia --region=us-central1 --port=8080
```

Abrir http://127.0.0.1:8080/ y pausar el tablero mientras se explica. Preparar /docs en otra pestaña.

## Al comenzar la exposición (minuto 0)

Otro integrante inicia el único worker y mantiene esa terminal abierta:

```bash
.venv_beam/bin/python scripts/run_dataflow.py --mode stream --max-minutes 15 --stop-file referencias_locales/exposicion/stop
```

En otra terminal publicar el warmup, que puede esperar en Pub/Sub mientras arranca Dataflow:

```bash
.venv_beam/bin/python pipelines/cloud/publicar_eventos.py --input referencias_locales/exposicion/warmup.jsonl --limit 1 --rate 1
```

Comprobar el ID impreso por el preparador en /api/events/ID o /eventos/ultimo antes del bloque de demo.
RUNNING por sí solo no garantiza que ya esté listo. Revisar cualquier error en el controller/driver log.
La comprobación vía API es la evidencia de que ya puede procesar.

## Bloque de demo (8:30 a 11:30)

1. Mostrar Dataflow en ejecución con un worker y reanudar el tablero.
2. Publicar la ráfaga en otra terminal:

```bash
.venv_beam/bin/python pipelines/cloud/publicar_eventos.py --input referencias_locales/exposicion/eventos.jsonl --limit 62 --rate 1
```

3. Durante el minuto de publicación, observar barras aceptadas/rechazadas y tarjeta del último evento.
4. Mostrar /eventos/por-minuto?min=15 y /eventos/ultimo en Swagger. Explicar los relojes y la deduplicación.
5. Mostrar los rechazos no numéricos y solicitar el cierre:

```bash
touch referencias_locales/exposicion/stop
```

Continuar la presentación mientras se drena. El controlador solicita cancelación si el drain excede su plazo.
El límite global es de 15 minutos desde que inicia el controlador; no interrumpir ni cerrar la laptop antes del cierre.
Si se abre una terminal desde otra carpeta, usar siempre la raíz del repo como directorio de trabajo.

## Al terminar

```bash
gcloud dataflow jobs list --project=proyecto-datalandia --status=active
gcloud compute instances list --project=proyecto-datalandia
```

Verificar listas vacías y pausar/cerrar el tablero. Si el proceso local cayó y sigue un job activo,
cancelarlo por ID con --project=proyecto-datalandia y --region=us-central1, y verificar de nuevo.
La vigilancia local no protege frente a una caída de la laptop o pérdida de acceso a GCP.

Respaldo: evidencias reales en docs/evidencias y el HTML local api/static/index.html con ?demo=1.
Declarar explícitamente que ese modo es simulado. No afirmar que sustituye una demostración en vivo.
