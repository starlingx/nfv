#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit test for get_instance tolerating a transient Neutron ports failure.

A failed ports fetch is thrown into the get_instance generator at the ports
yield by the task scheduler (e.g. a 500 while a neutron-server replica
restarts). The fix wraps that yield so the instance is still reported from
nova data instead of the whole get_instance being abandoned.
"""

import sys
from unittest import mock
import uuid

from nfv_unit_tests.tests import testcase

from nfv_plugins.nfvi_plugins import nfvi_compute_api
from nfv_plugins.nfvi_plugins.openstack import exceptions


class _Result:
    """Minimal completed task result carrying data."""

    def __init__(self, data):
        self._data = data

    def is_complete(self):
        return True

    @property
    def data(self):
        return self._data


class _Future:
    """Minimal future: work() is a no-op; result is fed by the driver."""

    def __init__(self):
        self.result = None

    def set_timeouts(self, _timeouts):
        pass

    def work(self, _target, *_args, **_kwargs):
        pass


class TestGetInstancePortsDecouple(testcase.NFVTestCase):

    def _server_data(self):
        return {
            "server": {
                "id": str(uuid.uuid4()),
                "name": "testvm",
                "tenant_id": uuid.uuid4().hex,
                "OS-EXT-STS:vm_state": "active",
                "OS-EXT-STS:task_state": None,
                "OS-EXT-STS:power_state": 1,
                "OS-EXT-SRV-ATTR:host": "compute-0",
                "updated": "2026-01-01T00:00:00Z",
                "flavor": {"extra_specs": {}},
                "image": {"id": uuid.uuid4().hex},
                "metadata": {},
                "os-extended-volumes:volumes_attached": [],
            }
        }

    def test_ports_failure_thrown_at_yield_is_tolerated(self):
        """A ports failure thrown at the ports yield must not propagate.

        On the pre-fix code the yield is outside the guard, so the thrown
        exception escapes get_instance (this test would raise). With the fix
        the yield is wrapped, the capability is left unknown (None, never
        computed from empty ports), and get_instance proceeds to its callback.
        """
        api = nfvi_compute_api.NFVIComputeAPI()
        api._directory = mock.Mock()
        api._token = mock.Mock()
        api._token.is_expired.return_value = False

        captured = []

        def _callback():
            # Mirror the real callback: receive the response, then keep the
            # generator alive so get_instance's callback.send()/close() do not
            # raise StopIteration (PEP 479 -> RuntimeError) back into the step.
            captured.append((yield))
            while True:
                yield

        cb = _callback()
        next(cb)

        future = _Future()
        gen = api.get_instance(future, "inst-uuid", None, cb)

        next(gen)  # -> nova.get_server yield (token skipped: valid token)
        future.result = _Result(self._server_data())
        gen.send(future.result)  # -> ports yield

        ports_exc = exceptions.OpenStackRestAPIException(
            "GET", "/v2.0/ports", {}, None, 500, "err", "err", [], b"", "ports down"
        )

        with mock.patch.object(
            nfvi_compute_api, "instance_supports_live_migration"
        ) as mock_cap:
            escaped = None
            try:
                gen.throw(ports_exc)
            except StopIteration:
                pass
            except Exception as exc:  # noqa: B902
                escaped = exc

            # Core contract: the ports failure is caught, not propagated.
            self.assertIsNone(
                escaped, "ports failure must be tolerated, got: %r" % escaped
            )
            # Capability must be left unknown, never computed from empty ports.
            mock_cap.assert_not_called()
            # get_instance proceeded and reported the instance with the
            # capability unset (None).
            self.assertTrue(captured, "callback was not invoked")
            self.assertTrue(captured[-1].get("completed"))
            self.assertIsNone(captured[-1]["result-data"].live_migration_support)

    def test_ports_success_path_unchanged(self):
        """With a healthy ports result the capability is computed as before.

        No-regression guard: when the ports query succeeds, get_instance
        still calls instance_supports_live_migration and reports the
        instance normally.
        """
        api = nfvi_compute_api.NFVIComputeAPI()
        api._directory = mock.Mock()
        api._token = mock.Mock()
        api._token.is_expired.return_value = False

        captured = []

        def _callback():
            # Mirror the real callback: receive the response, then keep the
            # generator alive so get_instance's callback.send()/close() do not
            # raise StopIteration (PEP 479 -> RuntimeError) back into the step.
            captured.append((yield))
            while True:
                yield

        cb = _callback()
        next(cb)

        future = _Future()
        gen = api.get_instance(future, "inst-uuid", None, cb)

        next(gen)  # -> nova.get_server yield (token skipped: valid token)
        future.result = _Result(self._server_data())
        gen.send(future.result)  # -> ports yield

        with mock.patch.object(
            nfvi_compute_api,
            "instance_supports_live_migration",
            return_value=True,
        ) as mock_cap:
            # Feed a healthy ports result (no throw) and let the generator run.
            try:
                gen.send(_Result({"ports": []}))
            except StopIteration:
                pass

            # Success path: the capability IS computed from the ports result.
            mock_cap.assert_called_once()
            self.assertTrue(captured, "callback was not invoked")
            self.assertTrue(captured[-1].get("completed"))


if __name__ == "__main__":
    sys.exit(0)
