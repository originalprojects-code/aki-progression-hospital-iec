"""Synthetic tests for Paper 1 scientific data contracts."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from aki_rebuild.contracts.v1 import (
    HISTORICAL_AUDIT_REFERENCES,
    ContractViolation,
    LaboratoryTiming,
    OriginalCohortSelection,
    PastHistoryTiming,
    RespiratoryTiming,
    assert_hospital_disjoint,
    assert_outer_test_excluded_from_fitting,
    in_predictor_window,
    in_primary_outcome_window,
    select_latest_revised_record,
)


ROOT = Path(__file__).resolve().parents[1]


class ScientificContractTests(unittest.TestCase):
    def test_predictor_landmark_boundaries_are_inclusive(self) -> None:
        self.assertFalse(in_predictor_window(-1))
        self.assertTrue(in_predictor_window(0))
        self.assertTrue(in_predictor_window(720))
        self.assertFalse(in_predictor_window(721))

    def test_primary_outcome_window_is_open_at_landmark_and_censored(self) -> None:
        self.assertFalse(in_primary_outcome_window(720, 5_000))
        self.assertTrue(in_primary_outcome_window(721, 5_000))
        self.assertTrue(in_primary_outcome_window(4_320, 5_000))
        self.assertFalse(in_primary_outcome_window(4_321, 5_000))
        self.assertTrue(in_primary_outcome_window(1_000, 1_000))
        self.assertFalse(in_primary_outcome_window(1_001, 1_000))

    def test_laboratory_revision_is_not_result_availability(self) -> None:
        late_revision = LaboratoryTiming(600, 900, None, lab_id=3)
        self.assertEqual(late_revision.revision_proxy_class, "revision_proxy_after_landmark")
        self.assertEqual(late_revision.availability_evidence, "unknown")

        selected = select_latest_revised_record(
            [LaboratoryTiming(600, 800, lab_id=1), LaboratoryTiming(600, 800, lab_id=2)]
        )
        self.assertEqual(selected.lab_id, 2)

    def test_history_and_respiratory_documentation_remain_distinct(self) -> None:
        history = PastHistoryTiming(600, 800)
        self.assertEqual(history.documentation_evidence, "documented_after_landmark")
        self.assertEqual(PastHistoryTiming(600, None).documentation_evidence, "unknown")

        respiratory = RespiratoryTiming(600, 800)
        self.assertEqual(respiratory.event_evidence, "event_at_or_before_landmark")
        self.assertEqual(respiratory.documentation_evidence, "documented_after_landmark")

    def test_reference_cohort_selection_and_primary_outcome_are_explicit(self) -> None:
        eligible = OriginalCohortSelection(
            adult=True,
            discharge_at_or_after_landmark=True,
            first_eligible_unit_stay=True,
            patient_seen_at_one_hospital=True,
            reference_creatinine_exists=True,
            maximum_kdigo_stage_before_landmark=1,
            strict_chronic_dialysis=False,
            acute_rrt_at_or_before_landmark=False,
            creatinine_outcome_observed=True,
        )
        self.assertTrue(eligible.is_eligible_main_cohort)
        self.assertEqual(eligible.primary_outcome_name, "creatinine_based_kdigo_stage_2_or_3")
        self.assertFalse(
            OriginalCohortSelection(
                **{**eligible.__dict__, "acute_rrt_at_or_before_landmark": True}
            ).is_eligible_main_cohort
        )

    def test_hospital_disjoint_and_fitting_guards(self) -> None:
        assert_hospital_disjoint({"A", "B"}, {"C"})
        with self.assertRaises(ContractViolation):
            assert_hospital_disjoint({"A", "B"}, {"B", "C"})

        assert_outer_test_excluded_from_fitting(
            {"H5"}, {"fit": {"H1"}, "held_out_evaluation": {"H5"}}
        )
        with self.assertRaises(ContractViolation):
            assert_outer_test_excluded_from_fitting(
                {"H5"}, {"preprocess_fit": {"H1", "H5"}}
            )

    def test_machine_readable_policies_and_references_are_non_targets(self) -> None:
        policy = json.loads((ROOT / "contracts" / "feature_timing_policy.v1.json").read_text())
        policy_ids = {item["policy_id"] for item in policy["policies"]}
        self.assertTrue({"LAB-001", "HISTORY-001", "RESP-001"} <= policy_ids)
        self.assertTrue(
            all(reference.interpretation.endswith("not_final_target") for reference in HISTORICAL_AUDIT_REFERENCES)
        )

        with (ROOT / "contracts" / "policy_traceability.v1.csv").open(newline="") as handle:
            traceability = list(csv.DictReader(handle))
        self.assertTrue(any(row["policy_id"] == "LAB-001" for row in traceability))


if __name__ == "__main__":
    unittest.main()
