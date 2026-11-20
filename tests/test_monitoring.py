"""Contrato nuevo, vacío, reloj fuera de caché y reutilización de consulta entre rutas."""
import datetime as dt
import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app.main import create_app
from api.app.monitoring import MonitoringRepository
from api.app.settings import Settings

UTC = dt.timezone.utc


def empty_row():
    return dict(aceptadas=0,rechazadas=0,zonas_activas=0,ultima_ingesta=None,ingestion_seconds=None,
                ventana_inicio=None,zones_json=[],minutes_json=[],latest_json=None,rejections_json=[])


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        self.repo=MonitoringRepository(Settings(cache_ttl=60))
        self.row=empty_row()
        self.mock=patch.object(self.repo,'query',side_effect=lambda *a,**k:[dict(self.row)]).start()
        self.addCleanup(patch.stopall)
        self.client=TestClient(create_app(repository=self.repo))

    def test_empty_tables_and_shared_cache(self):
        for route in ['/kpis','/latencia','/zonas','/rechazos','/eventos/ultimo','/eventos/por-minuto?min=15']:
            self.assertEqual(self.client.get(route).status_code,200,route)
        self.assertEqual(self.mock.call_count,1)
        self.assertEqual(self.client.get('/eventos/ultimo').json(),{})
        self.assertIsNone(self.client.get('/kpis').json()['latencia_e2e_s'])
        self.assertEqual(self.client.get('/zonas').json()['zonas'],[])
        self.assertEqual(self.client.get('/rechazos').json(),{'rechazos':[]})
        self.assertEqual(self.client.get('/ventanas').status_code,404)

    def test_minutes_exact_order_and_current_minute(self):
        now=dt.datetime.now(UTC).replace(second=0,microsecond=0)
        stamp=now.isoformat().replace('+00:00','Z')
        self.row['minutes_json']=[json.dumps({'minuto':stamp,'aceptadas':3,'rechazadas':1})]
        for size in (1,15,60):
            rows=self.client.get('/eventos/por-minuto',params={'min':size}).json()['minutos']
            self.assertEqual(len(rows),size)
            self.assertEqual(rows[-1],{'minuto':stamp,'aceptadas':3,'rechazadas':1})
            self.assertEqual([r['minuto'] for r in rows],sorted(r['minuto'] for r in rows))
            self.assertTrue(all(r['aceptadas']==0 for r in rows[:-1]))
        for route in ['/eventos/por-minuto?min=0','/eventos/por-minuto?min=61','/rechazos?limit=51']:
            self.assertEqual(self.client.get(route).status_code,422)

    def test_clock_is_fresh_and_payload_is_not_exposed(self):
        self.row['latest_json']=json.dumps({'event_id':'test','value':1.0})
        self.row['rejections_json']=[json.dumps({'processed_at':'2026-11-20T10:00:00Z','motivo':'valor_no_numerico',
          'raw_payload':json.dumps({'node_id':'x'*200,'sensor':'abc','secret':'must-not-appear'})})]
        a=self.client.get('/eventos/ultimo').json();b=self.client.get('/eventos/ultimo').json()
        self.assertGreater(b['ahora'],a['ahora'])
        self.assertEqual(self.mock.call_count,1)
        reject=self.client.get('/rechazos').json()['rechazos'][0]
        self.assertLessEqual(len(reject['detalle']),80)
        self.assertNotIn('must-not-appear',json.dumps(reject))
        self.assertNotIn('raw_payload',reject)


if __name__=='__main__':unittest.main()
