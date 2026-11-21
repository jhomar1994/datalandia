"""Prueba el orden y las puertas de consolidación sin utilizar GCP."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import prueba_escala as workflow


class ScaleWorkflowTests(unittest.TestCase):
    def scenario(self, state):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = root / ".venv_bigdata/bin/python"
            python.parent.mkdir(parents=True)
            python.touch()
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "manifest.json").write_text(json.dumps({"counts": {"viajes": 1000000}, "bundle_id": "test"}))
            calls = []

            def fake_run(command):
                calls.append(str(command[1]))
                if command[1] == "scripts/stage_inputs.py":
                    report = command[command.index("--report") + 1]
                    report.write_text(json.dumps({"uris": {"viajes.jsonl": "gs://test/trips"}}))
                if command[1] == "scripts/run_dataflow.py":
                    name = command[command.index("--name") + 1]
                    report = root / "referencias_locales/dataflow" / name / "result.json"
                    report.parent.mkdir(parents=True)
                    report.write_text(json.dumps({"final_state": state, "shutdown_confirmed": True, "error": None}))

            with patch.object(workflow, "ROOT", root), patch.object(workflow, "run", side_effect=fake_run), \
                 patch.object(workflow, "verify_idle", return_value={"active_jobs_in_region": 0, "vms_in_project": 0}) as idle, \
                 contextlib.redirect_stdout(io.StringIO()):
                if state == "JOB_STATE_DONE":
                    workflow.execute(bundle, 1000000, 2, 30)
                    self.assertEqual(calls[-1], "scripts/finalize_batch.py")
                else:
                    with self.assertRaises(RuntimeError):
                        workflow.execute(bundle, 1000000, 2, 30)
                    self.assertNotIn("scripts/finalize_batch.py", calls)
                self.assertEqual(idle.call_count, 2)
                report = next((root / "referencias_locales/escala").glob("*/resultado.json"))
                self.assertIn("shutdown", json.loads(report.read_text()))

    def test_done_allows_merge(self):
        self.scenario("JOB_STATE_DONE")

    def test_cancelled_and_failed_never_merge(self):
        for state in ("JOB_STATE_CANCELLED", "JOB_STATE_FAILED"):
            with self.subTest(state=state):
                self.scenario(state)


if __name__ == "__main__":
    unittest.main()
