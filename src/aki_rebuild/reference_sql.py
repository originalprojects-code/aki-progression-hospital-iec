"""Local-only planning and rendering for the frozen Paper 1 reference cohort.

This module never creates a BigQuery client.  If an authorized caller later
submits a rendered plan, every stage is routed through ``BigQueryExecutionGuard``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from .config import RebuildConfig
from .manifest import ExecutionMetadata, build_manifest
from .query_guard import BigQueryExecutionGuard, QueryEstimate


_PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_DATASET_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,1023}$")
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


@dataclass(frozen=True)
class ReferenceStage:
    name: str
    filename: str
    depends_on: tuple[str, ...]
    output_table: str


REFERENCE_STAGES = (
    ReferenceStage("base_stays", "01_base_stays.sql", (), "base_stays_v1"),
    ReferenceStage(
        "creatinine_long", "02_creatinine_long.sql", ("base_stays",), "creatinine_long_v1"
    ),
    ReferenceStage("renal_flags", "03_renal_flags.sql", ("base_stays",), "renal_flags_v1"),
    ReferenceStage(
        "creatinine_staged",
        "04_creatinine_staged.sql",
        ("base_stays", "creatinine_long"),
        "creatinine_staged_v1",
    ),
    ReferenceStage(
        "cohort_outcome",
        "05_cohort_outcome.sql",
        ("base_stays", "renal_flags", "creatinine_staged"),
        "cohort_outcome_v1",
    ),
)


@dataclass(frozen=True)
class PlannedReferenceQuery:
    stage: ReferenceStage
    template_path: Path
    sql: str


def _validate_identifier(value: str, pattern: re.Pattern[str], label: str) -> None:
    if not pattern.fullmatch(value):
        raise ValueError(f"Invalid {label}; SQL identifiers are not interpolated unchecked.")


def validate_reference_config(config: RebuildConfig) -> None:
    """Validate every identifier before replacing a SQL template token."""

    _validate_identifier(config.source_project_id, _PROJECT_ID, "source project ID")
    _validate_identifier(config.destination_project_id, _PROJECT_ID, "destination project ID")
    _validate_identifier(config.source_dataset, _DATASET_ID, "source dataset ID")
    _validate_identifier(config.destination_dataset, _DATASET_ID, "destination dataset ID")
    _validate_identifier(config.run_id, _RUN_ID, "run ID")


def render_reference_template(template: str, config: RebuildConfig) -> str:
    """Render a reference SQL template after strict identifier validation."""

    validate_reference_config(config)
    rendered = template
    replacements = {
        "{{SOURCE_PROJECT_ID}}": config.source_project_id,
        "{{SOURCE_DATASET}}": config.source_dataset,
        "{{DESTINATION_PROJECT_ID}}": config.destination_project_id,
        "{{DESTINATION_DATASET}}": config.destination_dataset,
        "{{RUN_ID}}": config.run_id,
    }
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("Reference SQL template contains an unexpanded placeholder.")
    return rendered


def plan_reference_pipeline(
    config: RebuildConfig, template_directory: str | Path
) -> tuple[PlannedReferenceQuery, ...]:
    """Render the fixed, dependency-ordered five-stage reference cohort plan."""

    root = Path(template_directory)
    plan = []
    for stage in REFERENCE_STAGES:
        template_path = root / stage.filename
        if not template_path.is_file():
            raise FileNotFoundError(f"Missing reference SQL template: {template_path}")
        plan.append(
            PlannedReferenceQuery(
                stage=stage,
                template_path=template_path,
                sql=render_reference_template(template_path.read_text(encoding="utf-8"), config),
            )
        )
    return tuple(plan)


def guarded_reference_dry_run(
    plan: Iterable[PlannedReferenceQuery], guard: BigQueryExecutionGuard
) -> dict[str, QueryEstimate]:
    """Obtain guarded dry-run estimates for every planned stage.

    This helper calls only ``guard.estimate``. It performs no execution job.
    """

    return {query.stage.name: guard.estimate(query.sql) for query in plan}


def submit_reference_plan(
    plan: Iterable[PlannedReferenceQuery], guard: BigQueryExecutionGuard
) -> list[object]:
    """Submit every stage solely through the mandatory guarded execution interface.

    This function is intentionally not invoked by Task 3A or its tests against a
    real client. Researcher approval is required before any caller uses it.
    """

    return [guard.run(query.sql) for query in plan]


def build_reference_run_manifest(
    *, config: RebuildConfig, repository: str | Path, template_directory: str | Path
) -> dict[str, object]:
    """Create a non-executed manifest with the five reference SQL hashes."""

    root = Path(template_directory)
    files = [root / stage.filename for stage in REFERENCE_STAGES]
    return build_manifest(
        config=config,
        repository=repository,
        sql_files=files,
        execution=ExecutionMetadata(
            run_id=config.run_id,
            status="reference_plan_not_executed",
            started_at_utc="not_executed",
            query_count=0,
        ),
    )


def reference_stay_order_key(unit_visit_number: int | None, patient_unit_stay_id: int) -> tuple[int, int]:
    """Synthetic mirror of frozen eligible unit-stay ordering."""

    return (999_999 if unit_visit_number is None else unit_visit_number, patient_unit_stay_id)


def reference_revision_order_key(
    lab_result_revised_offset: int | None, lab_result_offset: int, lab_id: int
) -> tuple[int, int]:
    """Synthetic mirror of frozen creatinine revision ordering (descending)."""

    return (
        lab_result_offset if lab_result_revised_offset is None else lab_result_revised_offset,
        lab_id,
    )


def in_reference_creatinine_outcome_window(
    lab_offset: int, unit_discharge_offset: int
) -> bool:
    """Synthetic mirror of frozen primary outcome window, (720, min(discharge,4320)]."""

    return 720 < lab_offset <= min(unit_discharge_offset, 4320)
