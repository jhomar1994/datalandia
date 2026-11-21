# Infraestructura Terraform de Lumina

Configuración base para `proyecto-datalandia`, número `637872675138`, región `us-central1`.
La infraestructura base está aplicada y verificada: 44 recursos añadidos, sin diferencias en el plan posterior.
Ver [evidencia inicial](../../docs/evidencias/infraestructura_base.md). La ampliación P3 añade siete tablas,
cinco vistas y el workflow `lumina-verificar`.

La ampliación del tablero incorpora una octava tabla, `batch_ejecuciones`, para estados y
conteos batch. Es un recurso nuevo; no recrea las tablas de datos ni modifica sus particiones.

## Recursos definidos

- Quince APIs requeridas por almacenamiento, mensajería, procesamiento, IAM y orquestación.
- Tres buckets privados: datos, staging y temporales.
- Topic `lumina-eventos` y suscripción `lumina-streaming`, con retención de mensajes de un día.
- Dataset regional `lumina_demo`, sin expiración automática de tablas.
- Cuentas de servicio separadas para workers, API, workflow y publicador.
- Permisos IAM aditivos, acotados al recurso cuando corresponde.
- VPC propia, subred `10.42.0.0/24` con Private Google Access y comunicación interna entre workers.

Se define Artifact Registry y, al indicar `api_image`, la API Cloud Run privada. No se definen jobs Dataflow persistentes, máquinas virtuales propias, IP públicas ni NAT. El lanzador crea temporalmente workers administrados por Dataflow.
`tables.tf` usa los esquemas y SQL del repositorio; `workflows.tf` despliega un control de conteos bajo demanda.

## Autenticación

Terraform utiliza Application Default Credentials (ADC), que pueden ser distintas de la sesión de `gcloud`.
En un equipo nuevo, configurar ADC con `gcloud auth application-default login` si aún no existen.
El `project_id` del provider y de todos los recursos es explícito; no depende del proyecto activo del CLI.
El plan contrasta el número obtenido de Google Cloud con `expected_project_number` y rechaza diferencias.

Para reproducir las comprobaciones de identidad y facturación:

```bash
gcloud projects describe proyecto-datalandia --format='yaml(projectId,projectNumber,lifecycleState)'
gcloud billing projects describe proyecto-datalandia --format='yaml(projectId,billingEnabled)'
```

El ejecutor necesita permisos para habilitar APIs, crear los recursos y añadir sus permisos IAM.
La comprobación inicial confirmó catorce permisos base de la identidad activa; ver [revisión del plan](../../docs/plan_infraestructura.md).

## Generar y revisar el plan

Desde la raíz del repositorio, copiar el ejemplo solo si no existe una configuración local:

```bash
cp -n infra/terraform/environments/demo/terraform.tfvars.example infra/terraform/environments/demo/terraform.tfvars
terraform -chdir=infra/terraform init -input=false
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -input=false -var-file=environments/demo/terraform.tfvars -out=demo.tfplan
terraform -chdir=infra/terraform show -no-color demo.tfplan
```

`terraform init` fija el proveedor en `.terraform.lock.hcl`, que debe versionarse.
Los `.tfvars`, planes, estados y el directorio `.terraform/` están excluidos de Git.
Las APIs que ya estaban habilitadas también se añaden al estado al aplicar; no representan servicios duplicados.
Se conservan habilitadas al retirar la configuración (`disable_on_destroy = false`).

## Aplicación y verificación

El plan inicial ya fue aplicado. Para cambios posteriores, generar y revisar un nuevo plan antes de aplicar.
Los comandos de aplicación y verificación son:

```bash
terraform -chdir=infra/terraform apply demo.tfplan
terraform -chdir=infra/terraform output
.venv_beam/bin/python scripts/verify_infra.py
```

Si cambia la configuración o el estado remoto de recursos relevantes, regenerar y revisar el plan.
Los buckets y el dataset tienen protección `prevent_destroy`; los buckets tampoco permiten vaciar contenidos mediante `force_destroy`.
La eliminación deliberada de estos recursos requiere revisar y cambiar esas protecciones.

## Estado y colaboración

Esta etapa usa backend local; un respaldo privado del estado aplicado se conserva en `referencias_locales/terraform/`.
El estado contiene información operativa y no se versiona. Antes de aplicar desde otro equipo o CI,
crear un bucket dedicado al estado y migrar con el backend GCS; no usar los buckets del pipeline para ese fin.
Hasta esa migración, mantener un único equipo como responsable del estado y respaldarlo de forma privada tras aplicar.

## Operación y presupuesto

Los outputs `dataflow_runtime` definen la configuración utilizada por el lanzador: un worker inicial, máximo un worker y `use_public_ips = false`.
El script `scripts/run_dataflow.py` aplica estos parámetros: no constituyen una cuota ni un límite de gasto impuesto a GCP.
El presupuesto acordado es S/50 para pruebas y demo; ver [presupuesto](../../costs/README.md).

Los buckets staging y temp eliminan objetos de más de siete días y no retienen borrados reversibles;
el bucket de datos conserva borrados reversibles siete días y no tiene eliminación automática.
No borrar dependencias o staging mientras haya jobs activos.

Private Google Access permite alcanzar las APIs Google desde workers privados. Para dependencias Python externas,
preparar y subir dependencias o una imagen compatible antes de lanzar jobs; esta base no proporciona salida mediante NAT.
Las pruebas batch y streaming verificaron cuotas, empaquetado y red privada. Al pausar la demo, detener los jobs,
conservando los datos y la infraestructura base.

## Referencias

- [APIs y disable_on_destroy](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_service.html).
- [Datasets BigQuery con Terraform](https://docs.cloud.google.com/bigquery/docs/datasets).
- [Red privada y dependencias Dataflow](https://docs.cloud.google.com/dataflow/docs/guides/routes-firewall).

## API desplegada

`api.tf` añade Artifact Registry, permisos de Cloud Build y Cloud Run privado.
El digest de `api_image` se conserva únicamente en el tfvars local. Para reproducirlo,
seguir `api/README.md`. El servicio escala entre cero y una instancia de 0,25 vCPU/256 MiB.
El permiso Pub/Sub Viewer del worker está acotado a la suscripción para consultar su configuración;
Subscriber permite consumir los mensajes. No se otorga acceso público.
