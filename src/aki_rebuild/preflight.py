"""Non-executing local preflight for the Paper 1 reference cohort SQL plan."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

from .config import RebuildConfig, load_config
from .reference_sql import REFERENCE_STAGES, plan_reference_pipeline, validate_reference_config


_FROZEN_SOURCE_DATASET = "physionet-data.eicu_crd"
_PLACEHOLDER_SOURCE = "{{SOURCE_PROJECT_ID}}.{{SOURCE_DATASET}}"
_PLACEHOLDER_DESTINATION = "{{DESTINATION_PROJECT_ID}}.{{DESTINATION_DATASET}}"
REFERENCE_SOURCE_SCHEMA = {
    "patient": [
        "patientUnitStayID", "patientHealthSystemStayID", "uniquePID", "hospitalID",
        "unitVisitNumber", "hospitalAdmitOffset", "unitDischargeOffset",
        "unitDischargeStatus", "hospitalDischargeStatus", "age",
    ],
    "lab": ["patientUnitStayID", "labID", "labResultOffset", "labResultRevisedOffset", "labResult", "labName"],
    "pasthistory": ["patientUnitStayID", "pastHistoryOffset", "pastHistoryPath", "pastHistoryValue", "pastHistoryValueText"],
    "diagnosis": ["patientUnitStayID", "diagnosisOffset", "diagnosisString"],
    "treatment": ["patientUnitStayID", "treatmentOffset", "treatmentString"],
    "intakeoutput": ["patientUnitStayID", "intakeOutputOffset", "dialysisTotal"],
}

# These are byte-preserving technical substitutions, documented as the sole
# equivalence exception for frozen sql/03_renal_flags.sql.
_BACKSPACE_REWRITES = (
    (
        "CONCAT(r'end.?stage renal|', CHR(8), r'esrd', CHR(8), "
        "r'|dialysis.?dependent|chronic dialysis|maintenance dialysis|for chronic renal failure')",
        "r'end.?stage renal|\x08esrd\x08|dialysis.?dependent|chronic dialysis|maintenance dialysis|for chronic renal failure'",
    ),
    (
        "CONCAT(r'end.?stage renal|', CHR(8), r'esrd', CHR(8), "
        "r'|dialysis.?dependent|chronic dialysis|maintenance dialysis')",
        "r'end.?stage renal|\x08esrd\x08|dialysis.?dependent|chronic dialysis|maintenance dialysis'",
    ),
    (
        "CONCAT(r'for acute renal failure|hemodialysis\\|emergent|peritoneal dialysis\\|emergent|c v v h|c v v h d|c a v h d|', "
        "CHR(8), r'sled', CHR(8), r'|', CHR(8), r'crrt', CHR(8), r'|hemofiltration|renal replacement')",
        "r'for acute renal failure|hemodialysis\\|emergent|peritoneal dialysis\\|emergent|c v v h|c v v h d|c a v h d|\x08sled\x08|\x08crrt\x08|hemofiltration|renal replacement'",
    ),
)


def _remove_comments_and_normalize(sql: str) -> str:
    uncommented = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return re.sub(r"\s+", " ", uncommented).strip()


def canonicalize_frozen_sql(sql: str) -> str:
    """Canonicalize frozen SQL only for identifier parameterization comparison."""

    canonical = sql.replace(
        "{{PROJECT_ID}}.{{DATASET_ID}}", _PLACEHOLDER_DESTINATION
    ).replace(_FROZEN_SOURCE_DATASET, _PLACEHOLDER_SOURCE)
    return _remove_comments_and_normalize(canonical)


def canonicalize_reference_sql(sql: str) -> str:
    """Canonicalize reference SQL and reverse the documented CHR(8) rewrite."""

    canonical = sql
    for replacement, frozen_equivalent in _BACKSPACE_REWRITES:
        canonical = canonical.replace(replacement, frozen_equivalent)
    return _remove_comments_and_normalize(canonical)


def verify_reference_semantic_equivalence(
    frozen_directory: str | Path, reference_directory: str | Path
) -> list[dict[str, object]]:
    """Compare all five templates after only documented technical transforms."""

    frozen_root = Path(frozen_directory)
    reference_root = Path(reference_directory)
    results = []
    for stage in REFERENCE_STAGES:
        frozen_path = frozen_root / stage.filename
        reference_path = reference_root / stage.filename
        frozen = canonicalize_frozen_sql(frozen_path.read_text(encoding="utf-8"))
        reference = canonicalize_reference_sql(reference_path.read_text(encoding="utf-8"))
        exceptions = ["CHR(8)_represents_frozen_ASCII_backspace"] if stage.name == "renal_flags" else []
        results.append(
            {
                "stage": stage.name,
                "equivalent": frozen == reference,
                "exceptions": exceptions,
                "frozen_sha256": hashlib.sha256(frozen.encode("utf-8")).hexdigest(),
                "reference_sha256": hashlib.sha256(reference.encode("utf-8")).hexdigest(),
            }
        )
    return results


def _source_table_references(rendered_sql: str) -> list[str]:
    return sorted(
        set(
            re.findall(
                r"`[^`]+\.(?:patient|lab|pasthistory|diagnosis|treatment|intakeoutput)`",
                rendered_sql,
            )
        )
    )


def build_reference_preflight_report(
    *,
    config: RebuildConfig,
    repository: str | Path,
    frozen_directory: str | Path,
    reference_directory: str | Path,
) -> dict[str, object]:
    """Build an in-memory preflight report without creating a client or job."""

    validate_reference_config(config)
    plan = plan_reference_pipeline(config, reference_directory)
    equivalence = verify_reference_semantic_equivalence(frozen_directory, reference_directory)
    rendered_stages = []
    for query in plan:
        expected_destination = (
            f"`{config.destination_project_id}.{config.destination_dataset}.{query.stage.output_table}`"
        )
        rendered_stages.append(
            {
                "stage": query.stage.name,
                "depends_on": list(query.stage.depends_on),
                "destination_identifier": expected_destination,
                "destination_identifier_present": expected_destination in query.sql,
                "source_tables": _source_table_references(query.sql),
                "rendered_sql_sha256": hashlib.sha256(query.sql.encode("utf-8")).hexdigest(),
                "contains_create_or_replace": "CREATE OR REPLACE TABLE" in query.sql,
            }
        )

    equivalence_passed = all(item["equivalent"] for item in equivalence)
    destination_passed = all(item["destination_identifier_present"] for item in rendered_stages)
    return {
        "report_version": 1,
        "kind": "local_non_executing_reference_sql_preflight",
        "repository": str(Path(repository)),
        "configuration": asdict(config),
        "configuration_sha256": config.sha256(),
        "semantic_equivalence": equivalence,
        "source_schema_contract": REFERENCE_SOURCE_SCHEMA,
        "syntax_review": {
            "dialect": "BigQuery Standard SQL",
            "local_check": "fixed templates use backtick-qualified identifiers and reviewed Standard SQL constructs",
            "remote_parser_validation_completed": False,
        },
        "rendered_stages": rendered_stages,
        "execution_readiness": {
            "local_preflight_passed": equivalence_passed and destination_passed,
            "real_execution_submitted": False,
            "remote_dry_run_submitted": False,
            "optional_dry_run_procedure": "requires explicit approval and BigQueryExecutionGuard.estimate only",
            "remaining_remote_checks": [
                "BigQuery Standard SQL parser validation",
                "source table and column access validation",
                "guarded dry-run byte estimates at or below 5000000000",
            ],
        },
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Render and print a local JSON report; this command has no cloud behavior."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--frozen-sql", type=Path, default=Path("sql"))
    parser.add_argument("--reference-sql", type=Path, default=Path("sql/rebuild/reference"))
    args = parser.parse_args(argv)
    report = build_reference_preflight_report(
        config=load_config(args.config),
        repository=args.repository,
        frozen_directory=args.frozen_sql,
        reference_directory=args.reference_sql,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["execution_readiness"]["local_preflight_passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
