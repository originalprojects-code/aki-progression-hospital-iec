"""Tests for the non-executing local reference SQL preflight."""

from __future__ import annotations

from pathlib import Path
import unittest

from aki_rebuild.config import REQUIRED_BILLING_LIMIT, RebuildConfig
from aki_rebuild.preflight import (
    build_reference_preflight_report,
    verify_reference_semantic_equivalence,
)
from aki_rebuild.reference_sql import validate_reference_config


ROOT = Path(__file__).resolve().parents[1]


def config(destination_dataset: str = "aki_paper1_rebuild_preflight") -> RebuildConfig:
    return RebuildConfig(
        source_project_id="physionet-data",
        source_dataset="eicu_crd",
        destination_project_id="test-project",
        destination_dataset=destination_dataset,
        run_id="preflight-test-001",
        landmark_hours=12,
        outcome_horizon_hours=72,
        maximum_bytes_billed=REQUIRED_BILLING_LIMIT,
    )


class ReferencePreflightTests(unittest.TestCase):
    def test_all_five_templates_are_equivalent_with_only_documented_exception(self) -> None:
        results = verify_reference_semantic_equivalence(ROOT / "sql", ROOT / "sql/rebuild/reference")
        self.assertTrue(all(result["equivalent"] for result in results))
        renal = next(result for result in results if result["stage"] == "renal_flags")
        self.assertEqual(renal["exceptions"], ["CHR(8)_represents_frozen_ASCII_backspace"])

    def test_preflight_renders_hashes_and_never_submits_a_job(self) -> None:
        report = build_reference_preflight_report(
            config=config(),
            repository=ROOT,
            frozen_directory=ROOT / "sql",
            reference_directory=ROOT / "sql/rebuild/reference",
        )
        self.assertTrue(report["execution_readiness"]["local_preflight_passed"])
        self.assertFalse(report["execution_readiness"]["real_execution_submitted"])
        self.assertFalse(report["execution_readiness"]["remote_dry_run_submitted"])
        stages = report["rendered_stages"]
        self.assertEqual(len(stages), 5)
        self.assertTrue(all(stage["contains_create_or_replace"] for stage in stages))
        self.assertTrue(all(stage["destination_identifier_present"] for stage in stages))

    def test_production_or_non_dedicated_destination_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "original production/audit"):
            validate_reference_config(config("aki_jcmc_v2"))
        with self.assertRaisesRegex(ValueError, "dedicated destination"):
            validate_reference_config(config("some_shared_dataset"))


if __name__ == "__main__":
    unittest.main()
