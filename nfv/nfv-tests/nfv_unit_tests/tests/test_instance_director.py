#
# Copyright (c) 2015-2023, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from unittest import mock
import uuid

from nfv_unit_tests.tests import testcase
from nfv_unit_tests.tests import utils
from nfv_vim.directors._directors_defs import Operation
from nfv_vim.directors._directors_defs import OPERATION_TYPE
from nfv_vim.directors._instance_director import InstanceDirector
from nfv_vim import nfvi
from nfv_vim import objects
from nfv_vim.tables._image_table import ImageTable
from nfv_vim.tables._table import Table

# Constants
_audit_interval = 330
_audit_cooldown = 30
_recovery_cooldown = 30
_rebuild_timeout = 300
_reboot_timeout = 300
_migrate_timeout = 600


def fake_timer(a, b, c, d):
    return 1234


class TestInstanceDirector(testcase.NFVTestCase):
    def setUp(self):
        super().setUp()
        self._image_table = ImageTable()
        self._instance_table = Table()
        self._instance_type_table = Table()
        self._tenant_table = Table()

        # Don't attempt to write to the database while unit testing
        self._image_table.persist = False
        self._instance_table.persist = False
        self._instance_type_table.persist = False
        self._tenant_table.persist = False
        self._director = None

        self.instance_setup_func()

    def tearDown(self):
        super().tearDown()
        self._image_table.clear()
        self._instance_table.clear()
        self._instance_type_table.clear()
        self._tenant_table.clear()
        self._director = None

    def create_instance(
        self, instance_type_name, instance_name, recovery_priority=None
    ):
        """Create an instance."""

        tenant_uuid = uuid.uuid4()
        image_uuid = uuid.uuid4()

        tenant = objects.Tenant(tenant_uuid, "%s_name" % tenant_uuid, "", True)
        self._tenant_table[tenant_uuid] = tenant

        for instance_type in list(self._instance_type_table.values()):
            if instance_type.name == instance_type_name:
                instance_uuid = uuid.uuid4()

                nfvi_instance = nfvi.objects.v1.Instance(
                    instance_uuid,
                    instance_name,
                    tenant_uuid,
                    admin_state=nfvi.objects.v1.INSTANCE_ADMIN_STATE.UNLOCKED,
                    oper_state=nfvi.objects.v1.INSTANCE_OPER_STATE.ENABLED,
                    avail_status=[],
                    action=nfvi.objects.v1.INSTANCE_ACTION.NONE,
                    host_name="compute-0",
                    instance_type=utils.instance_type_to_flavor_dict(instance_type),
                    image_uuid=image_uuid,
                    recovery_priority=recovery_priority,
                )

                return objects.Instance(nfvi_instance)

        return None

    @mock.patch("nfv_common.timers.timers_create_timer", fake_timer)
    def instance_setup_func(self):
        """Setup for testing."""

        instance_type_uuid = uuid.uuid4()

        instance_type = objects.InstanceType(instance_type_uuid, "small")
        instance_type.update_details(
            vcpus=1,
            mem_mb=64,
            disk_gb=1,
            ephemeral_gb=0,
            swap_gb=0,
            guest_services=None,
            auto_recovery=True,
            live_migration_timeout=800,
            live_migration_max_downtime=500,
        )
        self._instance_type_table[instance_type_uuid] = instance_type

        self._director = InstanceDirector(
            max_concurrent_recovering_instances=4,
            max_concurrent_migrates_per_host=1,
            max_concurrent_evacuates_per_host=1,
            recovery_audit_interval=_audit_interval,
            recovery_audit_cooldown=_audit_cooldown,
            recovery_audit_batch_interval=2,
            recovery_cooldown=_recovery_cooldown,
            rebuild_timeout=_rebuild_timeout,
            reboot_timeout=_reboot_timeout,
            migrate_timeout=_migrate_timeout,
            single_hypervisor=False,
            recovery_threshold=250,
            max_throttled_recovering_instances=2,
        )

    @mock.patch("nfv_vim.tables.tables_get_tenant_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_type_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_table")
    def test_instance_director_recovery_list(
        self,
        tables_get_instance_table_mock,
        tables_get_instance_type_table_mock,
        tables_get_tenant_table_mock,
    ):
        """Test the instance director recovery list logic."""

        tables_get_tenant_table_mock.return_value = self._tenant_table
        tables_get_instance_table_mock.return_value = self._instance_table
        tables_get_instance_type_table_mock.return_value = self._instance_type_table

        instance_1 = self.create_instance("small", "instance_1")
        self._instance_table[instance_1.uuid] = instance_1

        # Validate that the Instance Director recovery_list creation
        # -- with no instances in the failed state, verify that the list is
        #    empty and the normal audit interval is returned
        (
            next_audit_interval,
            instance_recovery_list,
            instance_failed_list,
            instance_rebuilding_list,
            instance_migrating_list,
            instance_rebooting_list,
        ) = self._director._get_instance_recovery_list()
        assert next_audit_interval == _audit_interval
        assert 0 == len(instance_recovery_list)

        instance_1._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.FAILED
        )

        # -- with one instance in the failed state, but elapsed time is less
        #    than the recovery cooldown, verify that the list is empty, but
        #    the audit interval is set to the recovery cooldown period
        instance_1._elapsed_time_in_state = _recovery_cooldown - 1
        (
            next_audit_interval,
            instance_recovery_list,
            instance_failed_list,
            instance_rebuilding_list,
            instance_migrating_list,
            instance_rebooting_list,
        ) = self._director._get_instance_recovery_list()
        assert next_audit_interval == _recovery_cooldown
        assert 0 == len(instance_recovery_list)

        # -- with one instance in the failed state, but elapsed time is greater
        #    than or equal to the recovery cooldown, verify that the list contains
        #    one instance and the audit interval is set to the recovery cooldown
        #    period
        instance_1._elapsed_time_in_state = _recovery_cooldown
        (
            next_audit_interval,
            instance_recovery_list,
            instance_failed_list,
            instance_rebuilding_list,
            instance_migrating_list,
            instance_rebooting_list,
        ) = self._director._get_instance_recovery_list()
        assert next_audit_interval == _recovery_cooldown
        assert 1 == len(instance_recovery_list)
        assert instance_recovery_list[0].name == instance_1.name

    @mock.patch("nfv_vim.tables.tables_get_tenant_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_type_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_table")
    def test_instance_director_recovery_list_order(
        self,
        tables_get_instance_table_mock,
        tables_get_instance_type_table_mock,
        tables_get_tenant_table_mock,
    ):
        """Test the instance director recovery list ordering."""

        tables_get_tenant_table_mock.return_value = self._tenant_table
        tables_get_instance_table_mock.return_value = self._instance_table
        tables_get_instance_type_table_mock.return_value = self._instance_type_table

        instance_1 = self.create_instance("small", "instance_1")
        instance_1._elapsed_time_in_state = _recovery_cooldown
        instance_1._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.FAILED
        )
        instance_1._nfvi_instance["instance_type"]["vcpus"] = 1
        instance_1._nfvi_instance["instance_type"]["ram"] = 32
        instance_1._nfvi_instance["instance_type"]["disk"] = 2
        instance_1._nfvi_instance["instance_type"]["swap"] = 0
        self._instance_table[instance_1.uuid] = instance_1

        # Validate the Instance Director recovery_list order
        # -- with one instance in the failed state
        (
            next_audit_interval,
            instance_recovery_list,
            instance_failed_list,
            instance_rebuilding_list,
            instance_migrating_list,
            instance_rebooting_list,
        ) = self._director._get_instance_recovery_list()
        assert next_audit_interval == _recovery_cooldown
        assert 1 == len(instance_recovery_list)
        assert instance_recovery_list[0].name == instance_1.name

        instance_2 = self.create_instance("small", "instance_2")
        instance_2._elapsed_time_in_state = _recovery_cooldown
        instance_2._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.FAILED
        )
        instance_2._nfvi_instance["instance_type"]["vcpus"] = 2
        instance_2._nfvi_instance["instance_type"]["ram"] = 32
        instance_2._nfvi_instance["instance_type"]["disk"] = 1
        instance_2._nfvi_instance["instance_type"]["swap"] = 0
        self._instance_table[instance_2.uuid] = instance_2

        # -- with two instances in the failed state
        #    vcpus takes precedence over disk_gb
        (
            next_audit_interval,
            instance_recovery_list,
            instance_failed_list,
            instance_rebuilding_list,
            instance_migrating_list,
            instance_rebooting_list,
        ) = self._director._get_instance_recovery_list()
        assert next_audit_interval == _recovery_cooldown
        assert 2 == len(instance_recovery_list)
        assert instance_recovery_list[0].name == instance_2.name
        assert instance_recovery_list[1].name == instance_1.name

        instance_3 = self.create_instance("small", "instance_3", recovery_priority=5)
        instance_3._elapsed_time_in_state = _recovery_cooldown
        instance_3._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.FAILED
        )
        instance_3._nfvi_instance["instance_type"]["vcpus"] = 1
        instance_3._nfvi_instance["instance_type"]["ram"] = 32
        instance_3._nfvi_instance["instance_type"]["disk"] = 0
        instance_3._nfvi_instance["instance_type"]["swap"] = 0
        self._instance_table[instance_3.uuid] = instance_3

        # -- with three instances in the failed state
        #    recovery_priority takes precedence over instance size
        (
            next_audit_interval,
            instance_recovery_list,
            instance_failed_list,
            instance_rebuilding_list,
            instance_migrating_list,
            instance_rebooting_list,
        ) = self._director._get_instance_recovery_list()
        assert next_audit_interval == _recovery_cooldown
        assert 3 == len(instance_recovery_list)
        assert instance_recovery_list[0].name == instance_3.name
        assert instance_recovery_list[1].name == instance_2.name
        assert instance_recovery_list[2].name == instance_1.name

        instance_4 = self.create_instance("small", "instance_4", recovery_priority=1)
        instance_4._elapsed_time_in_state = _recovery_cooldown
        instance_4._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.FAILED
        )
        instance_4._nfvi_instance["instance_type"]["vcpus"] = 1
        instance_4._nfvi_instance["instance_type"]["ram"] = 32
        instance_4._nfvi_instance["instance_type"]["disk"] = 0
        instance_4._nfvi_instance["instance_type"]["swap"] = 0
        self._instance_table[instance_4.uuid] = instance_4

        # -- with four instances in the failed state
        #    recovery_priority sorts instances
        (
            next_audit_interval,
            instance_recovery_list,
            instance_failed_list,
            instance_rebuilding_list,
            instance_migrating_list,
            instance_rebooting_list,
        ) = self._director._get_instance_recovery_list()
        assert next_audit_interval == _recovery_cooldown
        assert 4 == len(instance_recovery_list)
        assert instance_recovery_list[0].name == instance_4.name
        assert instance_recovery_list[1].name == instance_3.name
        assert instance_recovery_list[2].name == instance_2.name
        assert instance_recovery_list[3].name == instance_1.name

        instance_5 = self.create_instance("small", "instance_5", recovery_priority=10)
        instance_5._elapsed_time_in_state = _recovery_cooldown
        instance_5._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.FAILED
        )
        instance_5._nfvi_instance["instance_type"]["vcpus"] = 2
        instance_5._nfvi_instance["instance_type"]["ram"] = 32
        instance_5._nfvi_instance["instance_type"]["disk"] = 0
        instance_5._nfvi_instance["instance_type"]["swap"] = 0
        self._instance_table[instance_5.uuid] = instance_5

        # -- with five instances in the failed state
        #    no recovery_priority treated the same as priority 10
        (
            next_audit_interval,
            instance_recovery_list,
            instance_failed_list,
            instance_rebuilding_list,
            instance_migrating_list,
            instance_rebooting_list,
        ) = self._director._get_instance_recovery_list()
        assert next_audit_interval == _recovery_cooldown
        assert 5 == len(instance_recovery_list)
        assert instance_recovery_list[0].name == instance_4.name
        assert instance_recovery_list[1].name == instance_3.name
        assert instance_recovery_list[2].name == instance_2.name
        assert instance_recovery_list[3].name == instance_5.name
        assert instance_recovery_list[4].name == instance_1.name

    @mock.patch("nfv_vim.tables.tables_get_image_table")
    @mock.patch("nfv_vim.tables.tables_get_tenant_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_type_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_table")
    @mock.patch("nfv_vim.dor.system_is_stabilized")
    @mock.patch("nfv_vim.dor.dor_is_complete")
    def test_instance_director_recover_instance(
        self,
        dor_is_complete_mock,
        system_is_stabilized_mock,
        tables_get_instance_table_mock,
        tables_get_instance_type_table_mock,
        tables_get_tenant_table_mock,
        tables_get_image_table_mock,
    ):
        """Test the instance director recover instance logic."""

        tables_get_tenant_table_mock.return_value = self._tenant_table
        tables_get_instance_table_mock.return_value = self._instance_table
        tables_get_instance_type_table_mock.return_value = self._instance_type_table
        tables_get_image_table_mock.return_value = self._image_table

        system_is_stabilized_mock.return_value = True
        dor_is_complete_mock.return_value = True

        instance_1 = self.create_instance("small", "instance_1")
        instance_1.fail = mock.Mock()
        instance_1.do_action = mock.Mock()
        instance_1._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.FAILED
        )

        self._director._is_host_enabled = mock.Mock(return_value=True)
        self._director._is_hypervisor_enabled = mock.Mock(return_value=True)
        self._director.upgrade_inprogress = mock.Mock(return_value=False)

        # Set_A
        # -- the first attempt to recover an instance that is failed on an
        #    enabled host, verify a reboot is attempted
        self._director.instance_recovered(instance_1)
        self._director.recover_instance(instance_1)
        instance_1.do_action.assert_called_with(
            objects.INSTANCE_ACTION_TYPE.REBOOT, initiated_by="director"
        )

        # -- a subsequent attempt to recover an instance that is failed on an
        #    enabled host and the instance has an image to rebuild from, verify
        #    a rebuild is attempted
        self._director.recover_instance(instance_1)
        instance_1.do_action.assert_called_with(
            objects.INSTANCE_ACTION_TYPE.REBUILD, initiated_by="director"
        )

        # Set_B
        # -- the first attempt to recover an instance that is failed on an
        #    enabled host, verify a reboot is attempted
        original_image_uuid = instance_1._nfvi_instance.image_uuid
        instance_1._nfvi_instance.image_uuid = None
        self._director.instance_recovered(instance_1)
        self._director.recover_instance(instance_1)
        instance_1.do_action.assert_called_with(
            objects.INSTANCE_ACTION_TYPE.REBOOT, initiated_by="director"
        )

        # -- a subsequent attempt to recover an instance that is failed on an
        #    enabled host and the instance does not have an image to rebuild from,
        #    verify a reboot is attempted
        self._director.recover_instance(instance_1)
        instance_1.do_action.assert_called_with(
            objects.INSTANCE_ACTION_TYPE.REBOOT, initiated_by="director"
        )
        instance_1._nfvi_instance.image_uuid = original_image_uuid

        # Set_C
        # -- instance is rebuilding or evacuating and the instance has an image
        #    to rebuild from, verify that a rebuild is attempted
        self._director.instance_recovered(instance_1)
        instance_1._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.REBUILDING
        self._director.recover_instance(instance_1)
        instance_1.do_action.assert_called_with(
            objects.INSTANCE_ACTION_TYPE.REBUILD, initiated_by="director"
        )

        # Set_D
        # -- instance is rebuilding or evacuating and the instance does not have an
        #    image to rebuild from, verify that a reboot is attempted
        original_image_uuid = instance_1._nfvi_instance.image_uuid
        instance_1._nfvi_instance.image_uuid = None
        self._director.recover_instance(instance_1)
        instance_1.do_action.assert_called_with(
            objects.INSTANCE_ACTION_TYPE.REBOOT, initiated_by="director"
        )
        instance_1._nfvi_instance.image_uuid = original_image_uuid
        instance_1._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.NONE

        # Set_E
        # -- instance is migrating and the instance has an image to rebuild from,
        #    verify that a rebuild is attempted
        self._director.instance_recovered(instance_1)
        instance_1._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.MIGRATING
        self._director.recover_instance(instance_1)
        instance_1.do_action.assert_called_with(
            objects.INSTANCE_ACTION_TYPE.REBUILD, initiated_by="director"
        )

        # Set_F
        # -- instance is migrating and the instance does not have an image to
        #    rebuild from, verify that a reboot is attempted
        original_image_uuid = instance_1._nfvi_instance.image_uuid
        instance_1._nfvi_instance.image_uuid = None
        self._director.recover_instance(instance_1)
        instance_1.do_action.assert_called_with(
            objects.INSTANCE_ACTION_TYPE.REBOOT, initiated_by="director"
        )
        instance_1._nfvi_instance.image_uuid = original_image_uuid
        instance_1._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.NONE

    @mock.patch("nfv_vim.tables.tables_get_tenant_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_table")
    def test_instance_director_host_disabling_okay(
        self,
        tables_get_instance_table_mock,
        tables_get_tenant_table_mock,
    ):
        """Test InstanceDirector._host_disabling_okay semantic checks.

        The test cases currently cover the host operation type HOST_LOCK.
        """

        host = mock.Mock()
        host.name = "compute-0"

        self._director._is_hypervisor_enabled = mock.Mock(return_value=True)
        self._director._hypervisors_available = mock.Mock(return_value=True)
        self._director._single_hypervisor = False

        instance_table = mock.Mock()
        tables_get_instance_table_mock.return_value = instance_table
        tables_get_tenant_table_mock.return_value = self._tenant_table

        # A non-HOST_LOCK operation returns early as okay without inspecting any
        # instances on the host.
        host_operation = Operation(OPERATION_TYPE.HOST_DISABLE)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is True
        instance_table.on_host.assert_not_called()

        # A paused instance rejects the lock when the operation is not a live
        # migration; disabling live-migration support keeps operation at
        # COLD_MIGRATE so the paused reject branch is reached.
        paused = self.create_instance("small", "paused")
        paused._live_migration_support = False
        paused._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.PAUSED
        )
        instance_table.on_host.return_value = [paused]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False

        # A suspended instance rejects the lock.
        suspended = self.create_instance("small", "suspended")
        suspended._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.SUSPENDED
        )
        instance_table.on_host.return_value = [suspended]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False

        # A migrating instance (in-flight, external trigger) is skipped and the
        # lock is allowed to proceed.
        migrating = self.create_instance("small", "migrating")
        migrating._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.MIGRATING
        instance_table.on_host.return_value = [migrating]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is True

        # A migrating instance followed by an active one: the migrating instance
        # is skipped (continue) and the loop goes on to evaluate the active
        # instance, which passes every check, so the lock is allowed to proceed.
        active = self.create_instance("small", "active")
        instance_table.on_host.return_value = [migrating, active]
        self._director._hypervisors_available.reset_mock()
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is True
        assert host_operation.is_failed() is False
        assert host_operation.instance_exists(migrating.uuid) is False
        assert host_operation.instance_exists(active.uuid) is False
        self._director._hypervisors_available.assert_called_once_with(
            min_count=1, excluded_hosts=[host.name]
        )

        # A migrating instance followed by a suspended one: the migrating
        # instance is skipped (continue) but the suspended instance is still
        # evaluated and rejects the lock.
        instance_table.on_host.return_value = [migrating, suspended]
        self._director._hypervisors_available.reset_mock()
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False
        assert host_operation.reason == (
            "Lock of host %s rejected because instance %s is suspended."
            % (host.name, suspended.name)
        )
        assert host_operation.instance_exists(migrating.uuid) is False
        assert host_operation.instance_exists(suspended.uuid) is True
        self._director._hypervisors_available.assert_not_called()

        # An active instance followed by a migrating one: the active instance
        # passes every check and the migrating instance is then skipped
        # (continue), so the lock is allowed to proceed.
        instance_table.on_host.return_value = [active, migrating]
        self._director._hypervisors_available.reset_mock()
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is True
        assert host_operation.is_failed() is False
        assert host_operation.total_instances == 0
        self._director._hypervisors_available.assert_called_once_with(
            min_count=1, excluded_hosts=[host.name]
        )

        # A suspended instance followed by a migrating one: the suspended
        # instance rejects the lock right away, so the migrating instance is
        # never evaluated.
        instance_table.on_host.return_value = [suspended, migrating]
        self._director._hypervisors_available.reset_mock()
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False
        assert host_operation.reason == (
            "Lock of host %s rejected because instance %s is suspended."
            % (host.name, suspended.name)
        )
        assert host_operation.total_instances == 1
        assert host_operation.instance_exists(suspended.uuid) is True
        assert host_operation.instance_exists(migrating.uuid) is False
        self._director._hypervisors_available.assert_not_called()

        # A cold-migrating instance rejects the lock; cold migration requires the
        # resizing action together with a COLD_MIGRATE action type.
        cold_migrating = self.create_instance("small", "cold_migrating")
        cold_migrating._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.RESIZING
        cold_migrating._action_data = mock.Mock()
        cold_migrating._action_data.action_type = (
            objects.INSTANCE_ACTION_TYPE.COLD_MIGRATE
        )
        instance_table.on_host.return_value = [cold_migrating]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False
        assert host_operation.reason == (
            "Lock of host %s rejected because instance %s is migrating."
            % (host.name, cold_migrating.name)
        )

        # A rebuilding instance rejects the lock.
        rebuilding = self.create_instance("small", "rebuilding")
        rebuilding._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.REBUILDING
        instance_table.on_host.return_value = [rebuilding]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False

        # An instance with an action in progress rejects the lock; rebooting is a
        # non-NONE action that is not one of the earlier-evaluated states.
        action_running = self.create_instance("small", "action_running")
        action_running._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.REBOOTING
        instance_table.on_host.return_value = [action_running]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False

        # A resized/resizing instance rejects the lock.
        resized = self.create_instance("small", "resized")
        resized._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.RESIZED
        )
        instance_table.on_host.return_value = [resized]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False

        # With no other hypervisors available for a multi-hypervisor system an
        # otherwise-migratable instance rejects the lock.
        active = self.create_instance("small", "active")
        instance_table.on_host.return_value = [active]
        self._director._hypervisors_available = mock.Mock(return_value=False)
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        result = self._director._host_disabling_okay(host, host_operation)
        assert result is False
        self._director._hypervisors_available.assert_called_with(
            min_count=1, excluded_hosts=[host.name]
        )

    @mock.patch("nfv_vim.dor.dor_is_complete")
    @mock.patch("nfv_vim.tables.tables_get_tenant_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_table")
    def test_instance_director_host_migrate_instances(
        self,
        tables_get_instance_table_mock,
        tables_get_tenant_table_mock,
        dor_is_complete_mock,
    ):
        """Test InstanceDirector._host_migrate_instances regular cases."""

        dor_is_complete_mock.return_value = True

        host = mock.Mock()
        host.name = "compute-0"

        self._director.upgrade_inprogress = mock.Mock(return_value=False)
        self._director._hypervisors_available = mock.Mock(return_value=True)
        self._director._single_hypervisor = False
        self._director.reschedule_audit_instances = mock.Mock()

        instance_table = mock.Mock()
        tables_get_instance_table_mock.return_value = instance_table
        tables_get_tenant_table_mock.return_value = self._tenant_table

        # A single cold-migrating instance rejects a HOST_LOCK
        cold_migrating = self.create_instance("small", "cold_migrating")
        cold_migrating._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.RESIZING
        cold_migrating._action_data = mock.Mock()
        cold_migrating._action_data.action_type = (
            objects.INSTANCE_ACTION_TYPE.COLD_MIGRATE
        )
        cold_migrating.do_action = mock.Mock()
        instance_table.on_host.return_value = [cold_migrating]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_failed() is True
        assert host_operation.reason == (
            "Lock of host %s failed because instance %s is migrating."
            % (host.name, cold_migrating.name)
        )
        assert host_operation.instance_exists(cold_migrating.uuid) is True
        cold_migrating.do_action.assert_not_called()

        # A single migrating instance rejects a MIGRATE_INSTANCES operation
        migrating = self.create_instance("small", "migrating")
        migrating._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.MIGRATING
        migrating.do_action = mock.Mock()
        instance_table.on_host.return_value = [migrating]
        host_operation = Operation(OPERATION_TYPE.MIGRATE_INSTANCES)
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_failed() is True
        assert host_operation.reason == (
            "Migrate instances from host %s failed because instance %s is migrating."
            % (host.name, migrating.name)
        )
        assert host_operation.instance_exists(migrating.uuid) is True
        migrating.do_action.assert_not_called()

        # A single cold-migrating instance also rejects a MIGRATE_INSTANCES
        # operation at the migrating/cold-migrating check.
        cold_migrating = self.create_instance("small", "cold_migrating")
        cold_migrating._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.RESIZING
        cold_migrating._action_data = mock.Mock()
        cold_migrating._action_data.action_type = (
            objects.INSTANCE_ACTION_TYPE.COLD_MIGRATE
        )
        cold_migrating.do_action = mock.Mock()
        instance_table.on_host.return_value = [cold_migrating]
        host_operation = Operation(OPERATION_TYPE.MIGRATE_INSTANCES)
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_failed() is True
        assert host_operation.reason == (
            "Migrate instances from host %s failed because instance %s is migrating."
            % (host.name, cold_migrating.name)
        )
        assert host_operation.instance_exists(cold_migrating.uuid) is True
        cold_migrating.do_action.assert_not_called()

        # When DOR is not complete a MIGRATE_INSTANCES operation returns early
        dor_is_complete_mock.return_value = False
        active = self.create_instance("small", "active")
        active.do_action = mock.Mock()
        instance_table.on_host.return_value = [active]
        host_operation = Operation(OPERATION_TYPE.MIGRATE_INSTANCES)
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_failed() is False
        assert host_operation.is_inprogress() is False
        assert host_operation.instance_exists(active.uuid) is False
        active.do_action.assert_not_called()
        self._director.reschedule_audit_instances.assert_called_once_with(
            self._director._recovery_audit_cooldown
        )

        # A HOST_LOCK_FORCE operation returns early
        dor_is_complete_mock.return_value = True
        self._director.reschedule_audit_instances.reset_mock()
        active = self.create_instance("small", "active")
        active.do_action = mock.Mock()
        instance_table.on_host.return_value = [active]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK_FORCE)
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_failed() is False
        assert host_operation.is_inprogress() is False
        assert host_operation.instance_exists(active.uuid) is False
        active.do_action.assert_not_called()
        self._director.reschedule_audit_instances.assert_called_once_with(
            self._director._recovery_audit_cooldown
        )

    @mock.patch("nfv_vim.tables.tables_get_tenant_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_table")
    def test_instance_director_host_migrate_instances_deferred(
        self,
        tables_get_instance_table_mock,
        tables_get_tenant_table_mock,
    ):
        """Test InstanceDirector._host_migrate_instances HOST_LOCK deferral."""

        host = mock.Mock()
        host.name = "compute-0"

        self._director.upgrade_inprogress = mock.Mock(return_value=False)
        self._director._hypervisors_available = mock.Mock(return_value=True)
        self._director._single_hypervisor = False

        instance_table = mock.Mock()
        tables_get_instance_table_mock.return_value = instance_table
        tables_get_tenant_table_mock.return_value = self._tenant_table

        # A single migrating instance defers the lock: it is recorded as
        # inprogress, no new migrate action is issued, and the operation is not
        # failed.
        migrating = self.create_instance("small", "migrating")
        migrating._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.MIGRATING
        migrating.do_action = mock.Mock()
        instance_table.on_host.return_value = [migrating]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_inprogress() is True
        assert host_operation.is_failed() is False
        assert host_operation.instance_exists(migrating.uuid) is True
        migrating.do_action.assert_not_called()

        # Two instances, active first then migrating: re-running
        # _host_migrate_instances self-skips the already
        # processed active instance and defers the migrating one.
        active = self.create_instance("small", "active")
        active.do_action = mock.Mock()
        migrating.do_action.reset_mock()
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        instance_table.on_host.return_value = [active, migrating]
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.instance_exists(active.uuid) is True
        assert host_operation.instance_exists(migrating.uuid) is False
        active.do_action.assert_called_once_with(
            objects.INSTANCE_ACTION_TYPE.LIVE_MIGRATE,
            initiated_by=objects.INSTANCE_ACTION_INITIATED_BY.DIRECTOR,
            reason=mock.ANY,
        )
        migrating.do_action.assert_not_called()
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_inprogress() is True
        assert host_operation.is_failed() is False
        assert host_operation.instance_exists(migrating.uuid) is True
        active.do_action.assert_called_once_with(
            objects.INSTANCE_ACTION_TYPE.LIVE_MIGRATE,
            initiated_by=objects.INSTANCE_ACTION_INITIATED_BY.DIRECTOR,
            reason=mock.ANY,
        )
        migrating.do_action.assert_not_called()

        # Migrating instance first then active: the first call defers the
        # migrating instance; re-running self-skips the already deferred
        # migrating instance and live-migrates the active one.
        active.do_action.reset_mock()
        migrating.do_action.reset_mock()
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        instance_table.on_host.return_value = [migrating, active]
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.instance_exists(migrating.uuid) is True
        assert host_operation.instance_exists(active.uuid) is False
        active.do_action.assert_not_called()
        migrating.do_action.assert_not_called()
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_inprogress() is True
        assert host_operation.is_failed() is False
        assert host_operation.instance_exists(active.uuid) is True
        active.do_action.assert_called_once_with(
            objects.INSTANCE_ACTION_TYPE.LIVE_MIGRATE,
            initiated_by=objects.INSTANCE_ACTION_INITIATED_BY.DIRECTOR,
            reason=mock.ANY,
        )
        migrating.do_action.assert_not_called()

        # Migrating instance first then suspended: the first call defers the
        # migrating instance; re-running self-skips it and the suspended instance
        # now rejects the lock.
        suspended = self.create_instance("small", "suspended")
        suspended._nfvi_instance.avail_status.append(
            nfvi.objects.v1.INSTANCE_AVAIL_STATUS.SUSPENDED
        )
        suspended.do_action = mock.Mock()
        migrating.do_action.reset_mock()
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        instance_table.on_host.return_value = [migrating, suspended]
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_failed() is False
        assert host_operation.instance_exists(migrating.uuid) is True
        assert host_operation.instance_exists(suspended.uuid) is False
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_failed() is True
        assert host_operation.instance_exists(suspended.uuid) is True
        migrating.do_action.assert_not_called()
        suspended.do_action.assert_not_called()

        # A rejectable instance (suspended) at the front of the table rejects the
        # lock immediately, before the migrating instance is ever evaluated.
        migrating.do_action.reset_mock()
        suspended.do_action.reset_mock()
        instance_table.on_host.return_value = [suspended, migrating]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        self._director._host_migrate_instances(host, host_operation)
        assert host_operation.is_failed() is True
        assert host_operation.instance_exists(suspended.uuid) is True
        assert host_operation.instance_exists(migrating.uuid) is False
        suspended.do_action.assert_not_called()
        migrating.do_action.assert_not_called()

    @mock.patch("nfv_vim.dor.dor_is_complete")
    @mock.patch("nfv_vim.tables.tables_get_tenant_table")
    @mock.patch("nfv_vim.tables.tables_get_instance_table")
    def test_instance_director_host_evacuate_instances(
        self,
        tables_get_instance_table_mock,
        tables_get_tenant_table_mock,
        dor_is_complete_mock,
    ):
        """Test cases for InstanceDirector _host_evacuate_instances."""

        dor_is_complete_mock.return_value = True

        host = mock.Mock()
        host.name = "compute-0"

        self._director.upgrade_inprogress = mock.Mock(return_value=False)
        self._director._hypervisors_available = mock.Mock(return_value=True)
        self._director._single_hypervisor = False

        instance_table = mock.Mock()
        tables_get_instance_table_mock.return_value = instance_table
        tables_get_tenant_table_mock.return_value = self._tenant_table

        # A single migrating instance rejects a HOST_LOCK; the evacuate path has
        # no deferral branch, so the migrating check fails the lock.
        migrating = self.create_instance("small", "migrating")
        migrating._nfvi_instance.action = nfvi.objects.v1.INSTANCE_ACTION.MIGRATING
        migrating.do_action = mock.Mock()
        instance_table.on_host.return_value = [migrating]
        host_operation = Operation(OPERATION_TYPE.HOST_LOCK)
        self._director._host_evacuate_instances(host, host_operation)
        assert host_operation.is_failed() is True
        assert host_operation.instance_exists(migrating.uuid) is True
        migrating.do_action.assert_not_called()
