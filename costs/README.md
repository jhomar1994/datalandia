# Presupuesto y calculadora

La [tabla con redundancia y replicación](primer_ano_redundancia.md) ordena los costos
de mayor a menor e incluye supuestos de dos jobs streaming zonales y archivo batch dual-region.

Para una simulación empresarial con batch diario y streaming continuo, consultar
[consumo del primer año](primer_ano_empresa.md), el modelo
[enterprise_calculator.py](enterprise_calculator.py) y [sus resultados](enterprise_estimate.json).
La estimación histórica de abajo describe el prototipo; no sustituye ese escenario empresarial.
Su reserva SECU era un supuesto: el modelo empresarial distingue cobro por volumen y por SECU.

Presupuesto total acordado: **S/50** para pruebas del 20 y demo del 21 de noviembre de 2026 (Lima).
Gasto real acumulado y créditos: **NO VERIFICADO**. No se presume gratuidad ni un límite automático de S/50.
Distribución de planificación: pruebas S/20, demo S/15 y reserva S/15.

## Control aplicado en la demo

- Dataflow batch de escala: dos `n1-standard-1`, disco de 30 GB por worker, sin autoescalado
  ni IP pública; un millón de entradas y plazo máximo de treinta minutos. Las pruebas
  históricas menores usaron uno o dos workers.
- Streaming: un `n1-standard-2` y Streaming Engine; cierre tras comprobar resultados y límite de doce minutos.
- Cloud Run: mínimo cero, máximo uno, 0,25 vCPU y 256 MiB; autenticación IAM.
- Consultas API con máximo de 128 MiB facturables por job y caché breve.
- Un build del contenedor, conservación de la imagen para la siguiente sesión y temporales con ciclo de vida.

Estos controles reducen consumo; no son un tope monetario. La vigilancia local debe permanecer activa.
Una alerta de presupuesto tampoco detiene los servicios por sí sola. Al terminar, comprobar jobs y VMs vacíos.

## Primer año

Ejecutar desde la raíz:

```bash
python3 costs/calculator.py --pen-per-usd 4.0
```

Resultado reproducible en `costs/estimate.json`. El cambio de S/4 por USD es un **supuesto editable**,
no una cotización actual. Se comparan diez horas mensuales de streaming bajo demanda y 730 horas mensuales
para operación continua, con un worker; diez horas de batch al mes, consultas de 0,1 TiB/mes,
10 GiB medios en BigQuery y 2 GiB/mes de tráfico Pub/Sub entre publicación y recepción.

Es una estimación preliminar: dos SECU por hora son un supuesto NO VERIFICADO y dependen del modelo
de facturación real del job y su carga. Dimensionar tras medir uso de Streaming Engine.
Discos, inserts streaming, Storage, Cloud Run, imágenes, compilación, logs y Workflows usan reservas
explícitas, no tarifas exactas. Incluye 30% de contingencia. No descuenta free tier, créditos, impuestos
ni descuentos. Transferencia a internet elevada y carga masiva requieren recalcular.
Para mantener 10 GiB medios al crecer, hace falta una política de retención; hoy no hay expiración de hechos.
Este escenario de consumo no acredita que un worker satisfaga un SLA de producción.

Tarifas de lista consultadas el 20/11/2026, para completar con la calculadora oficial antes de una cotización:

| Recurso | USD / unidad |
|---|---:|
| Dataflow batch vCPU-h | 0,056 |
| Dataflow memoria GiB-h | 0,003557 |
| Dataflow streaming vCPU-h | 0,069 |
| Streaming Engine unidad-h (según modelo) | 0,089 |
| BigQuery on-demand TiB | 6,25 |
| BigQuery almacenamiento lógico GiB-mes | 0,023 |
| Pub/Sub tráfico TiB | 40 |

Fuentes: [Dataflow](https://cloud.google.com/dataflow/pricing),
[BigQuery](https://cloud.google.com/bigquery/pricing), [Pub/Sub](https://cloud.google.com/pubsub/pricing),
[Cloud Run](https://cloud.google.com/run/pricing), [Cloud Build](https://cloud.google.com/build/pricing),
[Storage](https://cloud.google.com/storage/pricing), [calculadora oficial](https://cloud.google.com/products/calculator).

No sumar a este modelo el precio de la VM de Compute Engine: el cómputo del worker ya se estima
con las tarifas Dataflow. Las métricas de uso observadas no constituyen la factura de Cloud Billing.
