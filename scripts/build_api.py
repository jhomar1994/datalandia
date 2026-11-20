"""Construye en Cloud Build exclusivamente API y consumidor (sin datos ni credenciales)."""
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "proyecto-datalandia"
REGION = "us-central1"


def main():
    folder = ROOT / "referencias_locales/api_build"
    folder.mkdir(parents=True, exist_ok=True)
    files = [(ROOT / "api/Dockerfile", "Dockerfile"),
             (ROOT / "api/requirements.txt", "requirements.txt")]
    files += [(p, "app/" + p.name) for p in sorted((ROOT / "api/app").glob("*.py"))]
    files += [(p, "static/" + str(p.relative_to(ROOT / "api/static")))
              for p in sorted((ROOT / "api/static").rglob("*")) if p.is_file() and p.suffix in {".html", ".css", ".js", ".svg"}]
    digest = hashlib.sha256()
    for path, name in files:
        digest.update(name.encode())
        digest.update(path.read_bytes())
    source_hash = digest.hexdigest()
    image = f"{REGION}-docker.pkg.dev/{PROJECT}/lumina-images/lumina-api:demo-{source_hash[:12]}"
    archive = folder / f"source-{source_hash[:12]}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path, name in files:
            tar.add(path, arcname=name, recursive=False)
    config = {
        "steps": [{"name": "gcr.io/cloud-builders/docker", "args": ["build", "-t", image, "."]}],
        "images": [image], "timeout": "600s",
        "serviceAccount": f"projects/{PROJECT}/serviceAccounts/lumina-build@{PROJECT}.iam.gserviceaccount.com",
        "options": {"logging": "CLOUD_LOGGING_ONLY"},
    }
    config_path = folder / "cloudbuild.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(json.dumps({"image": image, "files": [n for _, n in files], "source_bytes": archive.stat().st_size}), flush=True)
    output = subprocess.run([
        "gcloud", "builds", "submit", str(archive), f"--project={PROJECT}", f"--region={REGION}",
        f"--config={config_path}", "--gcs-source-staging-dir=gs://proyecto-datalandia-637872675138-data-staging/cloud-build/source",
        "--format=json", "--quiet",
    ], check=False, capture_output=True, text=True)
    (folder / "build.log").write_text(output.stderr)
    if output.returncode:
        raise RuntimeError(f"Cloud Build falló (exit {output.returncode}); revisar {folder / 'build.log'}")
    result = json.loads(output.stdout)
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    if result["status"] != "SUCCESS":
        raise RuntimeError("Cloud Build no terminó correctamente")
    built = result["results"]["images"][0]
    immutable = image.split(":demo-")[0] + "@" + built["digest"]
    (folder / "image.txt").write_text(immutable + "\n")
    print(json.dumps({"id": result["id"], "status": result["status"], "image": immutable}), flush=True)


if __name__ == "__main__":
    main()
