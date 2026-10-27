"""BigQuery query execution with mandatory dry-run cost protection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:  # Import lazily enough for local, credential-free safety tests.
    from google.cloud import bigquery
except ModuleNotFoundError:  # pragma: no cover - exercised by the local test runtime.
    bigquery = None

from .config import REQUIRED_BILLING_LIMIT


class BigQueryCostLimitExceeded(RuntimeError):
    """Raised before execution when a query's dry-run cost exceeds the hard cap."""


class BigQueryDryRunUnavailable(RuntimeError):
    """Raised when BigQuery does not provide a dry-run byte estimate."""


@dataclass(frozen=True)
class _LocalQueryJobConfig:
    """Small stand-in used only when the BigQuery package is not installed.

    It permits unit testing the safety contract without credentials or a cloud SDK.
    Production query execution requires the real google-cloud-bigquery package.
    """

    dry_run: bool
    use_query_cache: bool
    maximum_bytes_billed: int


@dataclass(frozen=True)
class QueryEstimate:
    sql: str
    bytes_processed: int
    maximum_bytes_billed: int


class BigQueryExecutionGuard:
    """Only supported interface for executing rebuild queries.

    Every call to :meth:`run` first sends a BigQuery dry run. The actual query is
    submitted only when the estimate is at or below the mandatory billing cap and
    carries the same ``maximum_bytes_billed`` setting. This class deliberately
    accepts an injected client so tests never need credentials or network access.
    """

    def __init__(self, client: Any, maximum_bytes_billed: int = REQUIRED_BILLING_LIMIT):
        if maximum_bytes_billed != REQUIRED_BILLING_LIMIT:
            raise ValueError(
                "The Paper 1 rebuild billing limit is fixed at "
                f"{REQUIRED_BILLING_LIMIT}."
            )
        self._client = client
        self._limit = maximum_bytes_billed

    @property
    def maximum_bytes_billed(self) -> int:
        return self._limit

    def _job_config(self, *, dry_run: bool) -> Any:
        config_class = (
            bigquery.QueryJobConfig if bigquery is not None else _LocalQueryJobConfig
        )
        return config_class(
            dry_run=dry_run,
            use_query_cache=False,
            maximum_bytes_billed=self._limit,
        )

    def estimate(self, sql: str) -> QueryEstimate:
        """Dry-run a non-empty SQL string and reject an over-cap estimate."""
        if not sql or not sql.strip():
            raise ValueError("SQL must be non-empty.")

        dry_run_job = self._client.query(sql, job_config=self._job_config(dry_run=True))
        total_bytes = getattr(dry_run_job, "total_bytes_processed", None)
        if total_bytes is None:
            raise BigQueryDryRunUnavailable(
                "BigQuery dry run returned no total_bytes_processed estimate."
            )

        estimate = QueryEstimate(
            sql=sql,
            bytes_processed=int(total_bytes),
            maximum_bytes_billed=self._limit,
        )
        if estimate.bytes_processed > self._limit:
            raise BigQueryCostLimitExceeded(
                f"Dry-run estimate {estimate.bytes_processed} exceeds "
                f"the limit {self._limit}. Query was not executed."
            )
        return estimate

    def run(self, sql: str) -> Any:
        """Submit a query only after its successful mandatory dry-run check.

        The returned job is intentionally not awaited here; callers must record
        execution metadata separately and may call ``result()`` only after an
        approved pipeline stage has invoked this guarded method.
        """
        self.estimate(sql)
        return self._client.query(sql, job_config=self._job_config(dry_run=False))
