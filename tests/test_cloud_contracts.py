"""Pruebas de reglas que evitan resultados erróneos o fallos de replay."""
import datetime as dt
import json
import unittest

from pipelines.cloud.sql_utils import render_sql
from pipelines.cloud.validaciones import InvalidEvent, digest, reject, validate_sensor, validate_trip

UTC = dt.timezone.utc
START = dt.datetime(2024, 1, 1, 5, tzinfo=UTC)
END = START + dt.timedelta(days=1)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.trip = dict(trip_id="source-row-0", origin_id=132, destination_id=41,
                         pickup_local="2024-01-01T00:00:00", dropoff_local="2024-01-01T00:10:00",
                         distance_miles=2, total_usd=10)
        self.event = dict(event_id="event-1", node_id="node-a", subsystem="weather", sensor="temp",
                          parameter="temperature", unit="C", value=12,
                          original_ts="2018-01-01T05:00:00Z", event_ts="2024-01-01T05:00:00Z",
                          published_at="2026-11-20T08:00:00Z")
        self.nodes = {"node-a": "DL-132", "node-b": "DL-237"}
        self.catalog = {("weather", "temp", "temperature"): {"unit": "C", "min_value": -30, "max_value": 60}}

    def sensor(self, **changes):
        return validate_sensor(json.dumps(dict(self.event, **changes)), self.nodes, self.catalog, START, END)

    def test_numeric_json_containers_are_quarantinable(self):
        for raw in ["null", "[]", "42", "true", "not-json"]:
            with self.subTest(raw=raw), self.assertRaises(InvalidEvent):
                validate_trip(raw)

    def test_trip_identity_preserves_distinct_source_rows(self):
        a = validate_trip(json.dumps(self.trip))
        b = validate_trip(json.dumps(dict(self.trip, trip_id="source-row-1")))
        self.assertNotEqual(a["trip_id"], b["trip_id"])
        self.assertAlmostEqual(a["distance_km"], 3.218688)

    def test_trip_hash_stable_on_retry(self):
        self.assertEqual(validate_trip(json.dumps(self.trip)), validate_trip(json.dumps(self.trip)))

    def test_invalid_trip_rules(self):
        cases = [dict(origin_id=1.5), dict(origin_id=True), dict(total_usd=0),
                 dict(distance_miles="NaN"), dict(dropoff_local="2024-01-01T00:00:00"),
                 dict(pickup_local="2024-02-01T00:00:00"), dict(trip_id=""),
                 dict(pickup_local="2024-01-01T00:00:00Z")]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(InvalidEvent):
                validate_trip(json.dumps(dict(self.trip, **change)))

    def test_second_mapped_node_is_accepted(self):
        self.assertEqual(self.sensor(node_id="node-b")["zone_id"], "DL-237")

    def test_sensor_retry_ignores_publication_time(self):
        self.assertEqual(self.sensor()["payload_hash"], self.sensor(published_at="2026-11-21T08:00:00Z")["payload_hash"])

    def test_sensor_content_conflict_changes_hash(self):
        self.assertNotEqual(self.sensor()["payload_hash"], self.sensor(value=13)["payload_hash"])

    def test_physical_outlier_is_flagged(self):
        self.assertTrue(self.sensor(value=100)["out_of_range"])

    def test_sensor_invalid_cases(self):
        for change in [dict(node_id="unknown"), dict(unit="F"), dict(sensor="unknown"),
                       dict(value=True), dict(value="Infinity"), dict(value="error"),
                       dict(event_ts="2024-01-02T05:00:00Z", original_ts="2018-01-02T05:00:00Z"),
                       dict(published_at="2026-11-20T08:00:00"), dict(original_ts="2018-01-01T04:00:00Z")]:
            with self.subTest(change=change), self.assertRaises(InvalidEvent):
                self.sensor(**change)

    def test_rejection_identity_is_retry_stable(self):
        a = reject("sensor", "unit", json.dumps(self.event))
        b = reject("sensor", "unit", json.dumps(dict(self.event, published_at="2026-11-21T08:00:00Z")))
        self.assertEqual(a["rejection_id"], b["rejection_id"])

    def test_sql_identifiers_reject_injection(self):
        with self.assertRaises(ValueError):
            render_sql("finalizar_batch.sql", "bad-project`", "lumina_demo")
        with self.assertRaises(ValueError):
            render_sql("finalizar_batch.sql", "proyecto-datalandia", "demo;DROP")

    def test_merge_uses_data_parameter(self):
        sql = render_sql("finalizar_batch.sql", "proyecto-datalandia", "lumina_demo")
        self.assertIn("@batch_id", sql)
        self.assertNotIn("__PROJECT__", sql)


if __name__ == "__main__":
    unittest.main()
