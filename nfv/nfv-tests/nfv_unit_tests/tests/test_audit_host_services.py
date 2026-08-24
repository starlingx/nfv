#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for AuditHostServicesTaskWork.

Two behaviours are covered:

1. A failed query must not have the service state inferred from the platform
   health of the host. Fabricating "enabled" caches a value that is simply
   wrong, and HostDirector.enable_host_services() then reports an enable
   complete without ever calling nova.

2. A compute service that nova truthfully reports as disabled, on a host VIM
   intends to be in service, must be reconciled. The host FSM excludes the
   compute service from the aggregate host service state, so nothing else
   owns the mismatch.
"""

from unittest import mock

from nfv_common import state_machine
from nfv_vim.host_fsm._host_task_work import AuditHostServicesTaskWork
from nfv_vim.host_fsm._host_task_work import (
    MAX_COMPUTE_SERVICE_RECONCILE_ATTEMPTS,
)
from nfv_vim import objects

from nfv_unit_tests.tests import testcase


def _send(callback, response):
    """Deliver a response to a coroutine callback.

    The nfvi plugin layer drives these callbacks to completion, so the
    StopIteration raised as the generator returns is expected.
    """

    try:
        callback.send(response)
    except StopIteration:
        pass


class FakeTask:
    """Records the task-work results reported by the work item."""

    def __init__(self):
        self.results = []

    def task_work_complete(self, result, reason):
        self.results.append((result, reason))


class FakeHost:
    """Stands in for nfv_vim.objects.Host.

    The real Host pulls in the host state machine, the event log and the
    database. This mirrors the semantics of every member the code under test
    touches, including the reconcile attempt counter.
    """

    def __init__(
        self,
        *,
        name="compute-0",
        enabled=True,
        host_services_locked=False,
        compute_state=objects.HOST_SERVICE_STATE.ENABLED,
        compute_configured=True,
        personality=objects.HOST_PERSONALITY.WORKER,
    ):
        self.name = name
        self.uuid = "uuid-" + name
        self.personality = personality
        self.host_services_locked = host_services_locked
        self._enabled = enabled
        # The real Host seeds _host_service_state only for services that are
        # configured on the host, so a controller has no 'compute' key at all.
        self._host_service_state = {
            objects.HOST_SERVICES.NETWORK: objects.HOST_SERVICE_STATE.ENABLED
        }
        if compute_configured:
            self._host_service_state[objects.HOST_SERVICES.COMPUTE] = compute_state
        self._compute_service_reconcile_attempts = 0
        self.failure_reasons = []

    def is_enabled(self):
        return self._enabled

    def host_service_state(self, service):
        return self._host_service_state[service]

    def host_services_update(self, service, host_service_state, reason=None):
        self._host_service_state[service] = host_service_state

    def update_failure_reason(self, reason):
        self.failure_reasons.append(reason)

    @property
    def compute_service_reconcile_attempts(self):
        return self._compute_service_reconcile_attempts

    @compute_service_reconcile_attempts.setter
    def compute_service_reconcile_attempts(self, value):
        self._compute_service_reconcile_attempts = value

    def clear_compute_service_reconcile_attempts(self):
        self._compute_service_reconcile_attempts = 0


class TestAuditHostServices(testcase.NFVTestCase):
    """Unit tests for the compute host services audit callback."""

    def setUp(self):
        super().setUp()

        self._enable_calls = []

        def _fake_enable(host_uuid, host_name, host_personality, callback):
            self._enable_calls.append(host_name)
            _send(callback, {"completed": True, "reason": ""})

        patcher = mock.patch(
            "nfv_vim.nfvi.nfvi_enable_compute_host_services",
            side_effect=_fake_enable,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        sw_update_patcher = mock.patch(
            "nfv_vim.database._database_sw_update.database_sw_update_exists",
            return_value=False,
        )
        self._sw_update_exists = sw_update_patcher.start()
        self.addCleanup(sw_update_patcher.stop)

    def _audit(self, host, response, force_pass=True, service=None):
        """Run one audit callback cycle, as AuditEnabledHostTask runs it."""

        if service is None:
            service = objects.HOST_SERVICES.COMPUTE
        task = FakeTask()
        work = AuditHostServicesTaskWork(task, host, service, force_pass=force_pass)
        # StateTaskWork holds only a weakref to the task.
        work._test_task_ref = task
        _send(work._callback(), response)
        return task

    def test_query_failure_retains_last_known_state(self):
        """A failed query must not invent a state from host health."""

        host = FakeHost(enabled=True, compute_state=objects.HOST_SERVICE_STATE.DISABLED)

        task = self._audit(
            host,
            {
                "completed": False,
                "result-data": "enabled",
                "reason": "nova-api HTTP 500",
            },
        )

        self.assertEqual(
            objects.HOST_SERVICE_STATE.DISABLED,
            host.host_service_state(objects.HOST_SERVICES.COMPUTE),
        )
        self.assertEqual(
            [(state_machine.STATE_TASK_WORK_RESULT.SUCCESS, "")], task.results
        )
        self.assertEqual([], self._enable_calls)

    def test_disabled_compute_on_enabled_host_is_reconciled(self):
        """A truthful disabled reading on a healthy host re-drives enable."""

        host = FakeHost(enabled=True)

        task = self._audit(
            host, {"completed": True, "result-data": "disabled", "reason": ""}
        )

        self.assertEqual(
            objects.HOST_SERVICE_STATE.DISABLED,
            host.host_service_state(objects.HOST_SERVICES.COMPUTE),
        )
        self.assertEqual(
            [(state_machine.STATE_TASK_WORK_RESULT.SUCCESS, "")], task.results
        )
        self.assertEqual([host.name], self._enable_calls)
        self.assertEqual(1, host.compute_service_reconcile_attempts)

    def test_enabled_compute_does_not_reconcile(self):
        """Steady state issues no enable and clears the attempt counter."""

        host = FakeHost(enabled=True)
        host.compute_service_reconcile_attempts = 2

        self._audit(host, {"completed": True, "result-data": "enabled", "reason": ""})

        self.assertEqual([], self._enable_calls)
        self.assertEqual(0, host.compute_service_reconcile_attempts)

    def test_reconcile_is_bounded(self):
        """Reconcile gives up after the attempt limit."""

        host = FakeHost(enabled=True)

        for _ in range(MAX_COMPUTE_SERVICE_RECONCILE_ATTEMPTS + 3):
            self._audit(
                host, {"completed": True, "result-data": "disabled", "reason": ""}
            )

        self.assertEqual(
            MAX_COMPUTE_SERVICE_RECONCILE_ATTEMPTS, len(self._enable_calls)
        )

    def test_reconcile_skipped_when_host_services_locked(self):
        """A lock or an orchestrated disable is a deliberate intent."""

        host = FakeHost(enabled=True, host_services_locked=True)

        self._audit(host, {"completed": True, "result-data": "disabled", "reason": ""})

        self.assertEqual([], self._enable_calls)
        self.assertEqual(0, host.compute_service_reconcile_attempts)

    def test_reconcile_skipped_when_host_not_enabled(self):
        """Only a host the platform reports in service is reconciled."""

        host = FakeHost(enabled=False)

        self._audit(host, {"completed": True, "result-data": "disabled", "reason": ""})

        self.assertEqual([], self._enable_calls)

    def test_reconcile_skipped_during_software_update(self):
        """An update strategy owns host service state while it runs."""

        host = FakeHost(enabled=True)
        self._sw_update_exists.return_value = True

        self._audit(host, {"completed": True, "result-data": "disabled", "reason": ""})

        self.assertEqual([], self._enable_calls)
        self.assertEqual(0, host.compute_service_reconcile_attempts)


class TestAuditHostServicesNoComputeService(testcase.NFVTestCase):
    """Regression tests for hosts with no compute service configured.

    Host._host_service_state is populated only for configured services, and
    Host.host_service_state() is a bare dict lookup. Reading the compute state
    unconditionally therefore raises KeyError on a controller and kills the VIM
    process, which SM reports as vim(disabled, failed). The audit callback must
    never read or reconcile the compute service on a host that does not have
    one.
    """

    def setUp(self):
        super().setUp()

        self._enable_calls = []

        def _fake_enable(host_uuid, host_name, host_personality, callback):
            self._enable_calls.append(host_name)
            _send(callback, {"completed": True, "reason": ""})

        patcher = mock.patch(
            "nfv_vim.nfvi.nfvi_enable_compute_host_services",
            side_effect=_fake_enable,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        sw_patcher = mock.patch(
            "nfv_vim.database._database_sw_update.database_sw_update_exists",
            return_value=False,
        )
        sw_patcher.start()
        self.addCleanup(sw_patcher.stop)

    def _controller(self):
        return FakeHost(
            name="controller-0",
            enabled=True,
            compute_configured=False,
            personality=objects.HOST_PERSONALITY.CONTROLLER,
        )

    def _audit(self, host, service, response, force_pass=True):
        task = FakeTask()
        work = AuditHostServicesTaskWork(task, host, service, force_pass=force_pass)
        work._test_task_ref = task
        _send(work._callback(), response)
        return task

    def test_the_missing_key_is_real(self):
        """Guard the premise: reading compute state on a controller raises."""

        host = self._controller()
        self.assertRaises(
            KeyError, host.host_service_state, objects.HOST_SERVICES.COMPUTE
        )

    def test_network_audit_success_on_controller(self):
        """A successful non-compute audit must not touch the compute state."""

        host = self._controller()

        task = self._audit(
            host,
            objects.HOST_SERVICES.NETWORK,
            {"completed": True, "result-data": "enabled", "reason": ""},
        )

        self.assertEqual(
            [(state_machine.STATE_TASK_WORK_RESULT.SUCCESS, "")], task.results
        )
        self.assertEqual([], self._enable_calls)

    def test_network_audit_reporting_disabled_on_controller(self):
        """A disabled non-compute service must not trigger a compute reconcile."""

        host = self._controller()

        task = self._audit(
            host,
            objects.HOST_SERVICES.NETWORK,
            {"completed": True, "result-data": "disabled", "reason": ""},
        )

        self.assertEqual(
            objects.HOST_SERVICE_STATE.DISABLED,
            host.host_service_state(objects.HOST_SERVICES.NETWORK),
        )
        self.assertEqual(
            [(state_machine.STATE_TASK_WORK_RESULT.SUCCESS, "")], task.results
        )
        self.assertEqual([], self._enable_calls)

    def test_network_audit_force_pass_on_controller(self):
        """The force-pass log path must not read the compute state either."""

        host = self._controller()

        task = self._audit(
            host,
            objects.HOST_SERVICES.NETWORK,
            {
                "completed": False,
                "result-data": "enabled",
                "reason": "nova-api HTTP 500",
            },
        )

        self.assertEqual(
            objects.HOST_SERVICE_STATE.ENABLED,
            host.host_service_state(objects.HOST_SERVICES.NETWORK),
        )
        self.assertEqual(
            [(state_machine.STATE_TASK_WORK_RESULT.SUCCESS, "")], task.results
        )
        self.assertEqual([], self._enable_calls)
