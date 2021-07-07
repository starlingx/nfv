#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import fixtures

import pprint
import uuid

from nfv_vim import host_fsm
from nfv_vim import nfvi
from nfv_vim import objects

from nfv_vim.strategy._strategy import strategy_rebuild_from_dict
from nfv_vim.tables._host_aggregate_table import HostAggregateTable
from nfv_vim.tables._host_group_table import HostGroupTable
from nfv_vim.tables._host_table import HostTable
from nfv_vim.tables._instance_group_table import InstanceGroupTable
from nfv_vim.tables._instance_table import InstanceTable
from nfv_vim.tables._table import Table

from . import testcase  # noqa: H304
from . import utils  # noqa: H304

from nfv_vim.objects import HOST_PERSONALITY

DEBUG_PRINTING = False


def validate_strategy_persists(strategy):
    """
    Validate that the strategy can be converted to a dict and back without any
    loss of data.
    Note: This is not foolproof - it won't catch cases where the an object
    attribute was missed from both the as_dict and from_dict methods.
    """
    strategy_dict = strategy.as_dict()
    new_strategy = strategy_rebuild_from_dict(strategy_dict)

    if DEBUG_PRINTING:
        if strategy.as_dict() != new_strategy.as_dict():
            print("==================== Strategy ====================")
            pprint.pprint(strategy.as_dict())
            print("============== Converted Strategy ================")
            pprint.pprint(new_strategy.as_dict())
    assert strategy.as_dict() == new_strategy.as_dict(), \
        "Strategy changed when converting to/from dict"


def validate_phase(phase, expected_results):
    """
    Validate that the phase matches everything contained in expected_results
    Note: there is probably a super generic, pythonic way to do this, but this
    is good enough (tm).
    """
    if DEBUG_PRINTING:
        print("====================== Phase Results ========================")
        pprint.pprint(phase)
        print("===================== Expected Results ======================")
        pprint.pprint(expected_results)

    for key in expected_results:
        if key == 'stages':
            stage_number = 0
            for stage in expected_results[key]:
                apply_stage = phase[key][stage_number]
                for stages_key in stage:
                    if stages_key == 'steps':
                        step_number = 0
                        for step in stage[stages_key]:
                            apply_step = apply_stage[stages_key][step_number]
                            for step_key in step:
                                assert apply_step[step_key] == step[step_key], \
                                    "for [%s][%d][%s][%d][%s] found: %s but expected: %s" % \
                                    (key, stage_number, stages_key,
                                     step_number, step_key,
                                     apply_step[step_key], step[step_key])
                            step_number += 1
                    else:
                        assert apply_stage[stages_key] == stage[stages_key], \
                            "for [%s][%d][%s] found: %s but expected: %s" % \
                            (key, stage_number, stages_key,
                             apply_stage[stages_key], stage[stages_key])
                stage_number += 1
        else:
            assert phase[key] == expected_results[key], \
                "for [%s] found: %s but expected: %s" % \
                (key, phase[key], expected_results[key])


def fake_save(a):
    pass


def fake_timer(a, b, c, d):
    return 1234


def fake_host_name():
    return 'controller-0'


def fake_host_name_controller_1():
    return 'controller-1'


def fake_host_name_controller_0():
    return 'controller-0'


def fake_callback():
    return


def fake_event_issue(a, b, c, d):
    """
    Mock out the _event_issue function because it is being called when instance
    objects are created. It ends up trying to communicate with another thread
    (that doesn't exist) and this eventually leads to nosetests hanging if
    enough events are issued.
    """
    return None


def fake_nfvi_compute_plugin_disabled():
    return False


class SwUpdateStrategyTestCase(testcase.NFVTestCase):

    def setUp(self):
        """
        Setup for testing.
        """
        super(SwUpdateStrategyTestCase, self).setUp()
        self._tenant_table = Table()
        self._instance_type_table = Table()
        self._instance_table = InstanceTable()
        self._instance_group_table = InstanceGroupTable()
        self._host_table = HostTable()
        self._host_group_table = HostGroupTable()
        self._host_aggregate_table = HostAggregateTable()

        # Don't attempt to write to the database while unit testing
        self._tenant_table.persist = False
        self._instance_type_table.persist = False
        self._instance_table.persist = False
        self._instance_group_table.persist = False
        self._host_table.persist = False
        self._host_group_table.persist = False
        self._host_aggregate_table.persist = False

        self.useFixture(fixtures.MonkeyPatch('nfv_vim.tables._tenant_table._tenant_table',
                                             self._tenant_table))
        self.useFixture(fixtures.MonkeyPatch('nfv_vim.tables._host_table._host_table',
                                             self._host_table))
        self.useFixture(fixtures.MonkeyPatch('nfv_vim.tables._instance_group_table._instance_group_table',
                                             self._instance_group_table))
        self.useFixture(fixtures.MonkeyPatch('nfv_vim.tables._host_group_table._host_group_table',
                                             self._host_group_table))
        self.useFixture(fixtures.MonkeyPatch('nfv_vim.tables._host_aggregate_table._host_aggregate_table',
                                             self._host_aggregate_table))
        self.useFixture(fixtures.MonkeyPatch('nfv_vim.tables._instance_table._instance_table',
                                             self._instance_table))
        self.useFixture(fixtures.MonkeyPatch('nfv_vim.tables._instance_type_table._instance_type_table',
                                             self._instance_type_table))

        instance_type_uuid = str(uuid.uuid4())
        instance_type = objects.InstanceType(instance_type_uuid, 'small')
        instance_type.update_details(vcpus=1,
                                     mem_mb=64,
                                     disk_gb=1,
                                     ephemeral_gb=0,
                                     swap_gb=0,
                                     guest_services=None,
                                     auto_recovery=True,
                                     live_migration_timeout=800,
                                     live_migration_max_downtime=500)
        self._instance_type_table[instance_type_uuid] = instance_type

    def tearDown(self):
        """
        Cleanup testing setup.
        """
        super(SwUpdateStrategyTestCase, self).tearDown()
        self._tenant_table.clear()
        self._instance_type_table.clear()
        self._instance_table.clear()
        self._instance_group_table.clear()
        self._host_table.clear()
        self._host_group_table.clear()
        self._host_aggregate_table.clear()

    def create_instance(self, instance_type_name, instance_name, host_name,
                        admin_state=nfvi.objects.v1.INSTANCE_ADMIN_STATE.UNLOCKED):
        """
        Create an instance
        """
        tenant_uuid = str(uuid.uuid4())
        image_uuid = str(uuid.uuid4())

        tenant = objects.Tenant(tenant_uuid, "%s_name" % tenant_uuid, '', True)
        self._tenant_table[tenant_uuid] = tenant

        for instance_type in list(self._instance_type_table.values()):
            if instance_type.name == instance_type_name:
                instance_uuid = str(uuid.uuid4())

                nfvi_instance = nfvi.objects.v1.Instance(
                    instance_uuid, instance_name, tenant_uuid,
                    admin_state=admin_state,
                    oper_state=nfvi.objects.v1.INSTANCE_OPER_STATE.ENABLED,
                    avail_status=list(),
                    action=nfvi.objects.v1.INSTANCE_ACTION.NONE,
                    host_name=host_name,
                    instance_type=utils.instance_type_to_flavor_dict(
                        instance_type),
                    image_uuid=image_uuid)

                instance = objects.Instance(nfvi_instance)
                self._instance_table[instance.uuid] = instance
                return

        assert 0, "Unknown instance_type_name: %s" % instance_type_name

    def create_instance_group(self, name, members, policies):
        """
        Create an instance group
        """
        member_uuids = []

        for instance_uuid, instance in list(self._instance_table.items()):
            if instance.name in members:
                member_uuids.append(instance_uuid)

        nfvi_instance_group = nfvi.objects.v1.InstanceGroup(
            uuid=str(uuid.uuid4()),
            name=name,
            member_uuids=member_uuids,
            policies=policies
        )

        instance_group = objects.InstanceGroup(nfvi_instance_group)
        self._instance_group_table[instance_group.uuid] = instance_group

    def create_host(self,
                    host_name,
                    aio=False,
                    admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.UNLOCKED,
                    oper_state=nfvi.objects.v1.HOST_OPER_STATE.ENABLED,
                    avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.AVAILABLE,
                    software_load='12.01',
                    target_load='12.01',
                    openstack_installed=True):
        """
        Create a host
        """
        personality = ''

        openstack_control = False
        openstack_compute = False

        if host_name.startswith('controller'):
            personality = HOST_PERSONALITY.CONTROLLER
            if aio:
                personality = personality + ',' + HOST_PERSONALITY.WORKER
            if openstack_installed:
                openstack_control = True
                if aio:
                    openstack_compute = True
        elif host_name.startswith('compute'):
            personality = HOST_PERSONALITY.WORKER
            if openstack_installed:
                openstack_compute = True
        elif host_name.startswith('storage'):
            personality = HOST_PERSONALITY.STORAGE
        else:
            assert 0, "Invalid host_name: %s" % host_name

        nfvi_host = nfvi.objects.v1.Host(
            uuid=str(uuid.uuid4()),
            name=host_name,
            personality=personality,
            admin_state=admin_state,
            oper_state=oper_state,
            avail_status=avail_status,
            action=nfvi.objects.v1.HOST_ACTION.NONE,
            software_load=software_load,
            target_load=target_load,
            openstack_compute=openstack_compute,
            openstack_control=openstack_control,
            remote_storage=False,
            uptime='1000'
        )

        if admin_state == nfvi.objects.v1.HOST_ADMIN_STATE.UNLOCKED:
            host = objects.Host(nfvi_host,
                                initial_state=host_fsm.HOST_STATE.ENABLED)
        else:
            host = objects.Host(nfvi_host,
                                initial_state=host_fsm.HOST_STATE.DISABLED)

        self._host_table[host.name] = host

    def create_host_group(self, name, members, policies):
        """
        Create a host group
        """
        member_uuids = []

        for instance_uuid, instance in list(self._instance_table.items()):
            if instance.name in members:
                member_uuids.append(instance_uuid)

        nfvi_host_group = nfvi.objects.v1.HostGroup(
            name=name,
            member_names=members,
            policies=policies
        )

        host_group = objects.HostGroup(nfvi_host_group)
        self._host_group_table[host_group.name] = host_group

    def create_host_aggregate(self, name, host_names):
        """
        Create a host aggregate
        """
        nfvi_host_aggregate = nfvi.objects.v1.HostAggregate(
            name=name,
            host_names=host_names,
            availability_zone=''
        )

        host_aggregate = objects.HostAggregate(nfvi_host_aggregate)
        self._host_aggregate_table[host_aggregate.name] = host_aggregate
