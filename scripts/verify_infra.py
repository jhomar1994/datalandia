"""Verifica la base GCP sin crear recursos ni iniciar procesamiento.

Ejecutar desde la raíz: .venv_beam/bin/python scripts/verify_infra.py
Requiere gcloud autenticado, Terraform y la infraestructura base aplicada.
Guarda el resultado en referencias_locales/terraform/verificacion.json.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PROJECT = "proyecto-datalandia"
EXPECTED_NUMBER = "637872675138"


def command_json(args):
    result = subprocess.run(args, check=True, capture_output=True, text=True, cwd=ROOT)
    return json.loads(result.stdout)


def main():
    outputs = command_json(["terraform", "-chdir=infra/terraform", "output", "-json"])
    values = {key: value["value"] for key, value in outputs.items()}
    project = values["project"]["id"]
    number = str(values["project"]["number"])
    region = values["project"]["region"]
    if (project, number) != (EXPECTED_PROJECT, EXPECTED_NUMBER):
        raise ValueError("El estado no corresponde al proyecto autorizado.")

    # El token permanece en memoria y nunca se guarda ni se imprime.
    token = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

    def get(url):
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)

    checks = []

    def require(condition, name):
        if not condition:
            raise ValueError(f"Verificación fallida: {name}")
        checks.append(name)

    actual = get(f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}")
    require(str(actual["projectNumber"]) == number, "identidad_proyecto")

    enabled = set()
    page_token = ""
    while True:
        query = urllib.parse.urlencode({"filter": "state:ENABLED", "pageSize": 200, "pageToken": page_token})
        page = get(f"https://serviceusage.googleapis.com/v1/projects/{number}/services?{query}")
        enabled.update(service["config"]["name"] for service in page.get("services", []))
        page_token = page.get("nextPageToken", "")
        if not page_token:
            break
    required_services = {
        "serviceusage.googleapis.com", "cloudresourcemanager.googleapis.com",
        "iam.googleapis.com", "compute.googleapis.com", "storage.googleapis.com",
        "pubsub.googleapis.com", "bigquery.googleapis.com", "bigquerystorage.googleapis.com",
        "dataflow.googleapis.com", "workflows.googleapis.com",
        "logging.googleapis.com", "monitoring.googleapis.com",
        "run.googleapis.com", "cloudbuild.googleapis.com", "artifactregistry.googleapis.com",
    }
    require(required_services <= enabled, "apis_requeridas_habilitadas")

    for kind, uri in values["buckets"].items():
        name = uri.removeprefix("gs://")
        bucket = get(f"https://storage.googleapis.com/storage/v1/b/{name}")
        require(str(bucket["projectNumber"]) == number, f"bucket_{kind}_proyecto")
        require(bucket["location"].lower() == region, f"bucket_{kind}_region")
        iam = bucket["iamConfiguration"]
        require(iam["uniformBucketLevelAccess"]["enabled"], f"bucket_{kind}_acceso_uniforme")
        require(iam["publicAccessPrevention"] == "enforced", f"bucket_{kind}_sin_acceso_publico")

    for kind, email in values["service_accounts"].items():
        account_path = f"projects/{project}/serviceAccounts/{email}"
        account = get(f"https://iam.googleapis.com/v1/{account_path}")
        require(not account.get("disabled", False), f"cuenta_{kind}_habilitada")
        keys = get(f"https://iam.googleapis.com/v1/{account_path}/keys?keyTypes=USER_MANAGED")
        require(not keys.get("keys"), f"cuenta_{kind}_sin_claves_descargables")

    dataset_id = values["bigquery_dataset"].split(".", 1)[1]
    dataset = get(f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/datasets/{dataset_id}")
    require(dataset["location"].lower() == region, "dataset_region")
    require(not dataset.get("defaultTableExpirationMs"), "dataset_sin_expiracion_automatica")

    pubsub = values["pubsub"]
    topic = get(f"https://pubsub.googleapis.com/v1/{pubsub['topic']}")
    subscription = get(f"https://pubsub.googleapis.com/v1/{pubsub['subscription']}")
    require(topic["name"] == subscription["topic"], "suscripcion_conectada_al_topic")
    require(subscription["messageRetentionDuration"] == "86400s", "retencion_pubsub_un_dia")

    runtime = values["dataflow_runtime"]
    compute = f"https://compute.googleapis.com/compute/v1/projects/{project}"
    subnet_name = runtime["subnetwork"].rsplit("/", 1)[1]
    subnet = get(f"{compute}/regions/{region}/subnetworks/{subnet_name}")
    require(subnet["privateIpGoogleAccess"], "subred_private_google_access")
    require(subnet["network"].rsplit("/", 1)[1] == runtime["network"], "subred_red_correcta")
    network = get(f"{compute}/global/networks/{runtime['network']}")
    require(not network.get("autoCreateSubnetworks", False), "red_personalizada")

    jobs = get(f"https://dataflow.googleapis.com/v1b3/projects/{project}/locations/{region}/jobs?filter=ACTIVE")
    require(not jobs.get("jobs"), "sin_jobs_dataflow_activos")
    instances = get(f"{compute}/aggregated/instances")
    vm_count = sum(len(zone.get("instances", [])) for zone in instances.get("items", {}).values())
    require(vm_count == 0, "sin_maquinas_virtuales")

    if values.get("api_url"):
        service = get(f"https://run.googleapis.com/v2/projects/{project}/locations/{region}/services/lumina-api")
        template = service["template"]
        scaling = template.get("scaling", {})
        require(scaling.get("minInstanceCount", 0) == 0 and scaling["maxInstanceCount"] == 1,
                "cloud_run_escala_cero_a_uno")
        require(template["serviceAccount"] == values["service_accounts"]["api"], "cloud_run_cuenta_correcta")
        require(template["maxInstanceRequestConcurrency"] == 1, "cloud_run_concurrencia_uno")
        limits = template["containers"][0]["resources"]["limits"]
        require(float(limits["cpu"]) == 0.25 and limits["memory"] == "256Mi", "cloud_run_recursos_acotados")

    regional = get(f"{compute}/regions/{region}")
    global_info = get(compute)
    selected = {"CPUS", "CPUS_ALL_REGIONS", "DISKS_TOTAL_GB", "SSD_TOTAL_GB", "INSTANCES", "IN_USE_ADDRESSES"}

    def quotas(info):
        return {
            quota["metric"]: {
                "limit": quota["limit"], "usage": quota["usage"],
                "available": quota["limit"] - quota["usage"],
            }
            for quota in info.get("quotas", []) if quota["metric"] in selected
        }

    quota_report = {"regional": quotas(regional), "global": quotas(global_info)}
    cpu = quota_report["regional"].get("CPUS")
    require(cpu is not None and cpu["available"] >= 2, "cuota_regional_para_un_worker_dos_vcpu")
    global_cpu = quota_report["global"].get("CPUS_ALL_REGIONS")
    if global_cpu is not None:
        require(global_cpu["available"] >= 2, "cuota_global_para_un_worker_dos_vcpu")

    report = {
        "verified_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "project": project, "project_number": number, "region": region,
        "checks_passed": checks, "quotas": quota_report,
        "active_dataflow_jobs": len(jobs.get("jobs", [])), "vm_count": vm_count,
    }
    destination = ROOT / "referencias_locales/terraform/verificacion.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        # Registrar solo el estado HTTP y endpoint, nunca cabeceras ni tokens.
        raise SystemExit(f"Error HTTP {error.code} consultando {error.url}") from None
