#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for MigrateInstancesFromHostStep retry logic.

These tests verify that when a migrate fails on a transient messaging/RPC
error (e.g. a lost scheduler reply while RabbitMQ is restarting during a
deploy), the step retries the migrate instead of immediately failing the
whole strategy. The instance has not moved on failure, so the retry is safe.
"""

from unittest import mock

from nfv_common import strategy as common_strategy
from nfv_common import timers
from nfv_vim.strategy._strategy_defs import STRATEGY_EVENT
from nfv_vim.strategy._strategy_steps import MigrateInstancesFromHostStep

from nfv_unit_tests.tests import sw_update_testcase


class TestMigrateInstancesFromHostStepRetry(
    sw_update_testcase.SwUpdateStrategyTestCase
):
    """Unit tests for MigrateInstancesFromHostStep retry on failure."""

    def setUp(self):
        super().setUp()
        self.create_host("compute-0")
        self.create_instance("small", "test-instance-0", "compute-0")
        self._host = self._host_table.get("compute-0")
        self._instance = list(self._instance_table.values())[0]
        self._mock_stage = None

    def _make_migrate_step(self, retry_count=3, retry_delay=60):
        step = MigrateInstancesFromHostStep(
            hosts=[self._host],
            instances=[self._instance],
            retry_count=retry_count,
            retry_delay=retry_delay,
        )
        # step.stage is a weakref property; keep a strong ref to the mock.
        self._mock_stage = mock.MagicMock()
        step.stage = self._mock_stage
        return step

    def test_migrate_failed_triggers_retry_when_retries_available(self):
        """MIGRATE_INSTANCES_FAILED should retry, not fail the step."""

        step = self._make_migrate_step(retry_count=3)

        handled = step.handle_event(
            STRATEGY_EVENT.MIGRATE_INSTANCES_FAILED, "migrate failed"
        )

        self.assertTrue(handled)
        self._mock_stage.step_complete.assert_not_called()
        self.assertTrue(step._retry_requested)
        self.assertEqual(step._retries, 2)

    def test_migrate_failed_fails_step_when_no_retries(self):
        """MIGRATE_INSTANCES_FAILED should fail the step when retries=0."""

        step = self._make_migrate_step(retry_count=0)

        handled = step.handle_event(
            STRATEGY_EVENT.MIGRATE_INSTANCES_FAILED, "migrate failed"
        )

        self.assertTrue(handled)
        self._mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.FAILED, "migrate failed"
        )

    def test_migrate_failed_fails_after_retries_exhausted(self):
        """Step should fail only after all retries are exhausted."""

        step = self._make_migrate_step(retry_count=2)

        step.handle_event(STRATEGY_EVENT.MIGRATE_INSTANCES_FAILED, "fail")
        self._mock_stage.step_complete.assert_not_called()
        self.assertEqual(step._retries, 1)
        step._retry_requested = False

        step.handle_event(STRATEGY_EVENT.MIGRATE_INSTANCES_FAILED, "fail")
        self._mock_stage.step_complete.assert_not_called()
        self.assertEqual(step._retries, 0)
        step._retry_requested = False

        step.handle_event(STRATEGY_EVENT.MIGRATE_INSTANCES_FAILED, "fail")
        self._mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.FAILED, "fail"
        )

    @mock.patch("nfv_vim.directors.get_instance_director")
    def test_retry_reissues_migrate_after_delay(self, mock_get_director):
        """After retry_delay, an audit event should re-issue the migrate."""

        step = self._make_migrate_step(retry_count=3, retry_delay=60)

        step.handle_event(STRATEGY_EVENT.MIGRATE_INSTANCES_FAILED, "fail")
        self.assertTrue(step._retry_requested)

        mock_director = mock.MagicMock()
        mock_operation = mock.MagicMock()
        mock_operation.is_failed.return_value = False
        mock_director.migrate_instances_from_hosts.return_value = mock_operation
        mock_get_director.return_value = mock_director

        # Audit before the delay elapses -> no re-issue yet
        step.handle_event(STRATEGY_EVENT.HOST_AUDIT, None)
        mock_director.migrate_instances_from_hosts.assert_not_called()

        # Advance time beyond retry_delay
        current_time = timers.get_monotonic_timestamp_in_ms()
        step._wait_time = current_time - (61 * 1000)

        step.handle_event(STRATEGY_EVENT.HOST_AUDIT, None)
        mock_director.migrate_instances_from_hosts.assert_called_once_with(
            ["compute-0"]
        )
        self.assertFalse(step._retry_requested)

    def test_from_dict_restores_retry_state(self):
        """from_dict should restore retry_count and retry_delay."""

        step = self._make_migrate_step(retry_count=3, retry_delay=60)
        data = step.as_dict()

        self.assertEqual(data["retry_count"], 3)
        self.assertEqual(data["retry_delay"], 60)

        new_step = object.__new__(MigrateInstancesFromHostStep)
        new_step.from_dict(data)

        self.assertEqual(new_step._retry_count, 3)
        self.assertEqual(new_step._retry_delay, 60)
        self.assertEqual(new_step._retries, 3)
        self.assertFalse(new_step._retry_requested)
        self.assertEqual(new_step._wait_time, 0)

    def test_from_dict_backward_compatible(self):
        """from_dict should default retry keys when absent (upgrade compat)."""

        step = self._make_migrate_step(retry_count=3)
        data = step.as_dict()
        del data["retry_count"]
        del data["retry_delay"]

        new_step = object.__new__(MigrateInstancesFromHostStep)
        new_step.from_dict(data)

        # Absent retry keys default to 0 (retries off), matching the step's
        # default; the strategy builder opts in by passing retry_count.
        self.assertEqual(new_step._retry_count, 0)
        self.assertEqual(
            new_step._retry_delay, MigrateInstancesFromHostStep.RETRY_DELAY
        )

    def test_migrate_success_completes_step(self):
        """If instances have migrated off, an audit completes the step."""

        step = self._make_migrate_step(retry_count=3)

        with mock.patch.object(
            step, "_all_instances_migrated", return_value=(True, "")
        ):
            step.handle_event(STRATEGY_EVENT.INSTANCE_AUDIT, None)
            self._mock_stage.step_complete.assert_called_once_with(
                common_strategy.STRATEGY_STEP_RESULT.SUCCESS, ""
            )
