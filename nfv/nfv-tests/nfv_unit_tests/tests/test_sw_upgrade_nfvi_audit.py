#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for SwUpgrade.nfvi_audit() kube upgrade polling in combined strategy."""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

from nfv_unit_tests.tests import testcase
from nfv_vim.objects._sw_update import DEFAULT_KUBE_AUDIT_RATE
from nfv_vim.objects import SwUpgrade


class FakeStage:
    """A minimal fake strategy stage for testing _is_kube_upgrade_active."""

    def __init__(self, name):
        self.name = name


class FakePhase:
    """A minimal fake apply phase."""

    def __init__(self, stage_name, current_stage=0):
        self.stages = [FakeStage(stage_name)]
        self.current_stage = current_stage


class FakeStrategy:
    """A minimal fake strategy for testing."""

    def __init__(self, kube_to_version=None, stage_name="sw-upgrade-worker-hosts"):
        self.kube_to_version = kube_to_version
        self.apply_phase = FakePhase(stage_name)

    def is_applying(self):
        return True

    def is_apply_failed(self):
        return False

    def is_apply_timed_out(self):
        return False

    def is_aborting(self):
        return False


# Note: _sw_upgrade.py and _kube_upgrade_mixins.py both do
# "from nfv_common import timers", so they share the exact same module
# object. Patching timers_reschedule_timer through either module path
# patches the same underlying attribute on nfv_common.timers - so a single
# patch target is used here and calls are distinguished by their arguments.
@mock.patch("nfv_vim.objects._sw_update.timers.timers_reschedule_timer")
@mock.patch("nfv_vim.objects._sw_update.timers.timers_create_timer")
@mock.patch("nfv_vim.objects._sw_update.SwUpdate.save")
@mock.patch("nfv_vim.event_log._instance._event_issue")
class TestSwUpgradeNfviAuditKubePolling(testcase.NFVTestCase):
    """Test that SwUpgrade.nfvi_audit() polls kube upgrade state

    when _is_kube_upgrade_active() returns True (combined strategy).
    """

    TIMER_ID = 42

    def _create_sw_upgrade(
        self, kube_to_version=None, stage_name="sw-upgrade-worker-hosts"
    ):
        """Create a SwUpgrade with the given strategy configuration."""
        sw_upgrade = SwUpgrade()
        sw_upgrade._nfvi_audit_inprogress = False
        sw_upgrade._strategy = FakeStrategy(
            kube_to_version=kube_to_version,
            stage_name=stage_name,
        )
        return sw_upgrade

    @contextmanager
    def _nfvi_patches(self):
        """Context manager that patches all nfvi calls used during audit.

        Yields a namespace-like object with attributes:
            get_alarms, get_kube_upgrade, get_kube_hosts
        """
        with mock.patch("nfv_vim.nfvi.nfvi_get_alarms") as m_alarms, mock.patch(
            "nfv_vim.nfvi.nfvi_fault_mgmt_plugin_disabled", return_value=True
        ), mock.patch(
            "nfv_vim.nfvi.nfvi_get_kube_upgrade"
        ) as m_kube_upgrade, mock.patch(
            "nfv_vim.nfvi.nfvi_get_kube_host_upgrade_list"
        ) as m_kube_hosts:
            mocks = SimpleNamespace(
                get_alarms=m_alarms,
                get_kube_upgrade=m_kube_upgrade,
                get_kube_hosts=m_kube_hosts,
            )
            yield mocks

    def _start_audit(self, sw_upgrade):
        """Initialize the audit coroutine and drive it past the alarms phase.

        Returns the coroutine positioned right after the alarms callback
        has completed (i.e., ready for the next send that enters the kube
        upgrade or nfvi_update path).
        """
        audit_coro = sw_upgrade.nfvi_audit()
        next(audit_coro)
        # Trigger the first audit cycle (calls nfvi_get_alarms)
        audit_coro.send(self.TIMER_ID)
        # Simulate alarms callback completing
        sw_upgrade._nfvi_audit_inprogress = False
        return audit_coro

    def test_kube_upgrade_active_polls_kube_state(
        self, mock_event, mock_save, mock_create_timer, mock_reschedule
    ):
        """When _is_kube_upgrade_active() is True, nfvi_audit should call

        nfvi_get_kube_upgrade and use DEFAULT_KUBE_AUDIT_RATE.
        """
        sw_upgrade = self._create_sw_upgrade(
            kube_to_version="v1.30.6",
            stage_name="kube-upgrade-networking",
        )

        with self._nfvi_patches() as nfvi:
            audit_coro = self._start_audit(sw_upgrade)
            nfvi.get_alarms.assert_called_once()

            # Drive past alarms -> enters kube upgrade polling
            audit_coro.send(self.TIMER_ID)
            nfvi.get_kube_upgrade.assert_called_once()

            # Simulate kube upgrade callback completing (no state change)
            sw_upgrade._nfvi_audit_inprogress = False
            sw_upgrade._kube_upgrade = mock.MagicMock(state="upgrade-started")

            with mock.patch.object(sw_upgrade, "nfvi_update", return_value=True):
                audit_coro.send(self.TIMER_ID)

            # Timer should be rescheduled to DEFAULT_KUBE_AUDIT_RATE (5s)
            mock_reschedule.assert_called_once_with(
                self.TIMER_ID, DEFAULT_KUBE_AUDIT_RATE
            )

            # kube host upgrade list should NOT have been called
            # (state is not upgrading-kubelets)
            nfvi.get_kube_hosts.assert_not_called()

    def test_kube_upgrade_active_kubelet_state_polls_hosts(
        self, mock_event, mock_save, mock_create_timer, mock_reschedule
    ):
        """When kube upgrade state is 'upgrading-kubelets', nfvi_audit should

        also poll kube host upgrade list.
        """
        sw_upgrade = self._create_sw_upgrade(
            kube_to_version="v1.30.6",
            stage_name="kube-host-upgrade",
        )

        with self._nfvi_patches() as nfvi:
            audit_coro = self._start_audit(sw_upgrade)

            # Drive past alarms -> enters kube upgrade polling
            audit_coro.send(self.TIMER_ID)
            nfvi.get_kube_upgrade.assert_called_once()

            # Simulate kube upgrade callback with kubelet state
            sw_upgrade._nfvi_audit_inprogress = False
            sw_upgrade._kube_upgrade = mock.MagicMock(state="upgrading-kubelets")
            audit_coro.send(self.TIMER_ID)

            # kube host upgrade list should now be called
            nfvi.get_kube_hosts.assert_called_once()

            # Simulate kube host callback completing
            sw_upgrade._nfvi_audit_inprogress = False

            with mock.patch.object(sw_upgrade, "nfvi_update", return_value=True):
                audit_coro.send(self.TIMER_ID)

            mock_reschedule.assert_called_once_with(
                self.TIMER_ID, DEFAULT_KUBE_AUDIT_RATE
            )

    def test_kube_upgrade_not_active_uses_30s_rate(
        self, mock_event, mock_save, mock_create_timer, mock_reschedule
    ):
        """When _is_kube_upgrade_active() is False, nfvi_audit should NOT call

        nfvi_get_kube_upgrade and should use 30s timer.
        """
        sw_upgrade = self._create_sw_upgrade(
            kube_to_version=None,
            stage_name="sw-upgrade-worker-hosts",
        )

        with self._nfvi_patches() as nfvi:
            audit_coro = self._start_audit(sw_upgrade)

            with mock.patch.object(sw_upgrade, "nfvi_update", return_value=True):
                audit_coro.send(self.TIMER_ID)

            mock_reschedule.assert_called_once_with(self.TIMER_ID, 30)
            nfvi.get_kube_upgrade.assert_not_called()
            nfvi.get_kube_hosts.assert_not_called()

    def test_kube_upgrade_active_sw_stage_uses_30s_rate(
        self, mock_event, mock_save, mock_create_timer, mock_reschedule
    ):
        """When kube_to_version is set but current stage is a sw-deploy stage,

        _is_kube_upgrade_active() is False and 30s rate is used.
        """
        sw_upgrade = self._create_sw_upgrade(
            kube_to_version="v1.30.6",
            stage_name="sw-upgrade-worker-hosts",
        )

        with self._nfvi_patches() as nfvi:
            audit_coro = self._start_audit(sw_upgrade)

            with mock.patch.object(sw_upgrade, "nfvi_update", return_value=True):
                audit_coro.send(self.TIMER_ID)

            mock_reschedule.assert_called_once_with(self.TIMER_ID, 30)
            nfvi.get_kube_upgrade.assert_not_called()
            nfvi.get_kube_hosts.assert_not_called()

    def test_nfvi_audit_stops_when_nfvi_update_returns_false(
        self, mock_event, mock_save, mock_create_timer, mock_reschedule
    ):
        """When nfvi_update() returns False, the audit loop should stop."""
        sw_upgrade = self._create_sw_upgrade(
            kube_to_version=None,
            stage_name="sw-upgrade-worker-hosts",
        )

        with self._nfvi_patches():
            audit_coro = self._start_audit(sw_upgrade)

            with mock.patch.object(sw_upgrade, "nfvi_update", return_value=False):
                self.assertRaises(StopIteration, audit_coro.send, self.TIMER_ID)

            self.assertIsNone(sw_upgrade._nfvi_timer_id)
