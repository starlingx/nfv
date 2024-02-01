#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from unittest import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_vim import nfvi

from nfv_vim.objects import HOST_PERSONALITY
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.objects import SwPatch
from nfv_vim.strategy._strategy import SwPatchStrategy

from nfv_unit_tests.tests import sw_update_testcase


def create_sw_patch_strategy(
        controller_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        storage_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        swift_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        max_parallel_worker_hosts=10,
        default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
        alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
        single_controller=False):
    """
    Create a software update strategy
    """
    return SwPatchStrategy(
        uuid=str(uuid.uuid4()),
        controller_apply_type=controller_apply_type,
        storage_apply_type=storage_apply_type,
        swift_apply_type=swift_apply_type,
        worker_apply_type=worker_apply_type,
        max_parallel_worker_hosts=max_parallel_worker_hosts,
        default_instance_action=default_instance_action,
        alarm_restrictions=alarm_restrictions,
        ignore_alarms=[],
        single_controller=single_controller
    )


@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save', sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer', sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.strategy._strategy.get_local_host_name', sw_update_testcase.fake_host_name)
@mock.patch('nfv_vim.event_log._instance._event_issue', sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled', sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestSwPatchStrategy(sw_update_testcase.SwUpdateStrategyTestCase):
    """
    Software Patch Strategy Unit Tests
    """
    def test_sw_patch_strategy_worker_stages_ignore(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - ignore apply
        - stop start instance action
        Verify:
        - stages not created
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        assert success is True, "Strategy creation failed"

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 0
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_migrate_anti_affinity(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - hosts with no instances patched first
        - anti-affinity policy enforced
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_migrate_ten_hosts(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - hosts with no instances patched first
        - instances migrated
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')
        self.create_host('compute-6')
        self.create_host('compute-7')
        self.create_host('compute-8')
        self.create_host('compute-9')

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_6", 'compute-6')
        self.create_instance('small', "test_instance_7", 'compute-7')
        self.create_instance('small', "test_instance_8", 'compute-8')
        self.create_instance('small', "test_instance_9", 'compute-9')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0',
                                       'test_instance_2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_3',
                                       'test_instance_4']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3', 'compute-4']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3', 'compute-4']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3', 'compute-4']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_6',
                                       'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-6', 'compute-7']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-6', 'compute-7']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-6', 'compute-7']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_8',
                                       'test_instance_9']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-8', 'compute-9']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-8', 'compute-9']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-8', 'compute-9']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_migrate_host_aggregate(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - hosts with no instances patched first
        - host aggregate limits enforced
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')
        self.create_host('compute-6')
        self.create_host('compute-7')
        self.create_host('compute-8')
        self.create_host('compute-9')

        self.create_host_aggregate('aggregate-1', ['compute-0',
                                                   'compute-1',
                                                   'compute-2',
                                                   'compute-3',
                                                   'compute-4'])
        self.create_host_aggregate('aggregate-2', ['compute-5',
                                                   'compute-6',
                                                   'compute-7',
                                                   'compute-8',
                                                   'compute-9'])

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_6", 'compute-6')
        self.create_instance('small', "test_instance_7", 'compute-7')
        self.create_instance('small', "test_instance_8", 'compute-8')
        self.create_instance('small', "test_instance_9", 'compute-9')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0',
                                       'test_instance_6']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_2',
                                       'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_3',
                                       'test_instance_8']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_4',
                                       'test_instance_9']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_migrate_overlap_host_aggregate(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - hosts with no instances patched first
        - host aggregate limits enforced
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')
        self.create_host('compute-6')
        self.create_host('compute-7')
        self.create_host('compute-8')
        self.create_host('compute-9')

        self.create_host_aggregate('aggregate-1', ['compute-0',
                                                   'compute-1',
                                                   'compute-2',
                                                   'compute-3',
                                                   'compute-4'])
        self.create_host_aggregate('aggregate-2', ['compute-5',
                                                   'compute-6',
                                                   'compute-7',
                                                   'compute-8',
                                                   'compute-9'])
        self.create_host_aggregate('aggregate-3', ['compute-0',
                                                   'compute-1',
                                                   'compute-2',
                                                   'compute-3',
                                                   'compute-4',
                                                   'compute-5',
                                                   'compute-6',
                                                   'compute-7',
                                                   'compute-8',
                                                   'compute-9'])

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_6", 'compute-6')
        self.create_instance('small', "test_instance_7", 'compute-7')
        self.create_instance('small', "test_instance_8", 'compute-8')
        self.create_instance('small', "test_instance_9", 'compute-9')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0',
                                       'test_instance_6']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_2',
                                       'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_3',
                                       'test_instance_8']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_4',
                                       'test_instance_9']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_migrate_small_host_aggregate(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - hosts with no instances patched first
        - small host aggregate handled
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')
        self.create_host('compute-6')
        self.create_host('compute-7')
        self.create_host('compute-8')
        self.create_host('compute-9')

        self.create_host_aggregate('aggregate-1', ['compute-0',
                                                   'compute-1'])
        self.create_host_aggregate('aggregate-2', ['compute-2',
                                                   'compute-3',
                                                   'compute-4',
                                                   'compute-5',
                                                   'compute-6'])
        self.create_host_aggregate('aggregate-3', ['compute-7',
                                                   'compute-8',
                                                   'compute-9'])

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_1", 'compute-1')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_5", 'compute-5')
        self.create_instance('small', "test_instance_6", 'compute-6')
        self.create_instance('small', "test_instance_7", 'compute-7')
        self.create_instance('small', "test_instance_8", 'compute-8')
        self.create_instance('small', "test_instance_9", 'compute-9')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0',
                                       'test_instance_2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_1',
                                       'test_instance_3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1', 'compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1', 'compute-3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_4',
                                       'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4', 'compute-7']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-4', 'compute-7']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-4', 'compute-7']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_5',
                                       'test_instance_8']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-5', 'compute-8']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-5', 'compute-8']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-5', 'compute-8']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_6',
                                       'test_instance_9']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-6', 'compute-9']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-6', 'compute-9']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-6', 'compute-9']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_stop_start_anti_affinity(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - stop start instance action
        Verify:
        - hosts with no instances patched first
        - anti-affinity policy enforced
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_stop_start_anti_affinity_locked_instance(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - stop start instance action
        - locked instance in instance group
        Verify:
        - stage creation fails
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1',
                             admin_state=nfvi.objects.v1.INSTANCE_ADMIN_STATE.LOCKED)

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        assert success is False, "Strategy creation did not fail"

    def test_sw_patch_strategy_worker_stages_parallel_stop_start_host_aggregate(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - stop start instance action
        - test both reboot and no reboot cases
        Verify:
        - hosts with no instances patched first
        - host aggregate limits enforced
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_host_aggregate('aggregate-1', ['compute-0', 'compute-1'])

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches.
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            max_parallel_worker_hosts=3,
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        # Perform no-reboot parallel worker patches without any
        # grouping by aggregates or determining which hosts have VMs
        # max_parallel_worker_hosts is 3 (for 4 hosts) resulting in 2 stages
        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                     {'name': 'system-stabilize', 'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize', 'timeout': 30}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_stop_start_locked_host(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - stop start instance action
        - locked host
        Verify:
        - hosts with no instances patched first
        - locked host patched and rebooted
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3',
                         admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED)

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'reboot-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'wait-alarms-clear', 'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1']},
                     {'name': 'wait-alarms-clear', 'timeout': 600}
                 ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_stop_start_host_aggregate_locked_instance(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - stop start instance action
        - locked instance not in an instance group
        Verify:
        - hosts with no instances patched first
        - host aggregate limits enforced
        - locked instance not stopped or started
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_host_aggregate('aggregate-1', ['compute-0', 'compute-1'])

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1',
                             admin_state=nfvi.objects.v1.INSTANCE_ADMIN_STATE.LOCKED)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_stop_start_host_aggregate_single_host(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - stop start instance action
        Verify:
        - host aggregates with a single host are patched in parallel
        """
        self.create_host('compute-0')
        self.create_host('compute-1')

        self.create_host_aggregate('aggregate-1', ['compute-0'])
        self.create_host_aggregate('aggregate-2', ['compute-1'])

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_stop_start_anti_affinity_host_aggregate(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - stop start instance action
        Verify:
        - hosts with no instances patched first
        - anti-affinity policy and host aggregates enforced at same time
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_host_aggregate('aggregate-1', ['compute-1', 'compute-2'])

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')
        self.create_instance('small',
                             "test_instance_2",
                             'compute-2')
        self.create_instance('small',
                             "test_instance_3",
                             'compute-3')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0', 'test_instance_2', 'test_instance_3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-2', 'compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-2', 'compute-3']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0', 'test_instance_2', 'test_instance_3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_serial_stop_start(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - serial apply
        - stop start instance action
        - test both reboot and no reboot cases
        Verify:
        - hosts with no instances patched first
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'wait-alarms-clear'}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'wait-alarms-clear'}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear'}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_serial_no_openstack(self):
        """
        Test the sw_patch strategy with no openstack, add worker strategy stages:
        - serial apply
        - no stop start instance action
        - test both reboot and no reboot cases
        Verify:
        - hosts are patched in order and and doesn't wait for alarms to clear
        """
        self.create_host('compute-0', openstack_installed=False)
        self.create_host('compute-1', openstack_installed=False)
        self.create_host('compute-2', openstack_installed=False)
        self.create_host('compute-3', openstack_installed=False)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_no_openstack(self):
        """
        Test the sw_patch strategy with no openstack add worker strategy stages:
        - serial apply
        - no migrate instance action
        - test both reboot and no reboot cases
        Verify:
        - hosts are patched and and doesn't wait for alarms to clear
        """
        self.create_host('compute-0', openstack_installed=False)
        self.create_host('compute-1', openstack_installed=False)
        self.create_host('compute-2', openstack_installed=False)
        self.create_host('compute-3', openstack_installed=False)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_serial_stop_start_locked_host(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - serial apply
        - stop start instance action
        - locked host
        - test both reboot and no reboot cases
        Verify:
        - hosts with no instances patched first
        - locked host patched and rebooted
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2',
                         admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED)
        self.create_host('compute-3')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')
        self.create_instance('small',
                             "test_instance_2",
                             'compute-3')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 5,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'reboot-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_2']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_parallel_stop_start_max_hosts(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - parallel apply
        - stop start instance action
        Verify:
        - maximum host limit enforced
        """
        for x in range(0, 13):
            self.create_host('compute-%02d' % x)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            max_parallel_worker_hosts=5
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-00',
                                       'compute-01',
                                       'compute-02',
                                       'compute-03',
                                       'compute-04']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-00',
                                       'compute-01',
                                       'compute-02',
                                       'compute-03',
                                       'compute-04']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-00',
                                       'compute-01',
                                       'compute-02',
                                       'compute-03',
                                       'compute-04']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-05',
                                       'compute-06',
                                       'compute-07',
                                       'compute-08',
                                       'compute-09']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-05',
                                       'compute-06',
                                       'compute-07',
                                       'compute-08',
                                       'compute-09']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-05',
                                       'compute-06',
                                       'compute-07',
                                       'compute-08',
                                       'compute-09']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-10',
                                       'compute-11',
                                       'compute-12']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-10',
                                       'compute-11',
                                       'compute-12']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-10',
                                       'compute-11',
                                       'compute-12']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_serial_migrate(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - serial apply
        - migrate instance action
        - test both reboot and no reboot cases
        Verify:
        - hosts with no instances patched first
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_worker_stages_serial_migrate_locked_instance(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - serial apply
        - migrate instance action
        - locked instance in instance group
        - test both reboot and no reboot cases
        Verify:
        - stages not created for reboot case
        - for no reboot case:
          - hosts with no instances patched first
          - locked instance is not migrated
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0',
                             admin_state=nfvi.objects.v1.INSTANCE_ADMIN_STATE.LOCKED)
        self.create_instance('small',
                             "test_instance_1",
                             'compute-1')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        assert success is False, "Strategy creation did not fail"

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 30},
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_storage_stages_ignore(self):
        """
        Test the sw_patch strategy add storage strategy stages:
        - ignore apply
        Verify:
        - stages not created
        """
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('storage-2')
        self.create_host('storage-3')

        self.create_host_group('group-0',
                               ['storage-0', 'storage-1'],
                               [nfvi.objects.v1.HOST_GROUP_POLICY.STORAGE_REPLICATION])
        self.create_host_group('group-1',
                               ['storage-2', 'storage-3'],
                               [nfvi.objects.v1.HOST_GROUP_POLICY.STORAGE_REPLICATION])

        storage_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.STORAGE in host.personality:
                storage_hosts.append(host)
        # Sort hosts so the order of the steps is deterministic
        sorted_storage_hosts = sorted(storage_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            storage_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE
        )

        success, reason = strategy._add_storage_strategy_stages(
            storage_hosts=sorted_storage_hosts,
            reboot=True)

        assert success is True, "Strategy creation failed"

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 0
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_storage_stages_parallel_host_group(self):
        """
        Test the sw_patch strategy add storage strategy stages:
        - parallel apply
        - test both reboot and no reboot cases
        Verify:
        - host groups enforced
        """
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('storage-2')
        self.create_host('storage-3')

        self.create_host_group('group-0',
                               ['storage-0', 'storage-1'],
                               [nfvi.objects.v1.HOST_GROUP_POLICY.STORAGE_REPLICATION])
        self.create_host_group('group-1',
                               ['storage-2', 'storage-3'],
                               [nfvi.objects.v1.HOST_GROUP_POLICY.STORAGE_REPLICATION])

        storage_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.STORAGE in host.personality:
                storage_hosts.append(host)
        # Sort hosts so the order of the steps is deterministic
        sorted_storage_hosts = sorted(storage_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            storage_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL
        )

        strategy._add_storage_strategy_stages(storage_hosts=sorted_storage_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['storage-0', 'storage-2']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['storage-0', 'storage-2']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['storage-0', 'storage-2']},
                     {'name': 'wait-data-sync',
                      'ignore_alarms': ['900.001',
                                        '900.005',
                                        '900.101',
                                        '200.001',
                                        '700.004',
                                        '280.002',
                                        '100.119'],
                      'timeout': 1800}
                 ]
                },
                {'name': 'sw-patch-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['storage-1', 'storage-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['storage-1', 'storage-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['storage-1', 'storage-3']},
                     {'name': 'wait-data-sync',
                      'ignore_alarms': ['900.001',
                                        '900.005',
                                        '900.101',
                                        '200.001',
                                        '700.004',
                                        '280.002',
                                        '100.119'],
                      'timeout': 1800}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            storage_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL
        )

        strategy._add_storage_strategy_stages(storage_hosts=sorted_storage_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-storage-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['storage-0', 'storage-2']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-storage-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['storage-1', 'storage-3']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_storage_stages_serial(self):
        """
        Test the sw_patch strategy add storage strategy stages:
        - serial apply
        """
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('storage-2')
        self.create_host('storage-3')

        self.create_host_group('group-0',
                               ['storage-0', 'storage-1'],
                               [nfvi.objects.v1.HOST_GROUP_POLICY.STORAGE_REPLICATION])
        self.create_host_group('group-1',
                               ['storage-2', 'storage-3'],
                               [nfvi.objects.v1.HOST_GROUP_POLICY.STORAGE_REPLICATION])

        storage_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.STORAGE in host.personality:
                storage_hosts.append(host)
        # Sort hosts so the order of the steps is deterministic
        sorted_storage_hosts = sorted(storage_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            storage_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        strategy._add_storage_strategy_stages(storage_hosts=sorted_storage_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['storage-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['storage-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['storage-0']},
                     {'name': 'wait-data-sync',
                      'ignore_alarms': ['900.001',
                                        '900.005',
                                        '900.101',
                                        '200.001',
                                        '700.004',
                                        '280.002',
                                        '100.119'],
                      'timeout': 1800}
                 ]
                },
                {'name': 'sw-patch-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['storage-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['storage-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['storage-1']},
                     {'name': 'wait-data-sync',
                      'ignore_alarms': ['900.001',
                                        '900.005',
                                        '900.101',
                                        '200.001',
                                        '700.004',
                                        '280.002',
                                        '100.119'],
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-patch-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['storage-2']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['storage-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['storage-2']},
                     {'name': 'wait-data-sync',
                      'ignore_alarms': ['900.001',
                                        '900.005',
                                        '900.101',
                                        '200.001',
                                        '700.004',
                                        '280.002',
                                        '100.119'],
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-patch-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['storage-3']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['storage-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['storage-3']},
                     {'name': 'wait-data-sync',
                      'ignore_alarms': ['900.001',
                                        '900.005',
                                        '900.101',
                                        '200.001',
                                        '700.004',
                                        '280.002',
                                        '100.119'],
                      'timeout': 1800}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_controller_stages_ignore(self):
        """
        Test the sw_patch strategy add controller strategy stages:
        - ignore apply
        Verify:
        - stages not created
        """
        self.create_host('controller-0')
        self.create_host('controller-1')

        controller_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.CONTROLLER in host.personality:
                controller_hosts.append(host)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            controller_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE
        )

        success, reason = strategy._add_controller_strategy_stages(
            controllers=controller_hosts,
            reboot=True)
        assert success is True, "Strategy creation failed"

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 0
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_controller_stages_serial(self):
        """
        Test the sw_patch strategy add controller strategy stages:
        - serial apply
        - test both reboot and no reboot cases
        Verify:
        - patch mate controller first
        """
        self.create_host('controller-0')
        self.create_host('controller-1')

        controller_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.CONTROLLER in host.personality:
                controller_hosts.append(host)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        strategy._add_controller_strategy_stages(controllers=controller_hosts,
                                                 reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800},
                 ]
                },
                {'name': 'sw-patch-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800},
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        strategy._add_controller_strategy_stages(controllers=controller_hosts,
                                                 reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-controllers',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-controllers',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_controller_stages_serial_openstack_not_installed(self):
        """
        Test the sw_patch strategy add controller strategy stages:
        - serial apply
        - test both reboot and no reboot cases
        Verify:
        - patch mate controller first
        """
        self.create_host('controller-0', openstack_installed=False)
        self.create_host('controller-1', openstack_installed=False)

        controller_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.CONTROLLER in host.personality:
                controller_hosts.append(host)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        strategy._add_controller_strategy_stages(controllers=controller_hosts,
                                                 reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800},
                 ]
                },
                {'name': 'sw-patch-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800},
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        strategy._add_controller_strategy_stages(controllers=controller_hosts,
                                                 reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-controllers',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                },
                {'name': 'sw-patch-controllers',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 30}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_duplex_stages_parallel_stop_start(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - aio hosts
        - parallel apply treated as serial
        - stop start instance action
        - test both reboot and no reboot cases
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small',
                             "test_instance_0",
                             'controller-0')
        self.create_instance('small',
                             "test_instance_1",
                             'controller-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800},
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                  ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize'}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize'}
                  ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_duplex_stages_serial_stop_start(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - aio hosts
        - serial apply
        - stop start instance action
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small',
                             "test_instance_0",
                             'controller-0')
        self.create_instance('small',
                             "test_instance_1",
                             'controller-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                  ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_duplex_stages_serial_stop_start_no_instances(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - aio hosts
        - no instances
        - serial apply
        - stop start instance action
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                  ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_duplex_stages_serial_stop_start_no_openstack(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - aio hosts
        - no instances
        - serial apply
        - stop start instance action
        """
        self.create_host('controller-0', aio=True, openstack_installed=False)
        self.create_host('controller-1', aio=True, openstack_installed=False)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                  ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_plus_stages_parallel_stop_start(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - aio hosts plus workers
        - parallel apply treated as serial
        - stop start instance action
        - test both reboot and no reboot cases
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small',
                             "test_instance_0",
                             'controller-0')
        self.create_instance('small',
                             "test_instance_1",
                             'controller-1')

        self.create_host('compute-0')
        self.create_host('compute-1')

        self.create_instance('small',
                             "test_instance_2",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_3",
                             'compute-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        # Test reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                             reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800},
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_2', 'test_instance_3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_2', 'test_instance_3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        # Test no reboot patches
        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                             reboot=False)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize'}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize'}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0', 'compute-1']},
                     {'name': 'system-stabilize'}
                 ]
                 },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_plus_stages_serial_stop_start(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - aio hosts plus workers
        - serial apply
        - stop start instance action
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small',
                             "test_instance_0",
                             'controller-0')
        self.create_instance('small',
                             "test_instance_1",
                             'controller-1')

        self.create_host('compute-0')
        self.create_host('compute-1')

        self.create_instance('small',
                             "test_instance_2",
                             'compute-0')
        self.create_instance('small',
                             "test_instance_3",
                             'compute-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                             reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_2']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_3']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_plus_stages_serial_stop_start_no_instances(
            self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - aio hosts plus workers
        - no instances
        - serial apply
        - stop start instance action
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_host('compute-0')
        self.create_host('compute-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                             reboot=True)

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_simplex_stages_serial_migrate(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - simplex aio host
        - serial apply
        - migrate instance action
        Verify:
        - stage creation fails
        """
        self.create_host('controller-0', aio=True)

        self.create_instance('small',
                             "test_instance_0",
                             'controller-0')
        self.create_instance('small',
                             "test_instance_1",
                             'controller-0')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            single_controller=True
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=worker_hosts,
            reboot=True)

        assert success is False, "Strategy creation did not fail"

    def test_sw_patch_strategy_aio_simplex_stages_serial_no_openstack(
            self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - simplex aio host (no openstack)
        - serial apply
        - no migrate instance action
        """
        self.create_host('controller-0', aio=True, openstack_installed=False)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            single_controller=True
        )

        strategy._add_worker_strategy_stages(worker_hosts=worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800},
                 ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_simplex_stages_serial_stop_start(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - simplex aio host
        - serial apply
        - stop start instance action
        """
        self.create_host('controller-0', aio=True)

        self.create_instance('small',
                             "test_instance_0",
                             'controller-0')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            single_controller=True
        )

        strategy._add_worker_strategy_stages(worker_hosts=worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800},
                 ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_aio_simplex_stages_serial_stop_start_no_instances(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - simplex aio host
        - no instances
        - serial apply
        - stop start instance action
        """
        self.create_host('controller-0', aio=True)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            single_controller=True
        )

        strategy._add_worker_strategy_stages(worker_hosts=worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 1800}
                 ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_patch_strategy_build_complete_parallel_stop_start(self):
        """
        Test the sw_patch strategy build_complete:
        - parallel apply
        - stop start instance action
        Verify:
        - hosts with no instances patched first
        - anti-affinity policy enforced
        """
        self.create_host('compute-0')
        self.create_host('compute-1')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')

        strategy = create_sw_patch_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START
        )

        fake_patch_obj = SwPatch()
        strategy.sw_update_obj = fake_patch_obj

        nfvi_sw_patches = list()
        sw_patch = nfvi.objects.v1.SwPatch(
            'PATCH_0001', '12.01', 'Applied', 'Available')
        nfvi_sw_patches.append(sw_patch)
        strategy.nfvi_sw_patches = nfvi_sw_patches

        nfvi_sw_patch_hosts = list()
        for host_name in ['compute-0', 'compute-1']:
            host = nfvi.objects.v1.HostSwPatch(
                host_name, 'worker', '12.01', True, False, 'idle', False,
                False)
            nfvi_sw_patch_hosts.append(host)
        strategy.nfvi_sw_patch_hosts = nfvi_sw_patch_hosts

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-patch-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'sw-patch-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)
