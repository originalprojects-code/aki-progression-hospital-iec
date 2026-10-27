from pathlib import Path
import subprocess
import unittest

from aki_rebuild.config import RebuildConfig, REQUIRED_BILLING_LIMIT
from aki_rebuild.manifest import ExecutionMetadata, build_manifest


class ManifestTests(unittest.TestCase):
    def test_manifest_records_local_provenance_without_execution(self):
        # Use unittest's standard-library temporary directory support.
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_path:
            sql_file = Path(temporary_path) / "example.sql"
            sql_file.write_text("SELECT 1;\n", encoding="utf-8")
            config = RebuildConfig(
                project_id="test-project",
                source_dataset="physionet-data.eicu_crd",
                destination_dataset="aki_rebuild_test",
                run_id="unit-test",
                landmark_hours=12,
                outcome_horizon_hours=72,
                maximum_bytes_billed=REQUIRED_BILLING_LIMIT,
            )
            repository = Path(__file__).resolve().parents[1]
            expected_commit = subprocess.check_output(
                ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
            ).strip()

            manifest = build_manifest(
                config=config,
                repository=repository,
                sql_files=[sql_file],
                execution=ExecutionMetadata(
                    run_id="unit-test", status="not_executed", started_at_utc="2026-01-01T00:00:00+00:00"
                ),
            )

        self.assertEqual(manifest["code_commit"], expected_commit)
        self.assertEqual(manifest["configuration_sha256"], config.sha256())
        self.assertEqual(manifest["execution"]["status"], "not_executed")
        self.assertTrue(manifest["sql_sha256"])
