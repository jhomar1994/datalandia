"""Prueba opt-in de MERGE real con tablas temporales, sin workers ni datos de negocio."""
import json
import os
import unittest
from pathlib import Path

from pipelines.cloud.sql_utils import render_sql

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("RUN_GCP_TESTS") == "1", "Requiere RUN_GCP_TESTS=1 y acceso a GCP")
class BigQueryMergeTest(unittest.TestCase):
    def test_sensor_gold_excludes_conflicts_and_duplicates(self):
        from google.cloud import bigquery
        client = bigquery.Client(project="proyecto-datalandia")
        conflict_sql = render_sql("conflictos_sensores.sql", "proyecto-datalandia", "lumina_demo")
        gold_sql = render_sql("gold_sensores_5min.sql", "proyecto-datalandia", "lumina_demo")
        for name, temporary in [("sensores_validos", "sensor_test"), ("conflictos_sensores", "conflict_test")]:
            identifier = f"`proyecto-datalandia.lumina_demo.{name}`"
            conflict_sql = conflict_sql.replace(identifier, temporary)
            gold_sql = gold_sql.replace(identifier, temporary)
        script = """
CREATE TEMP TABLE sensor_test (
  event_id STRING, payload_hash STRING, zone_id STRING, event_ts TIMESTAMP,
  subsystem STRING, sensor STRING, parameter STRING, unit STRING,
  value FLOAT64, out_of_range BOOL, published_at TIMESTAMP, processed_at TIMESTAMP
);
INSERT INTO sensor_test VALUES
('a','h-a','DL-132',TIMESTAMP '2024-01-01 05:00:00+00','weather','temp','temperature','C',10,FALSE,TIMESTAMP '2026-11-20 08:00:00+00',TIMESTAMP '2026-11-20 08:00:01+00'),
('a','h-a','DL-132',TIMESTAMP '2024-01-01 05:00:00+00','weather','temp','temperature','C',10,FALSE,TIMESTAMP '2026-11-20 08:01:00+00',TIMESTAMP '2026-11-20 08:01:01+00'),
('b','h-b','DL-132',TIMESTAMP '2024-01-01 05:00:00+00','weather','temp','temperature','C',20,FALSE,TIMESTAMP '2026-11-20 08:00:00+00',TIMESTAMP '2026-11-20 08:00:01+00'),
('b','other-hash','DL-132',TIMESTAMP '2024-01-01 05:00:00+00','weather','temp','temperature','C',99,TRUE,TIMESTAMP '2026-11-20 08:01:00+00',TIMESTAMP '2026-11-20 08:01:01+00'),
('c','h-c','DL-132',TIMESTAMP '2024-01-01 05:00:00+00','weather','temp','temperature','C',30,FALSE,TIMESTAMP '2026-11-20 08:00:00+00',TIMESTAMP '2026-11-20 08:00:01+00');
CREATE TEMP TABLE conflict_test AS
""" + conflict_sql.rstrip().rstrip(";") + ";\nCREATE TEMP TABLE gold_test AS\n" + gold_sql.rstrip().rstrip(";") + """;
ASSERT (SELECT COUNT(*) FROM conflict_test) = 1 AS 'No se detectó el conflicto';
ASSERT (SELECT lecturas FROM gold_test) = 2 AS 'Duplicados o conflictos entraron en Gold';
ASSERT (SELECT valor_promedio FROM gold_test) = 20 AS 'Promedio incorrecto';
SELECT lecturas, valor_promedio FROM gold_test;
"""
        job = client.query(script, location="us-central1", job_config=bigquery.QueryJobConfig(
            maximum_bytes_billed=512 * 1024**2))
        rows = list(job.result())
        self.assertEqual((rows[0].lecturas, rows[0].valor_promedio), (2, 20))
        evidence = {"job_id": job.job_id, "state": job.state, "bytes_processed": job.total_bytes_processed,
                    "canonical_readings": 2, "average": 20, "conflicting_ids": 1,
                    "uses_temporary_tables": True}
        path = ROOT / "referencias_locales/terraform/prueba_gold.json"
        path.write_text(json.dumps(evidence, indent=2) + "\n")

    def test_retry_and_conflict_are_safe(self):
        from google.cloud import bigquery
        client = bigquery.Client(project="proyecto-datalandia")
        names = {"viajes_staging": "staging_test", "viajes_validos": "target_test"}
        declarations = []
        for source, temporary in names.items():
            fields = json.loads((ROOT / f"schemas/bigquery/{source}.json").read_text())
            sql_types = {"FLOAT": "FLOAT64", "INTEGER": "INT64", "BOOLEAN": "BOOL"}
            ddl = ",".join(f"{field['name']} {sql_types.get(field['type'], field['type'])}" for field in fields)
            declarations.append(f"CREATE TEMP TABLE {temporary} ({ddl});")
        query = render_sql("finalizar_batch.sql", "proyecto-datalandia", "lumina_demo")
        for source, temporary in names.items():
            query = query.replace(f"`proyecto-datalandia.lumina_demo.{source}`", temporary)
        good = query.replace("@batch_id", "'run1'")
        conflict = query.replace("@batch_id", "'run2'")
        script = "\n".join(declarations) + """
INSERT INTO staging_test VALUES
('a','hash-a',132,41,DATETIME '2024-01-01 00:00:00',DATETIME '2024-01-01 00:10:00',3.2,10,TIMESTAMP '2026-11-20 08:00:00+00','run1'),
('a','hash-a',132,41,DATETIME '2024-01-01 00:00:00',DATETIME '2024-01-01 00:10:00',3.2,10,TIMESTAMP '2026-11-20 08:01:00+00','run1'),
('b','hash-b',237,41,DATETIME '2024-01-01 00:00:00',DATETIME '2024-01-01 00:10:00',6.4,20,TIMESTAMP '2026-11-20 08:00:00+00','run1');
""" + good + good + """
ASSERT (SELECT COUNT(*) FROM target_test) = 2 AS 'El reintento duplicó viajes';
ASSERT (SELECT SUM(total_usd) FROM target_test) = 30 AS 'El reintento duplicó importes';
INSERT INTO staging_test SELECT * REPLACE ('other-hash' AS payload_hash, 'run2' AS batch_id)
FROM staging_test WHERE trip_id='a' LIMIT 1;
BEGIN
""" + conflict + """
  ASSERT FALSE AS 'Se permitió un conflicto';
EXCEPTION WHEN ERROR THEN
  ROLLBACK TRANSACTION;
  ASSERT @@error.message LIKE '%contradice%' AS 'Error inesperado en la prueba de conflicto';
END;
ASSERT (SELECT COUNT(*) FROM target_test) = 2 AS 'El conflicto modificó el destino';
SELECT COUNT(*) viajes, SUM(total_usd) total_usd FROM target_test;
"""
        job = client.query(script, location="us-central1", job_config=bigquery.QueryJobConfig(
            maximum_bytes_billed=512 * 1024**2))
        result = list(job.result())
        self.assertEqual((result[0].viajes, result[0].total_usd), (2, 30))
        evidence = {"job_id": job.job_id, "state": job.state,
                    "bytes_processed": job.total_bytes_processed,
                    "trip_count_after_retry_and_conflict": 2, "total_usd": 30,
                    "uses_temporary_tables": True}
        path = ROOT / "referencias_locales/terraform/prueba_merge.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
