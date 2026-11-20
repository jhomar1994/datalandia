"""Sube un bundle verificado a GCS y opcionalmente carga las referencias en BigQuery."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {name + ".jsonl" for name in (
    "viajes", "sensores", "puente_batch", "puente_stream", "referencia_zona", "catalogo_sensores")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/p3/input")
    parser.add_argument("--load-references", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((args.input / "manifest.json").read_text())
    payload = dict(manifest)
    bundle_id = payload.pop("bundle_id")
    expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if bundle_id != expected or set(manifest["artifacts"]) != ALLOWED:
        raise ValueError("Manifiesto inválido o archivos fuera del contrato")
    for filename, artifact in manifest["artifacts"].items():
        with (args.input / filename).open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        if checksum != artifact["sha256"]:
            raise ValueError(f"El archivo cambió después de preparar el manifiesto: {filename}")
    outputs = json.loads(subprocess.run(
        ["terraform", "-chdir=infra/terraform", "output", "-json"],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout)
    config = {key: value["value"] for key, value in outputs.items()}
    project = config["project"]
    if project["id"] != "proyecto-datalandia" or str(project["number"]) != "637872675138":
        raise ValueError("Destino Terraform no autorizado")
    from google.api_core.exceptions import PreconditionFailed
    from google.cloud import storage
    client = storage.Client(project=project["id"])
    bucket = client.bucket(config["buckets"]["data"].removeprefix("gs://"))
    prefix = f"p3/inputs/{bundle_id}"
    uris = {}
    for filename in sorted(ALLOWED | {"manifest.json"}):
        source = args.input / filename
        with source.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        blob = bucket.blob(f"{prefix}/{filename}")
        blob.metadata = {"sha256": checksum}
        try:
            blob.upload_from_filename(source, if_generation_match=0)
        except PreconditionFailed:
            blob.reload()
            if (blob.metadata or {}).get("sha256") != checksum:
                raise ValueError(f"Objeto remoto conflictivo: {blob.name}") from None
        uris[filename] = f"gs://{bucket.name}/{blob.name}"
    loads = {}
    if args.load_references:
        from google.cloud import bigquery
        bq = bigquery.Client(project=project["id"])
        for name in ("puente_batch", "puente_stream", "referencia_zona"):
            fields = json.loads((ROOT / f"schemas/bigquery/{name}.json").read_text())
            job = bq.load_table_from_uri(
                uris[name + ".jsonl"], config["bigquery_dataset"] + "." + name,
                location=project["region"], job_config=bigquery.LoadJobConfig(
                    schema=[bigquery.SchemaField.from_api_repr(field) for field in fields],
                    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE))
            job.result()
            loads[name] = {"job_id": job.job_id, "rows": job.output_rows}
    report = {"project": project["id"], "bundle_id": bundle_id, "uris": uris, "reference_loads": loads}
    path = ROOT / "referencias_locales/p3_staging.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
