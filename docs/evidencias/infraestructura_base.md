# Infraestructura base aplicada

Proyecto `proyecto-datalandia`, número `637872675138`, región `us-central1`.
Verificación: 2026-11-20 03:31:18 America/Lima.

Terraform aplicó **44 altas, cero modificaciones y cero eliminaciones**.
Un nuevo plan, con lectura del estado real, terminó sin diferencias (`-detailed-exitcode` igual a 0).

El verificador de APIs completó **33 comprobaciones**: identidad,
servicios habilitados, buckets privados, cuentas habilitadas sin claves de usuario,
ubicación y retención del dataset, relación topic-suscripción, red privada y cuotas.

| Recurso o cuota | Resultado observado |
|---|---:|
| Jobs Dataflow activos | 0 |
| Máquinas virtuales | 0 |
| vCPU regionales disponibles | 200 |
| vCPU globales disponibles | 32 |
| Disco estándar regional disponible | 4096 GB |
| Límite de jobs Dataflow del proyecto | 25 |

Las cuotas son límites disponibles en el momento de la consulta, no un dimensionamiento de la demo
ni una garantía de disponibilidad física. Los futuros scripts deben limitar la ejecución a un worker.
El presupuesto total sigue siendo S/50; este hito no incluye procesamiento ni una medición de gasto.

La evidencia estructurada está en [infraestructura_base.json](infraestructura_base.json).
Para repetir la comprobación antes de iniciar procesamiento:

```bash
.venv_beam/bin/python scripts/verify_infra.py
```

Los logs completos, outputs y respaldo de estado se conservan en `referencias_locales/terraform/`, fuera de Git.
Siguiente etapa: parametrizar pipelines y destinos, ampliar cobertura y comprobar idempotencia antes de lanzar jobs.
