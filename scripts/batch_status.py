"""Registro de ejecución batch; no guarda payloads ni credenciales."""
import datetime as dt

PROJECT = "proyecto-datalandia"
TABLE = "`proyecto-datalandia.lumina_demo.batch_ejecuciones`"


class BatchStatus:
    def __init__(self, batch_id, records, workers):
        from google.cloud import bigquery
        self.client = bigquery.Client(project=PROJECT)
        self.values = dict(batch_id=batch_id, started_at=dt.datetime.now(dt.timezone.utc),
                           expected_records=records, workers_requested=workers,
                           accepted=None, rejected=None, zones=None, dataflow_job_id=None,
                           consolidated=False)

    def query(self, sql, params):
        from google.cloud import bigquery
        return self.client.query(sql, location="us-central1", job_config=bigquery.QueryJobConfig(
            query_parameters=params, maximum_bytes_billed=512 * 1024**2)).result(timeout=60)

    def update(self, state, job_id=None, counts=False):
        from google.cloud import bigquery
        self.values.update(state=state, dataflow_job_id=job_id,
                           updated_at=dt.datetime.now(dt.timezone.utc))
        if counts:
            sql = """SELECT
              (SELECT COUNT(DISTINCT trip_id) FROM `proyecto-datalandia.lumina_demo.viajes_staging`
               WHERE batch_id=@batch_id AND processed_at>=@started_at) accepted,
              (SELECT COUNT(DISTINCT rejection_id) FROM `proyecto-datalandia.lumina_demo.rechazados_raw`
               WHERE batch_id=@batch_id AND source='viaje' AND processed_at>=@started_at) rejected,
              (SELECT COUNT(DISTINCT origin_id) FROM `proyecto-datalandia.lumina_demo.viajes_staging`
               WHERE batch_id=@batch_id AND processed_at>=@started_at) zones"""
            row = next(iter(self.query(sql, [
                bigquery.ScalarQueryParameter("batch_id", "STRING", self.values["batch_id"]),
                bigquery.ScalarQueryParameter("started_at", "TIMESTAMP", self.values["started_at"])])))
            self.values.update(dict(row))
        types = {"batch_id": "STRING", "started_at": "TIMESTAMP", "updated_at": "TIMESTAMP",
                 "state": "STRING", "expected_records": "INT64", "accepted": "INT64",
                 "rejected": "INT64", "zones": "INT64", "workers_requested": "INT64",
                 "dataflow_job_id": "STRING", "consolidated": "BOOL"}
        columns = list(types)
        source = ",".join(f"@{c} {c}" for c in columns)
        assignments = ",".join(f"{c}=s.{c}" for c in columns if c != "batch_id")
        self.query(f"""MERGE {TABLE} t USING (SELECT {source}) s ON t.batch_id=s.batch_id
          WHEN MATCHED THEN UPDATE SET {assignments}
          WHEN NOT MATCHED THEN INSERT ({','.join(columns)}) VALUES ({','.join('s.'+c for c in columns)})""",
          [bigquery.ScalarQueryParameter(c, types[c], self.values[c]) for c in columns])


def mark_consolidated(batch_id):
    from google.cloud import bigquery
    reporter = BatchStatus(batch_id, 0, 0)
    reporter.query(f"UPDATE {TABLE} SET consolidated=TRUE,updated_at=CURRENT_TIMESTAMP() "
                   "WHERE batch_id=@batch_id AND state='JOB_STATE_DONE'",
                   [bigquery.ScalarQueryParameter("batch_id", "STRING", batch_id)])
