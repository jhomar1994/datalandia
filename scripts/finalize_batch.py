"""Consolida un batch terminado mediante MERGE, sin lanzar workers."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipelines.cloud.sql_utils import render_sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="proyecto-datalandia")
    parser.add_argument("--dataset", default="lumina_demo")
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()
    from google.cloud import bigquery
    client = bigquery.Client(project=args.project)
    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("batch_id", "STRING", args.batch_id)],
        maximum_bytes_billed=5 * 1024**3,
    )
    job = client.query(render_sql("finalizar_batch.sql", args.project, args.dataset),
                       location=args.region, job_config=config)
    job.result()
    print(json.dumps({"job_id": job.job_id, "batch_id": args.batch_id, "state": job.state,
                      "bytes_processed": job.total_bytes_processed}))


if __name__ == "__main__":
    main()
