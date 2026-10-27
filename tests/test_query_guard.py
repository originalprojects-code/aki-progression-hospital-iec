import unittest

from aki_rebuild.config import REQUIRED_BILLING_LIMIT
from aki_rebuild.query_guard import BigQueryCostLimitExceeded, BigQueryExecutionGuard


class FakeJob:
    def __init__(self, total_bytes_processed):
        self.total_bytes_processed = total_bytes_processed


class FakeClient:
    def __init__(self, estimated_bytes):
        self.estimated_bytes = estimated_bytes
        self.calls = []

    def query(self, sql, *, job_config):
        self.calls.append((sql, job_config))
        if job_config.dry_run:
            return FakeJob(self.estimated_bytes)
        return FakeJob(None)


class QueryGuardTests(unittest.TestCase):
    def test_over_limit_query_is_rejected_before_execution(self):
        client = FakeClient(REQUIRED_BILLING_LIMIT + 1)
        guard = BigQueryExecutionGuard(client)

        with self.assertRaises(BigQueryCostLimitExceeded):
            guard.run("SELECT * FROM a_large_table")

        self.assertEqual(len(client.calls), 1)
        _, dry_run_config = client.calls[0]
        self.assertTrue(dry_run_config.dry_run)
        self.assertEqual(dry_run_config.maximum_bytes_billed, REQUIRED_BILLING_LIMIT)

    def test_execution_is_preceded_by_dry_run_and_capped(self):
        client = FakeClient(REQUIRED_BILLING_LIMIT)
        guard = BigQueryExecutionGuard(client)

        guard.run("SELECT 1")

        self.assertEqual(len(client.calls), 2)
        _, dry_run_config = client.calls[0]
        _, execution_config = client.calls[1]
        self.assertTrue(dry_run_config.dry_run)
        self.assertFalse(execution_config.dry_run)
        self.assertEqual(dry_run_config.maximum_bytes_billed, REQUIRED_BILLING_LIMIT)
        self.assertEqual(execution_config.maximum_bytes_billed, REQUIRED_BILLING_LIMIT)
        self.assertFalse(execution_config.use_query_cache)

    def test_empty_sql_cannot_be_submitted(self):
        client = FakeClient(1)
        guard = BigQueryExecutionGuard(client)

        with self.assertRaisesRegex(ValueError, "non-empty"):
            guard.run("   ")

        self.assertEqual(client.calls, [])

    def test_nonstandard_billing_limit_is_not_permitted(self):
        with self.assertRaisesRegex(ValueError, "fixed"):
            BigQueryExecutionGuard(FakeClient(1), maximum_bytes_billed=1)
