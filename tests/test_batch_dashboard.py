import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.app.main import create_app
from api.app.monitoring import MonitoringRepository
from api.app.settings import Settings
from api.app.repository import DataUnavailable
from scripts.batch_status import BatchStatus


class BatchDashboardTests(unittest.TestCase):
    def test_empty_and_completed_batch_and_cache(self):
        repo = MonitoringRepository(Settings())
        client = TestClient(create_app(repository=repo))
        with patch.object(repo, 'query', return_value=[]) as query:
            self.assertEqual(client.get('/batch/ultimo').json(), {})
            self.assertEqual(client.get('/batch/ultimo').status_code, 200)
            self.assertEqual(query.call_count, 1)
        repo._cache.clear()
        row = dict(batch_id='batch-1', estado='JOB_STATE_DONE', entradas=10000,
                   validos=8459, rechazados=1541, zonas=255, consolidado=False)
        with patch.object(repo, 'query', return_value=[row]):
            self.assertEqual(client.get('/batch/ultimo').json(), row)

    def test_unavailable_is_not_presented_as_empty(self):
        repo = MonitoringRepository(Settings())
        with patch.object(repo, 'query', side_effect=DataUnavailable('Temporalmente no disponible')):
            self.assertEqual(TestClient(create_app(repository=repo)).get('/batch/ultimo').status_code, 503)

    def test_counts_scoped_to_job_and_unknown_counts_stay_null(self):
        with patch('google.cloud.bigquery.Client'):
            reporter = BatchStatus('batch-1', 10000, 2)
        with patch.object(reporter, 'query', return_value=[]) as query:
            reporter.update('JOB_STATE_RUNNING', 'job-1')
            params = {p.name: p.value for p in query.call_args.args[1]}
            self.assertIsNone(params['accepted'])
            self.assertEqual(params['expected_records'], 10000)
        with patch.object(reporter, 'query', side_effect=[iter([{'accepted': 8459, 'rejected': 1541, 'zones': 255}]), []]) as query:
            reporter.update('JOB_STATE_DONE', 'job-1', counts=True)
            sql, params = query.call_args_list[0].args
            self.assertIn('batch_id=@batch_id', sql)
            self.assertIn('COUNT(DISTINCT trip_id)', sql)
            self.assertIn('COUNT(DISTINCT rejection_id)', sql)
            self.assertEqual(params[0].value, 'batch-1')
            self.assertEqual(reporter.values['accepted'], 8459)
            self.assertFalse(reporter.values['consolidated'])


if __name__ == '__main__':
    unittest.main()
