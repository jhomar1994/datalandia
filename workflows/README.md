# Workflows

`verificar.yaml` se despliega con Terraform como `lumina-verificar` en `proyecto-datalandia`.
Obtiene el proyecto de su entorno de ejecución y consulta conteos de viajes consolidados,
sensores recibidos, IDs únicos, rechazos únicos, conflictos y cruces Gold.

```bash
gcloud workflows run lumina-verificar --project=proyecto-datalandia --location=us-central1
```

La primera ejecución de verificación fue satisfactoria, con hechos en cero antes de ejecutar
los pipelines P3. Después se completaron pruebas batch y streaming reales; ver
[resultados P3](../docs/pipelines_p3.md) y [evidencia de la demo](../docs/evidencias/demo_final.json).
Los conteos de aquella primera verificación no representan el estado actual de las tablas.
El workflow es un control bajo demanda: aún no inicia, supervisa ni detiene Dataflow.
