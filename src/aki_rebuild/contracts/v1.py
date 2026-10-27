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
class SourceTimestampPolicy:
    """Frozen source-SQL timestamp semantics for one data source.

    These are reference semantics only.  They do not approve a corrected
    availability policy, particularly when a source permits negative offsets.
    """

    source: str
    lower_bound_minutes: int | None
    upper_bound_minutes: int
    source_semantics: str
    corrected_policy_status: str = "requires_researcher_approval"


SOURCE_TIMESTAMP_POLICIES = {
    "laboratory_feature_reference": SourceTimestampPolicy(
        "laboratory_feature_reference", 0, LANDMARK_MINUTES, "sql/07_feature_labs.sql"
    ),
    "past_history_reference": SourceTimestampPolicy(
        "past_history_reference", None, LANDMARK_MINUTES, "sql/03_renal_flags.sql; sql/09_feature_context.sql"
    ),
    "respiratory_event_reference": SourceTimestampPolicy(
        "respiratory_event_reference", 0, LANDMARK_MINUTES, "sql/09_feature_context.sql"
    ),
    "respiratory_documentation_reference": SourceTimestampPolicy(
        "respiratory_documentation_reference", 0, LANDMARK_MINUTES, "sql/09_feature_context.sql"
    ),
    "infusion_reference": SourceTimestampPolicy(
        "infusion_reference", 0, LANDMARK_MINUTES, "sql/09_feature_context.sql"
    ),
    "treatment_reference": SourceTimestampPolicy(
        "treatment_reference", 0, LANDMARK_MINUTES, "sql/09_feature_context.sql"
    ),
}


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


def reference_timestamp_eligibility(source: str, offset_minutes: int | None) -> str:
    """Classify a timestamp under its frozen, source-specific SQL semantics.

    The result is deliberately descriptive rather than a corrected feature-use
    decision.  In particular, a negative past-history offset is reference-eligible
    while a negative laboratory feature offset is reference-ineligible.
    """

    try:
        policy = SOURCE_TIMESTAMP_POLICIES[source]
    except KeyError as error:
        raise ContractViolation(f"Unknown timestamp source: {source}") from error
    if offset_minutes is None:
        return "missing_timestamp"
    if policy.lower_bound_minutes is not None and offset_minutes < policy.lower_bound_minutes:
        return "reference_ineligible"
    if offset_minutes > policy.upper_bound_minutes:
        return "reference_ineligible"
    return "reference_eligible"


def in_predictor_window(offset_minutes: int | None) -> bool:
    """Compatibility helper for sources whose frozen rule is inclusive [0, 720].

    New contracts must call :func:`reference_timestamp_eligibility` with an
    explicit source instead of applying this generic rule to all data sources.
    """

    return reference_timestamp_eligibility("laboratory_feature_reference", offset_minutes) == "reference_eligible"


def in_primary_outcome_window(offset_minutes: int, discharge_offset_minutes: int) -> bool:
    """Return whether time is in the censored primary outcome window (720, 4320]."""

    censor_offset = min(discharge_offset_minutes, OUTCOME_HORIZON_MINUTES)
    return LANDMARK_MINUTES < offset_minutes <= censor_offset


@dataclass(frozen=True)
class LaboratoryGroupingKey:
    """The audited deduplication partition: stay, analyte, and sample offset."""

    patient_stay_key: str
    analyte: str
    sample_offset_minutes: int

    def __post_init__(self) -> None:
        if not self.patient_stay_key or not self.analyte:
            raise ContractViolation("Laboratory grouping requires a stay key and analyte.")


@dataclass(frozen=True)
class LaboratoryTiming:
    """Timing evidence for one laboratory record.

    ``result_available_offset_minutes`` is intentionally optional.  A revision
    timestamp is not evidence of the first time a result was available.
    """

    grouping_key: LaboratoryGroupingKey
    sample_offset_minutes: int | None
    revision_offset_minutes: int | None
    result_available_offset_minutes: int | None = None
    lab_id: int = 0

    @property
    def revision_proxy_offset_minutes(self) -> int:
        """Match the audited source SQL fallback: revision time, then sample time."""

        if self.sample_offset_minutes is None:
            raise ContractViolation("Laboratory revision selection requires a sample offset.")
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


def select_latest_revised_record(
    records: Iterable[LaboratoryTiming], expected_group: LaboratoryGroupingKey
) -> LaboratoryTiming:
    """Select one record using the audited SQL's revision/sample and lab-ID ordering.

    This is a reference-definition helper, not a statement about first-result
    availability for feature use.
    """

    values = tuple(records)
    if not values:
        raise ContractViolation("At least one laboratory record is required.")
    for record in values:
        if record.grouping_key != expected_group:
            raise ContractViolation(
                "Laboratory revision selection cannot mix stays, analytes, or sample offsets."
            )
        if record.sample_offset_minutes != expected_group.sample_offset_minutes:
            raise ContractViolation("Laboratory record sample offset disagrees with grouping key.")
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
    """Check declared usage excludes held-out hospitals from protected stages.

    This is an in-memory contract assertion, not runtime leakage protection.
    Actual model pipeline integration and pipeline-level tests are still required.
    """

    protected_roles = {
        "feature_definition_fit",
        "feature_selection",
        "missingness_rule_fit",
        "imputation_fit",
        "encoding_fit",
        "scaling_fit",
        "outlier_rule_fit",
        "preprocess_fit",
        "model_fit",
        "early_stopping_selection",
        "hyperparameter_tuning",
        "calibration_fit",
        "ensemble_weight_fit",
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
