"""Paper 1 scientific data contracts, version 1.

These contracts encode audited invariants using only synthetic, in-memory values.
They do not query BigQuery, load patient-level data, or declare a corrected cohort.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


CONTRACT_VERSION = "1.0.0"
LANDMARK_MINUTES = 720
OUTCOME_HORIZON_MINUTES = 4320
PRIMARY_OUTCOME_NAME = "creatinine_based_kdigo_stage_2_or_3"


class ContractViolation(ValueError):
    """Raised when a declared scientific invariant is violated."""


@dataclass(frozen=True)
class HistoricalAuditReference:
    """A historical count reference, explicitly not a corrected-cohort target."""

    label: str
    patients: int
    events: int
    hospitals: int
    interpretation: str = "historical_audit_reference_not_final_target"


HISTORICAL_AUDIT_REFERENCES = (
    HistoricalAuditReference("original_reported", 58_491, 3_032, 198),
    HistoricalAuditReference("original_code_rebuild", 59_612, 3_060, 199),
)


def in_predictor_window(offset_minutes: int) -> bool:
    """Return whether an event is in the inclusive [0, 720] predictor window."""

    return 0 <= offset_minutes <= LANDMARK_MINUTES


def in_primary_outcome_window(offset_minutes: int, discharge_offset_minutes: int) -> bool:
    """Return whether time is in the censored primary outcome window (720, 4320]."""

    censor_offset = min(discharge_offset_minutes, OUTCOME_HORIZON_MINUTES)
    return LANDMARK_MINUTES < offset_minutes <= censor_offset


@dataclass(frozen=True)
class LaboratoryTiming:
    """Timing evidence for one laboratory record.

    ``result_available_offset_minutes`` is intentionally optional.  A revision
    timestamp is not evidence of the first time a result was available.
    """

    sample_offset_minutes: int
    revision_offset_minutes: int | None
    result_available_offset_minutes: int | None = None
    lab_id: int = 0

    @property
    def revision_proxy_offset_minutes(self) -> int:
        """Match the audited source SQL fallback: revision time, then sample time."""

        return (
            self.revision_offset_minutes
            if self.revision_offset_minutes is not None
            else self.sample_offset_minutes
        )

    @property
    def availability_evidence(self) -> str:
        """Classify known availability without inferring it from a revision time."""

        if self.result_available_offset_minutes is None:
            return "unknown"
        if self.result_available_offset_minutes <= LANDMARK_MINUTES:
            return "known_at_or_before_landmark"
        return "known_after_landmark"

    @property
    def revision_proxy_class(self) -> str:
        if self.revision_proxy_offset_minutes <= LANDMARK_MINUTES:
            return "revision_proxy_at_or_before_landmark"
        return "revision_proxy_after_landmark"


def select_latest_revised_record(records: Iterable[LaboratoryTiming]) -> LaboratoryTiming:
    """Select one record using the audited SQL's revision/sample and lab-ID ordering.

    This is a reference-definition helper, not a statement about first-result
    availability for feature use.
    """

    values = tuple(records)
    if not values:
        raise ContractViolation("At least one laboratory record is required.")
    return max(values, key=lambda record: (record.revision_proxy_offset_minutes, record.lab_id))


@dataclass(frozen=True)
class PastHistoryTiming:
    """Keep event and documentation times distinct for past-history features."""

    past_history_offset_minutes: int
    past_history_entered_offset_minutes: int | None

    @property
    def documentation_evidence(self) -> str:
        if self.past_history_entered_offset_minutes is None:
            return "unknown"
        if self.past_history_entered_offset_minutes <= LANDMARK_MINUTES:
            return "documented_at_or_before_landmark"
        return "documented_after_landmark"


@dataclass(frozen=True)
class RespiratoryTiming:
    """Keep ventilation event timing separate from respiratory documentation timing."""

    ventilation_event_offset_minutes: int | None
    documentation_offset_minutes: int | None

    @property
    def event_evidence(self) -> str:
        if self.ventilation_event_offset_minutes is None:
            return "unknown"
        if self.ventilation_event_offset_minutes <= LANDMARK_MINUTES:
            return "event_at_or_before_landmark"
        return "event_after_landmark"

    @property
    def documentation_evidence(self) -> str:
        if self.documentation_offset_minutes is None:
            return "unknown"
        if self.documentation_offset_minutes <= LANDMARK_MINUTES:
            return "documented_at_or_before_landmark"
        return "documented_after_landmark"


@dataclass(frozen=True)
class OriginalCohortSelection:
    """Separately testable reference selection invariants from the frozen SQL."""

    adult: bool
    discharge_at_or_after_landmark: bool
    first_eligible_unit_stay: bool
    patient_seen_at_one_hospital: bool
    reference_creatinine_exists: bool
    maximum_kdigo_stage_before_landmark: int
    strict_chronic_dialysis: bool
    acute_rrt_at_or_before_landmark: bool
    creatinine_outcome_observed: bool

    @property
    def is_eligible_main_cohort(self) -> bool:
        return (
            self.adult
            and self.discharge_at_or_after_landmark
            and self.first_eligible_unit_stay
            and self.patient_seen_at_one_hospital
            and self.reference_creatinine_exists
            and self.maximum_kdigo_stage_before_landmark < 2
            and not self.strict_chronic_dialysis
            and not self.acute_rrt_at_or_before_landmark
            and self.creatinine_outcome_observed
        )

    @property
    def primary_outcome_name(self) -> str:
        """The primary label is creatinine based; RRT composite is not substituted."""

        return PRIMARY_OUTCOME_NAME


def assert_hospital_disjoint(
    training_hospitals: Iterable[str], held_out_hospitals: Iterable[str]
) -> None:
    """Reject a hospital appearing in both outer training and test partitions."""

    overlap = set(training_hospitals) & set(held_out_hospitals)
    if overlap:
        raise ContractViolation(f"Outer hospital overlap: {sorted(overlap)}")


def assert_outer_test_excluded_from_fitting(
    outer_test_hospitals: Iterable[str],
    usage_hospitals: Mapping[str, Iterable[str]],
) -> None:
    """Reject use of held-out hospitals for any fitting or selection activity."""

    protected_roles = {
        "fit",
        "preprocess_fit",
        "hyperparameter_tuning",
        "calibration_fit",
        "threshold_selection",
    }
    outer_test = set(outer_test_hospitals)
    for role, hospitals in usage_hospitals.items():
        if role not in protected_roles:
            continue
        overlap = outer_test & set(hospitals)
        if overlap:
            raise ContractViolation(
                f"Held-out hospitals used for {role}: {sorted(overlap)}"
            )
