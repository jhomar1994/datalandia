# Plan de infraestructura base de P3

El plan Terraform para `proyecto-datalandia` propone **44 recursos a añadir, cero a modificar y cero a eliminar**.
El plan fue aplicado: **44 recursos añadidos, cero modificados y cero eliminados**.
La comprobación posterior no encontró diferencias. Ver [evidencia](evidencias/infraestructura_base.md).

## Destino e inventario inicial

La revisión del 20 de noviembre de 2026 confirmó:

- Project ID `proyecto-datalandia`, número `637872675138`, estado `ACTIVE`.
- Facturación habilitada.
- Catorce permisos base consultados disponibles en la identidad activa: habilitar y listar APIs,
  consultar y modificar IAM del proyecto, crear buckets, topic, suscripción, dataset, cuentas,
  redes, subredes y firewall, y actuar como cuenta de servicio.
- Sin buckets, cuentas de servicio propias, datasets, topics ni suscripciones encontrados.
- Antes de aplicar, la API Compute estaba deshabilitada; el inventario de red se completó tras habilitarla.
- Algunas APIs, entre ellas BigQuery y Storage, ya están habilitadas. Su gestión en Terraform no las duplica.

## Cambios propuestos

| Categoría | Recursos Terraform | Detalle |
|---|---:|---|
| APIs | 12 | Habilitación o incorporación al estado de los servicios requeridos. |
| Buckets | 3 | Datos, staging y temporales. |
| Mensajería | 2 | Topic y suscripción. |
| BigQuery | 1 | Dataset regional sin expiración automática. |
| Identidades | 4 | Dataflow, API, workflow y publicador. |
| Red | 3 | VPC propia, subred privada y regla interna entre workers. |
| Permisos IAM | 19 | Adiciones a proyecto, dataset, buckets, mensajería, subred y cuenta worker. |
| **Total** | **44** | **Sin modificaciones ni eliminaciones planificadas.** |

Buckets:

```text
gs://proyecto-datalandia-637872675138-data
gs://proyecto-datalandia-637872675138-data-staging
gs://proyecto-datalandia-637872675138-data-temp
```

Se usará `us-central1` en almacenamiento, dataset y subred.
No se crean tablas ni se cargan datos en esta etapa.

## Comprobaciones

- `terraform fmt -check -recursive` y `terraform validate`.
- Plan real contra Google Cloud con comparación del número de proyecto.
- Revisión del JSON del plan: todas las acciones administradas son `create` y todos los atributos
  `project` corresponden a `proyecto-datalandia`.
- Ausencia de jobs Dataflow, máquinas, NAT, direcciones públicas y claves de servicio en el plan.
- Sin miembros IAM públicos `allUsers` o `allAuthenticatedUsers`.
- Comprobación de rechazo al proporcionar un número de proyecto incorrecto.

El plan binario está en `infra/terraform/demo.tfplan`. El texto, JSON y resumen del plan se conservan
en `referencias_locales/terraform/`, fuera de Git. Se versionan la configuración `.tf` y el lock del proveedor.

## Alcance operativo

La aplicación habilitó APIs y creó la infraestructura base. La verificación de recursos completó 33 comprobaciones.
No hay workers ni máquinas virtuales iniciados por esta etapa. El plan no es una cotización ni un límite automático de S/50.
Los límites de ejecución y el apagado deberán implementarse al preparar los scripts de Dataflow.

Los recursos de datos tienen protección frente a destrucción y el estado usa backend local.
Antes de trabajar desde varios equipos, migrar el estado a un bucket dedicado mediante backend GCS.

## Siguientes pasos

1. Parametrizar los pipelines, SQL y workflow con el nuevo destino; ampliar zonas/nodos y hacer seguro el reintento batch.
2. Preparar dependencias para workers privados y ejecutar batch y una prueba streaming breve con métricas y apagado.
3. Implementar API y consumidor sobre Gold y comprobar la disponibilidad de un evento publicado desde extremo a extremo.
4. Registrar KPI, estimación anual, evidencia de recuperación y preparar Slides y ensayo.
