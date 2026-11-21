"""Límites de recursos antes de autenticación, lecturas de estado o creación de jobs."""
import contextlib
import io
import unittest

from scripts.run_dataflow import parse_args


class LauncherLimitsTests(unittest.TestCase):
    def test_existing_demo_defaults(self):
        args = parse_args(["--mode", "stream"])
        self.assertEqual((args.workers, args.max_minutes), (1, 12))

    def test_scale_batch_configuration(self):
        args = parse_args(["--mode", "batch", "--input", "gs://test/trips.jsonl",
                           "--workers", "2", "--max-minutes", "30",
                           "--staging-report", "custom/staging.json"])
        self.assertEqual((args.workers, args.max_minutes), (2, 30))
        self.assertEqual(str(args.staging_report), "custom/staging.json")

    def test_reject_resource_expansion_outside_limits(self):
        cases = [
            ["--mode", "stream", "--workers", "2"],
            ["--mode", "stream", "--max-minutes", "16"],
            ["--mode", "batch", "--input", "gs://test/trips", "--workers", "4"],
            ["--mode", "batch", "--input", "gs://test/trips", "--workers", "0"],
            ["--mode", "batch", "--input", "gs://test/trips", "--max-minutes", "46"],
            ["--mode", "batch", "--input", "gs://test/trips", "--max-minutes", "2"],
            ["--mode", "batch"],
        ]
        for argv in cases:
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    parse_args(argv)
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
