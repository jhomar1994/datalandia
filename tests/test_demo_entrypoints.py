"""Contrato de volumen de las demos, sin publicar mensajes ni crear workers."""
import contextlib
import io
import unittest
from unittest.mock import patch

from scripts import demo_batch, demo_streaming, demo_e2e


class DemoEntrypointsTests(unittest.TestCase):
    def test_batch_defaults_and_volume_forwarded(self):
        with patch.object(demo_batch, "execute") as execute:
            demo_batch.main([])
            self.assertEqual(execute.call_args.args[1:], (10000, 2, 15))
            demo_batch.main(["--records", "25000", "--workers", "1"])
            self.assertEqual(execute.call_args.args[1:], (25000, 1, 15))
            self.assertEqual(execute.call_args.args[0].name, "demo_batch_25000")

    def test_streaming_volume_and_rate_forwarded(self):
        with patch.object(demo_e2e, "main") as main:
            demo_streaming.main([])
            args = demo_e2e.parse_args(main.call_args.args[0])
            self.assertEqual((args.live_events, args.rate), (60, 1))
            demo_streaming.main(["--events", "300", "--rate", "5"])
            args = demo_e2e.parse_args(main.call_args.args[0])
            self.assertEqual((args.live_events, args.rate), (300, 5))

    def test_legacy_visible_seconds_remains_supported(self):
        args = demo_e2e.parse_args(["--visible-seconds", "30"])
        self.assertEqual((args.live_events, args.rate), (30, 1))

    def test_invalid_sizes_and_duration_rejected_before_cloud(self):
        for argv in (["--events", "0"], ["--events", "10001"],
                     ["--events", "300", "--rate", "1"],
                     ["--events", "60", "--rate", "0"],
                     ["--events", "30", "--visible-seconds", "30"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    demo_e2e.parse_args(argv)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            demo_batch.parse_args(["--records", "0"])


if __name__ == "__main__":
    unittest.main()
