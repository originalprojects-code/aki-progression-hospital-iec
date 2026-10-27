# Paper 1 rebuild: safe infrastructure

This document applies only to the separate `develop/paper1-rebuild` development
branch. The frozen `v1.2.1-submission` tag is a reference and must not be moved,
rewritten, or used as an output destination.

## Scope

The initial infrastructure contains no cohort construction, feature generation,
fold assignment, model fitting, BigQuery table DDL, or scientific result. It does
not establish that the rebuilt cohort matches the reported cohort.

## Setup

Use Python 3.11 or newer and install the local package:

```bash
python -m pip install -e .
```

Copy `config/rebuild.example.toml` to an untracked local configuration file and
replace the source/destination project and destination dataset placeholders. Do not place credentials,
patient-level paths, query exports, or source data in the repository.

## Query safety contract

All future BigQuery calls must use `BigQueryExecutionGuard.run(sql)`. It performs
a dry run first and refuses a query whose estimated processed bytes exceed exactly
5,000,000,000. The subsequent execution job receives the same
`maximum_bytes_billed=5_000_000_000` setting and disables the query cache.

This guard does not grant authority to execute a query. Cohort, feature, fold, and
model stages remain blocked pending researcher approval. Dry runs and real jobs
must be recorded in the run manifest by the approved orchestration layer.

## Tests

Run only local tests:

```bash
python -m unittest discover -s tests -t . -v
```

The tests use a fake BigQuery client. They do not authenticate, make network
requests, access eICU, submit SQL, or create BigQuery resources.

## Reproducibility manifest

`aki_rebuild.manifest.build_manifest` records the local Git commit, configuration
hash, hashes of explicitly supplied SQL files, Python/environment metadata, and
declared execution metadata. It does not query BigQuery or infer patient-level
results. A manifest with `status: not_executed` is expected until a researcher has
approved a pipeline stage.
