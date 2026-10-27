"""Local, synthetic validation of the five-stage reference cohort SQL plan."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from aki_rebuild.config import REQUIRED_BILLING_LIMIT, RebuildConfig
from aki_rebuild.reference_sql import (
    REFERENCE_STAGES,
    build_reference_run_manifest,
    guarded_reference_dry_run,
    in_reference_creatinine_outcome_window,
    optional_guarded_reference_dry_run,
    plan_reference_pipeline,
    reference_revision_order_key,
    reference_stay_order_key,
    render_reference_template,
    submit_reference_plan,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIRECTORY = ROOT / "sql" / "rebuild" / "reference"


class RecordingGuard:
    """Credential-free guard double; no query client or network is used."""

    def __init__(self) -> None:
        self.estimated: list[str] = []
        self.submitted: list[str] = []

    def estimate(self, sql: str) -> str:
        self.estimated.append(sql)
        return "dry-run-estimate"

    def run(self, sql: str) -> str:
        self.submitted.append(sql)
        return "guarded-job"


def reference_config() -> RebuildConfig:
    return RebuildConfig(
        source_project_id="physionet-data",
        source_dataset="eicu_crd",
        destination_project_id="test-project",
        destination_dataset="aki_paper1_rebuild_test",
        run_id="reference-test-001",
        landmark_hours=12,
        outcome_horizon_hours=72,
        maximum_bytes_billed=REQUIRED_BILLING_LIMIT,
    )


class ReferenceCohortSqlTests(unittest.TestCase):
    def test_rendering_replaces_only_validated_identifier_tokens(self) -> None:
        plan = plan_reference_pipeline(reference_config(), TEMPLATE_DIRECTORY)
        self.assertEqual([query.stage.name for query in plan], [stage.name for stage in REFERENCE_STAGES])
        self.assertTrue(all("{{" not in query.sql for query in plan))
        self.assertIn("`physionet-data.eicu_crd.patient`", plan[0].sql)
        self.assertIn("`test-project.aki_paper1_rebuild_test.base_stays_v1`", plan[0].sql)
        unsafe = RebuildConfig(
            source_project_id="physionet-data",
            source_dataset="eicu_crd; DROP SCHEMA x",
            destination_project_id="test-project",
            destination_dataset="aki_paper1_rebuild_test",
            run_id="reference-test-001",
            landmark_hours=12,
            outcome_horizon_hours=72,
            maximum_bytes_billed=REQUIRED_BILLING_LIMIT,
        )
        with self.assertRaisesRegex(ValueError, "source dataset"):
            render_reference_template("SELECT '{{SOURCE_DATASET}}'", unsafe)

    def test_dependencies_and_reference_manifest_are_complete(self) -> None:
        plan_metadata = json.loads(
            (ROOT / "contracts" / "reference_cohort_execution_plan.v1.json").read_text()
        )
        self.assertEqual(plan_metadata["execution_status"], "not_executed")
        self.assertEqual(plan_metadata["historical_comparison"]["patients"], 59_612)
        self.assertIn("not_final_corrected_target", plan_metadata["historical_comparison"]["interpretation"])

        manifest = build_reference_run_manifest(
            config=reference_config(), repository=ROOT, template_directory=TEMPLATE_DIRECTORY
        )
        self.assertEqual(manifest["execution"]["status"], "reference_plan_not_executed")
        self.assertEqual(len(manifest["sql_sha256"]), 5)

    def test_every_planned_stage_uses_the_guard_interface(self) -> None:
        plan = plan_reference_pipeline(reference_config(), TEMPLATE_DIRECTORY)
        guard = RecordingGuard()
        estimates = guarded_reference_dry_run(plan, guard)  # type: ignore[arg-type]
        self.assertEqual(set(estimates), {stage.name for stage in REFERENCE_STAGES})
        self.assertEqual(len(guard.estimated), 5)
        self.assertEqual(guard.submitted, [])

        jobs = submit_reference_plan(plan, guard)  # type: ignore[arg-type]
        self.assertEqual(jobs, ["guarded-job"] * 5)
        self.assertEqual(len(guard.submitted), 5)

    def test_optional_remote_dry_run_requires_explicit_approval_and_never_runs_jobs(self) -> None:
        plan = plan_reference_pipeline(reference_config(), TEMPLATE_DIRECTORY)
        guard = RecordingGuard()
        with self.assertRaises(PermissionError):
            optional_guarded_reference_dry_run(plan, guard)  # type: ignore[arg-type]
        self.assertEqual(guard.estimated, [])
        self.assertEqual(guard.submitted, [])
        optional_guarded_reference_dry_run(
            plan, guard, explicit_remote_approval=True  # type: ignore[arg-type]
        )
        self.assertEqual(len(guard.estimated), 5)
        self.assertEqual(guard.submitted, [])

    def test_synthetic_landmark_and_outcome_window_boundaries(self) -> None:
        self.assertFalse(in_reference_creatinine_outcome_window(720, 5_000))
        self.assertTrue(in_reference_creatinine_outcome_window(721, 5_000))
        self.assertTrue(in_reference_creatinine_outcome_window(4_320, 5_000))
        self.assertFalse(in_reference_creatinine_outcome_window(4_321, 5_000))
        self.assertTrue(in_reference_creatinine_outcome_window(1_000, 1_000))
        self.assertFalse(in_reference_creatinine_outcome_window(1_001, 1_000))

    def test_synthetic_stay_selection_and_revision_ordering(self) -> None:
        stays = [(None, 8), (2, 9), (2, 3)]
        self.assertEqual(min(stays, key=lambda item: reference_stay_order_key(*item)), (2, 3))

        revisions = [(None, 600, 20), (800, 600, 1), (800, 600, 4)]
        self.assertEqual(
            max(revisions, key=lambda item: reference_revision_order_key(*item)), (800, 600, 4)
        )

    def test_reference_sql_keeps_primary_creatinine_label_and_censoring_text(self) -> None:
        cohort_sql = (TEMPLATE_DIRECTORY / "05_cohort_outcome.sql").read_text(encoding="utf-8")
        self.assertIn("s.labResultOffset > 720", cohort_sql)
        self.assertIn("LEAST(b.unitDischargeOffset,4320)", cohort_sql)
        self.assertIn("AND outcome_creatinine_stage23 IS NOT NULL", cohort_sql)
        self.assertIn("outcome_stage23_or_strict_rrt", cohort_sql)


if __name__ == "__main__":
    unittest.main()
