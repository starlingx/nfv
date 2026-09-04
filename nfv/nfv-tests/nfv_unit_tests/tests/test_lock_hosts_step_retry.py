#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for LockHostsStep retry logic.

These tests verify that when a host lock fails (e.g. due to ceph PG
recovery after a swact), the LockHostsStep retries the lock operation
instead of immediately failing the strategy step.
"""

from unittest import mock

from nfv_common import strategy as common_strategy
from nfv_common import timers
from nfv_vim import nfvi
from nfv_vim.strategy._strategy_defs import STRATEGY_EVENT
from nfv_vim.strategy._strategy_steps import LockHostsStep

from nfv_unit_tests.tests import sw_update_testcase


class TestLockHostsStepRetry(sw_update_testcase.SwUpdateStrategyTestCase):
    """Unit tests for LockHostsStep retry on HOST_LOCK_FAILED."""

    def setUp(self):
        super().setUp()
        # Create a host in unlocked state (not locked)
        self.create_host(
            "controller-1",
            aio=True,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.UNLOCKED,
        )
        self._host = self._host_table.get("controller-1")
        self._mock_stage = None

    def _make_lock_step(self, retry_count=3, retry_delay=90):
        """Create a LockHostsStep with retry enabled."""

        step = LockHostsStep(
            hosts=[self._host],
            wait_until_disabled=True,
            retry_count=retry_count,
            retry_delay=retry_delay,
        )
        # step.stage is a weakref property, so we must keep a strong
        # reference to the mock to prevent garbage collection.
        self._mock_stage = mock.MagicMock()
        step.stage = self._mock_stage
        return step

    def test_lock_failed_triggers_retry_when_retries_available(self):
        """HOST_LOCK_FAILED should trigger retry, not fail the step."""

        step = self._make_lock_step(retry_count=3)

        # Simulate HOST_LOCK_FAILED event
        handled = step.handle_event(STRATEGY_EVENT.HOST_LOCK_FAILED, self._host)

        self.assertTrue(handled)
        # Step should NOT have completed (no call to step_complete)
        self._mock_stage.step_complete.assert_not_called()
        # Retry should have been requested
        self.assertTrue(step._retry_requested)
        # Retry count for this host should be decremented
        self.assertEqual(step._retries["controller-1"], 2)

    def test_lock_failed_fails_step_when_no_retries(self):
        """HOST_LOCK_FAILED should fail step when retry_count is 0."""

        step = self._make_lock_step(retry_count=0)

        handled = step.handle_event(STRATEGY_EVENT.HOST_LOCK_FAILED, self._host)

        self.assertTrue(handled)
        self._mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.FAILED, "host lock failed"
        )

    def test_lock_failed_fails_step_when_retries_exhausted(self):
        """HOST_LOCK_FAILED should fail after all retries are exhausted."""

        step = self._make_lock_step(retry_count=2)

        # First failure -> retry
        step.handle_event(STRATEGY_EVENT.HOST_LOCK_FAILED, self._host)
        self._mock_stage.step_complete.assert_not_called()
        self.assertEqual(step._retries["controller-1"], 1)

        # Reset retry_requested (simulating that the retry was processed)
        step._retry_requested = False

        # Second failure -> retry
        step.handle_event(STRATEGY_EVENT.HOST_LOCK_FAILED, self._host)
        self._mock_stage.step_complete.assert_not_called()
        self.assertEqual(step._retries["controller-1"], 0)

        # Reset retry_requested
        step._retry_requested = False

        # Third failure -> no more retries, step fails
        step.handle_event(STRATEGY_EVENT.HOST_LOCK_FAILED, self._host)
        self._mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.FAILED, "host lock failed"
        )

    @mock.patch("nfv_vim.directors.get_host_director")
    def test_retry_reissues_lock_after_delay(self, mock_get_director):
        """After retry_delay, HOST_AUDIT should re-issue the lock."""

        step = self._make_lock_step(retry_count=3, retry_delay=90)

        # Trigger the retry (simulates HOST_LOCK_FAILED)
        step.handle_event(STRATEGY_EVENT.HOST_LOCK_FAILED, self._host)
        self.assertTrue(step._retry_requested)

        # Mock host_director to track lock_hosts calls
        mock_director = mock.MagicMock()
        mock_operation = mock.MagicMock()
        mock_operation.is_inprogress.return_value = True
        mock_operation.is_failed.return_value = False
        mock_director.lock_hosts.return_value = mock_operation
        mock_get_director.return_value = mock_director

        # Simulate HOST_AUDIT before retry_delay has elapsed
        # (wait_time was just set, so secs_expired < retry_delay)
        step.handle_event(STRATEGY_EVENT.HOST_AUDIT, None)
        # lock_hosts should NOT have been called yet
        mock_director.lock_hosts.assert_not_called()

        # Now simulate time passing beyond retry_delay
        # Set _wait_time to a value that makes secs_expired >= retry_delay
        current_time = timers.get_monotonic_timestamp_in_ms()
        step._wait_time = current_time - (91 * 1000)  # 91 seconds ago

        # Simulate HOST_AUDIT after delay has elapsed
        step.handle_event(STRATEGY_EVENT.HOST_AUDIT, None)

        # Now lock_hosts should have been re-issued
        mock_director.lock_hosts.assert_called_once_with(["controller-1"])
        # retry_requested should be cleared
        self.assertFalse(step._retry_requested)

    def test_lock_failed_always_retries_when_retries_available(self):
        """HOST_LOCK_FAILED should always retry if retries remain."""

        # Create a host that is already locked (edge case - stale event)
        self.create_host(
            "controller-0",
            aio=True,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
        )
        locked_host = self._host_table.get("controller-0")

        step = LockHostsStep(
            hosts=[locked_host],
            wait_until_disabled=True,
            retry_count=3,
            retry_delay=90,
        )
        mock_stage = mock.MagicMock()
        step.stage = mock_stage

        # Even if host appears locked, HOST_LOCK_FAILED with retries
        # triggers a retry (the next HOST_AUDIT will detect success)
        handled = step.handle_event(STRATEGY_EVENT.HOST_LOCK_FAILED, locked_host)

        self.assertTrue(handled)
        mock_stage.step_complete.assert_not_called()
        self.assertTrue(step._retry_requested)

    def test_from_dict_restores_retry_state(self):
        """from_dict should restore retry_count and retry_delay."""

        step = self._make_lock_step(retry_count=3, retry_delay=90)

        # Serialize
        data = step.as_dict()

        # Verify serialization
        self.assertEqual(data["retry_count"], 3)
        self.assertEqual(data["retry_delay"], 90)

        # Deserialize
        new_step = object.__new__(LockHostsStep)
        new_step.from_dict(data)

        self.assertEqual(new_step._retry_count, 3)
        self.assertEqual(new_step._retry_delay, 90)
        self.assertEqual(new_step._retries["controller-1"], 3)
        self.assertFalse(new_step._retry_requested)
        self.assertEqual(new_step._wait_time, 0)

    def test_from_dict_backward_compatible(self):
        """from_dict should handle missing retry keys (upgrade compat)."""

        step = self._make_lock_step(retry_count=0)

        # Serialize, then remove retry keys (simulate old strategy data)
        data = step.as_dict()
        del data["retry_count"]
        del data["retry_delay"]

        # Deserialize - should default to 0 retries
        new_step = object.__new__(LockHostsStep)
        new_step.from_dict(data)

        self.assertEqual(new_step._retry_count, 0)
        self.assertEqual(new_step._retry_delay, LockHostsStep.RETRY_DELAY)

    def test_lock_success_after_retry_trigger(self):
        """If host becomes locked after retry was triggered, step succeeds."""

        step = self._make_lock_step(retry_count=3, retry_delay=90)

        # Trigger retry
        step.handle_event(STRATEGY_EVENT.HOST_LOCK_FAILED, self._host)
        self.assertTrue(step._retry_requested)

        # Now simulate the host transitioning to locked+disabled
        # by mocking the host's is_locked and is_disabled methods
        with mock.patch.object(
            self._host, "is_locked", return_value=True
        ), mock.patch.object(self._host, "is_disabled", return_value=True):
            # HOST_STATE_CHANGED should detect host is locked and complete
            step.handle_event(STRATEGY_EVENT.HOST_STATE_CHANGED, None)
            self._mock_stage.step_complete.assert_called_once_with(
                common_strategy.STRATEGY_STEP_RESULT.SUCCESS, ""
            )

    def test_abort_returns_empty_list_for_sw_upgrade_strategy(self):
        """abort() returns [] when strategy is SW_UPGRADE.

        For sw-deploy strategies, locked hosts must not be unlocked during
        abort because the deploy must be cleaned up first via a separate
        rollback strategy.
        """

        step = self._make_lock_step(retry_count=0)

        # Build a mock strategy whose name matches SW_UPGRADE
        mock_strategy = mock.MagicMock()
        mock_strategy.name = "sw-upgrade"

        # Wire up the chain: step.stage.phase.strategy
        mock_phase = mock.MagicMock()
        mock_phase.strategy = mock_strategy
        self._mock_stage.phase = mock_phase

        result = step.abort()
        self.assertEqual(result, [])

    def test_abort_returns_unlock_step_for_non_sw_upgrade_strategy(self):
        """abort() returns [UnlockHostsStep] for non-SW_UPGRADE strategies."""

        step = self._make_lock_step(retry_count=0)

        mock_strategy = mock.MagicMock()
        mock_strategy.name = "fw-update"

        mock_phase = mock.MagicMock()
        mock_phase.strategy = mock_strategy
        self._mock_stage.phase = mock_phase

        result = step.abort()
        self.assertEqual(len(result), 1)
        from nfv_vim.strategy._strategy_steps import UnlockHostsStep

        self.assertIsInstance(result[0], UnlockHostsStep)

    def test_abort_returns_unlock_step_when_strategy_is_none(self):
        """abort() returns [UnlockHostsStep] when strategy is None.

        When the step has no strategy reference (e.g. stage/phase not wired),
        the fallback behavior is to return an unlock step.
        """

        step = self._make_lock_step(retry_count=0)

        # Make strategy return None via the property chain
        mock_phase = mock.MagicMock()
        mock_phase.strategy = None
        self._mock_stage.phase = mock_phase

        result = step.abort()
        self.assertEqual(len(result), 1)
        from nfv_vim.strategy._strategy_steps import UnlockHostsStep

        self.assertIsInstance(result[0], UnlockHostsStep)
