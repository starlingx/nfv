#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import testtools
from unittest import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_vim import nfvi

from nfv_vim.objects import HOST_NAME
from nfv_vim.objects import HOST_PERSONALITY
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.objects import SwUpgrade
from nfv_vim.strategy._strategy import strategy_rebuild_from_dict
from nfv_vim.strategy._strategy import SwUpgradeStrategy

from nfv_unit_tests.tests import sw_update_testcase


# TODO(jkraitbe): Update this when retry count is decicded.
# utility method for the formatting of unlock-hosts stage as dict
# workers default to 5 retries with 120 second delay between attempts
# std controllers and storage have 0 retries
def _unlock_hosts_stage_as_dict(host_names, retry_count=5, retry_delay=120):
    return {
        'name': 'unlock-hosts',
        'entity_names': host_names,
        # 'retry_count': retry_count,
        # 'retry_delay': retry_delay,
        # 'timeout': 1800,
    }


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestSwUpgradeStrategy(sw_update_testcase.SwUpdateStrategyTestCase):

    def create_sw_upgrade_strategy(self,
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            max_parallel_worker_hosts=10,
            alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            release='starlingx-24.03.1',
            rollback=False,
            nfvi_upgrade=None,
            single_controller=False
    ):
        """
        Create a software update strategy
        """
        strategy = SwUpgradeStrategy(
            uuid=str(uuid.uuid4()),
            controller_apply_type=controller_apply_type,
            storage_apply_type=storage_apply_type,
            worker_apply_type=worker_apply_type,
            max_parallel_worker_hosts=max_parallel_worker_hosts,
            default_instance_action=default_instance_action,
            alarm_restrictions=alarm_restrictions,
            release=release,
            rollback=rollback,
            ignore_alarms=[],
            single_controller=single_controller,
        )

        if nfvi_upgrade is True:
            nfvi_upgrade = nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'Y',
                },
                None,
            )

        strategy.nfvi_upgrade = nfvi_upgrade
        return strategy

    def _gen_aiosx_hosts_and_strategy(
            self,
            openstack=True,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            rollback=False,
            **kwargs,
    ):
        self.create_host('controller-0', aio=True, openstack_installed=openstack)

        controller_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                controller_hosts.append(host)

        strategy = self.create_sw_upgrade_strategy(
            single_controller=True,
            default_instance_action=default_instance_action,
            worker_apply_type=worker_apply_type,
            rollback=rollback,
            **kwargs,
        )

        return controller_hosts, strategy

    def _gen_aiodx_hosts_and_strategy(
            self,
            openstack=True,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            rollback=False,
            **kwargs,
    ):
        self.create_host('controller-0', aio=True, openstack_installed=openstack)
        self.create_host('controller-1', aio=True, openstack_installed=openstack)

        controller_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                controller_hosts.append(host)

        strategy = self.create_sw_upgrade_strategy(
            default_instance_action=default_instance_action,
            worker_apply_type=worker_apply_type,
            rollback=rollback,
            **kwargs,
        )

        return controller_hosts, strategy

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_worker_stages_ignore(self):
        """
        Test the sw_upgrade strategy add worker strategy stages:
        - ignore apply
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

        self.create_instance_group(
            'instance_group_1',
            ['test_instance_0', 'test_instance_1'],
            [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        assert success is True, f"Strategy creation failed: {reason}"

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 0
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_worker_stages_parallel_migrate_anti_affinity(self):
        """
        Test the sw_upgrade strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - hosts with no instances upgraded first
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            max_parallel_worker_hosts=2
        )

        strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-2', 'compute-3'],
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-2', 'compute-3']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-0']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-1']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_worker_stages_parallel_migrate_ten_hosts(self):
        """
        Test the sw_upgrade strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - hosts with no instances upgraded first
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            max_parallel_worker_hosts=3
        )

        strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-1', 'compute-5'],
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-1', 'compute-5']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0',
                                       'test_instance_2',
                                       'test_instance_3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-2', 'compute-3']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-0', 'compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(
                         ['compute-0', 'compute-2', 'compute-3']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_4',
                                       'test_instance_6',
                                       'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4', 'compute-6', 'compute-7']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-4', 'compute-6', 'compute-7']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(
                         ['compute-4', 'compute-6', 'compute-7']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_8',
                                       'test_instance_9']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-8', 'compute-9']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-8', 'compute-9']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(
                         ['compute-8', 'compute-9']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_worker_stages_parallel_migrate_for_aio(self):
        """
        Test the sw_upgrade strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - AIO hosts upgraded first in serial
        - hosts with no instances upgraded next
        - instances migrated
        - for AIO controllers, the last step is wait-data-sync
        - for workers, the last step is wait-alarms-clear (openstack workers)
        """
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_6", 'controller-0')
        self.create_instance('small', "test_instance_7", 'controller-1')

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=3
        )

        strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['controller-0'],
                      'entity_names': ['test_instance_6']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-0']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 2400},
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['controller-1'],
                      'entity_names': ['test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-1']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 2400},
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-1'],
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-1']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600},
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-0', 'compute-2', 'compute-3'],
                      'entity_names': ['test_instance_0',
                                       'test_instance_2',
                                       'test_instance_3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-2', 'compute-3']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-0', 'compute-2', 'compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(
                         ['compute-0', 'compute-2', 'compute-3']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-4'],
                      'entity_names': ['test_instance_4']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-4']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-4']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_worker_stages_parallel_migrate_fifty_hosts(self):
        """
        Test the sw_upgrade strategy add worker strategy stages:
        - parallel apply
        - migrate instance action
        Verify:
        - hosts with no instances upgraded first
        - host aggregate limits enforced
        """
        for x in range(0, 50):
            self.create_host('compute-%02d' % x)

        for x in range(2, 47):
            self.create_instance('small',
                                 "test_instance_%02d" % x,
                                 'compute-%02d' % x)

        self.create_host_aggregate('aggregate-1',
                                   ["compute-%02d" % x for x in range(0, 25)])
        self.create_host_aggregate('aggregate-2',
                                   ["compute-%02d" % x for x in range(25, 50)])

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            max_parallel_worker_hosts=5
        )

        strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        host_sets = [[0, 1, 47, 48, 49],
                     [2, 3, 25, 26],
                     [4, 5, 27, 28],
                     [6, 7, 29, 30],
                     [8, 9, 31, 32],
                     [10, 11, 33, 34],
                     [12, 13, 35, 36],
                     [14, 15, 37, 38],
                     [16, 17, 39, 40],
                     [18, 19, 41, 42],
                     [20, 21, 43, 44],
                     [22, 23, 45, 46],
                     [24]
                     ]
        instance_sets = list(host_sets)
        instance_sets[0] = []

        stage_hosts = list()
        stage_instances = list()

        for x in range(0, len(host_sets) - 1):
            stage_hosts.append(["compute-%02d" % host_num for host_num in host_sets[x]])
            stage_instances.append(
                ["test_instance_%02d" % host_num for host_num in instance_sets[x]])

        expected_results = {
            'total_stages': 13,
            'stages': [
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': stage_hosts[0],
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': stage_hosts[0]},
                     {'name': 'upgrade-hosts',
                      'entity_names': stage_hosts[0]},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(stage_hosts[0]),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                },
            ]
        }

        for x in range(1, len(stage_hosts)):
            expected_results['stages'].append(
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': stage_hosts[x],
                      'entity_names': stage_instances[x]},
                     {'name': 'lock-hosts',
                      'entity_names': stage_hosts[x]},
                     {'name': 'upgrade-hosts',
                      'entity_names': stage_hosts[x]},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(stage_hosts[x]),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 }
            )

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_worker_stages_serial_migrate(self):
        """
        Test the sw_upgrade strategy add worker strategy stages:
        - serial apply
        - migrate instance action
        Verify:
        - hosts with no instances upgraded first
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-2']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600},
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-3']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600},
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-0'],
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-0']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600},
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-1'],
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-1']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600},
                 ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_non_openstack_worker_stages_serial(self):
        """
        Test the sw_upgrade strategy add worker strategy stages:
        - workers with no openstack installed
        - serial apply
        - no migrate instance action
        Verify:
        - final step is SystemStabilize
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        strategy._add_worker_strategy_stages(worker_hosts=sorted_worker_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': [f'compute-{i}']},
                        {'name': 'upgrade-hosts',
                         'entity_names': [f'compute-{i}']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': [f'compute-{i}']},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ]
                }
                for i in range(4)
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_worker_stages_serial_migrate_locked_instance(self):
        """
        Test the sw_upgrade strategy add worker strategy stages:
        - serial apply
        - migrate instance action
        - locked instance in instance group
        Verify:
        - stages not created
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        assert success is False, "Strategy creation did not fail"

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_storage_stages_ignore(self):
        """
        Test the sw_upgrade strategy add storage strategy stages:
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

        strategy = self.create_sw_upgrade_strategy(
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

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_storage_stages_parallel_host_group(self):
        """
        Test the sw_upgrade strategy add storage strategy stages:
        - parallel apply
        Verify:
        - storage-0 upgraded first
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

        strategy = self.create_sw_upgrade_strategy(
            storage_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL
        )

        strategy._add_storage_strategy_stages(storage_hosts=sorted_storage_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-upgrade-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['storage-0', 'storage-2']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['storage-0', 'storage-2']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     _unlock_hosts_stage_as_dict(['storage-0', 'storage-2']),
                     {'name': 'wait-data-sync',
                      'timeout': 1800}
                 ]
                },
                {'name': 'sw-upgrade-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                      'entity_names': ['storage-1', 'storage-3']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['storage-1', 'storage-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     _unlock_hosts_stage_as_dict(['storage-1', 'storage-3']),
                     {'name': 'wait-data-sync',
                      'timeout': 1800}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_storage_stages_serial(self):
        """
        Test the sw_upgrade strategy add storage strategy stages:
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

        strategy = self.create_sw_upgrade_strategy(
            storage_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL
        )

        strategy._add_storage_strategy_stages(storage_hosts=sorted_storage_hosts,
                                              reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {
                    'name': 'sw-upgrade-storage-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': [f'storage-{i}']},
                        {'name': 'upgrade-hosts',
                         'entity_names': [f'storage-{i}']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': [f'storage-{i}']},
                        {'name': 'wait-data-sync', 'timeout': 1800},
                    ]
                }
                for i in range(4)
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_0)
    def test_sw_upgrade_strategy_controller_stages_serial(self):
        """
        Test the sw_upgrade strategy add controller strategy stages:
        - serial apply
        Verify:
        - controller-0 upgraded
        """
        self.create_host('controller-0')
        self.create_host('controller-1')

        controller_hosts = []
        for host in list(self._host_table.values()):
            if (HOST_PERSONALITY.CONTROLLER in host.personality and
                    HOST_NAME.CONTROLLER_0 == host.name):
                controller_hosts.append(host)

        strategy = self.create_sw_upgrade_strategy()

        strategy._add_controller_strategy_stages(controllers=controller_hosts,
                                                 reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-0']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_controller_stages_serial_start_upgrade(self):
        """
        Test the sw_upgrade strategy add controller strategy stages:
        - serial apply
        Verify:
        - controller-1 and controller-0 upgraded
        """
        self.create_host('controller-0')
        self.create_host('controller-1')

        controller_hosts = []
        for host in list(self._host_table.values()):
            if (HOST_PERSONALITY.CONTROLLER in host.personality):
                controller_hosts.append(host)

        strategy = self.create_sw_upgrade_strategy()

        strategy._add_controller_strategy_stages(controllers=controller_hosts,
                                                 reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-upgrade-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-0']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400},
                 ]
                },
                {'name': 'sw-upgrade-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-1']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_aio_stages_serial(self):
        """
        Test the sw_upgrade strategy add controller strategy stages:
        - aio hosts
        - serial apply
        Verify:
        - controller-0 and controller-1 upgraded
        """
        self.create_host('controller-0', aio=True, openstack_installed=False)
        self.create_host('controller-1', aio=True, openstack_installed=False)

        controller_hosts = []
        for host in list(self._host_table.values()):
            if (HOST_PERSONALITY.CONTROLLER in host.personality and
                    HOST_NAME.CONTROLLER_0 == host.name):
                controller_hosts.append(host)

        worker_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
        # Sort worker hosts so the order of the steps is deterministic
        sorted_worker_hosts = sorted(worker_hosts, key=lambda host: host.name)

        strategy = self.create_sw_upgrade_strategy(worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL)

        success, reason = strategy._add_controller_strategy_stages(
            controllers=controller_hosts,
            reboot=True)

        assert success is True, ""
        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 0,
        }
        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

        strategy._add_worker_strategy_stages(
            worker_hosts=sorted_worker_hosts,
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-0']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400}
                 ]
                },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-1']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400}
                 ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_upgrade_strategy_aiosx_controllers_serial_rr(self):
        """
        Test the sw_upgrade strategy add controller strategy stages:
        - aio-sx host
        - serial apply
        - reboot required
        - stop_start instances
        - no instances
        Verify:
        - failure
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy()

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=True)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts', 'entity_names': ['controller-0'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_upgrade_strategy_build_complete_serial_migrate_start_complete(self):
        """
        Test the sw_upgrade strategy build_complete:
        - serial apply
        - migrate instance action
        - start and complete upgrade
        Verify:
        - hosts with no instances upgraded first
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')

        strategy = self.create_sw_upgrade_strategy(
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            nfvi_upgrade=True,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 8,
            'stages': [
                {'name': 'sw-upgrade-start',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'start-upgrade',
                      'release': strategy.nfvi_upgrade.release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                 ]
                },
                {'name': 'sw-upgrade-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-1']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400}
                 ]
                 },
                {'name': 'sw-upgrade-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-0']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400}
                 ]
                 },
                {'name': 'sw-upgrade-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                       'entity_names': ['storage-0']},
                     {'name': 'upgrade-hosts',
                       'entity_names': ['storage-0']},
                     {'name': 'system-stabilize',
                       'timeout': 15},
                     {'name': 'unlock-hosts',
                       'entity_names': ['storage-0']},
                     {'name': 'wait-data-sync',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-upgrade-storage-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'lock-hosts',
                       'entity_names': ['storage-1']},
                     {'name': 'upgrade-hosts',
                       'entity_names': ['storage-1']},
                     {'name': 'system-stabilize',
                       'timeout': 15},
                     {'name': 'unlock-hosts',
                       'entity_names': ['storage-1']},
                     {'name': 'wait-data-sync',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 1800}
                 ]
                 },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-1']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600},
                 ]
                 },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'host_names': ['compute-0'],
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                       'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-0']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600},
                 ]
                 },
                {'name': 'sw-upgrade-complete',
                 'total_steps': 4,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'activate-upgrade',
                      'release': strategy.nfvi_upgrade.release},
                     {'name': 'complete-upgrade',
                      'release': strategy.nfvi_upgrade.release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                  ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_flipper('controller-1', 'controller-0', n=2))
    def test_sw_upgrade_strategy_build_complete_serial_migrate(self):
        """
        Test the sw_upgrade strategy build_complete:
        - serial apply
        - migrate instance action
        - start on controller-1
        Verify:
        - hosts with no instances upgraded first
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('compute-0')
        self.create_host('compute-1')

        self.create_instance('small',
                             "test_instance_0",
                             'compute-0')

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            nfvi_upgrade=True,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 6,
            'stages': [
                {'name': 'sw-upgrade-start',
                 'total_steps': 5,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'start-upgrade',
                      'release': strategy.nfvi_upgrade.release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                 ]
                },
                {'name': 'sw-upgrade-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-1']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400}
                 ]
                 },
                {'name': 'sw-upgrade-controllers',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['controller-0']),
                     {'name': 'wait-alarms-clear',
                      'ignore_alarms': ['900.005', '900.201', '750.006', '100.119', '900.701'],
                      'timeout': 2400}
                 ]
                 },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': []},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-1']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-upgrade-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'migrate-instances-from-host',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'upgrade-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     _unlock_hosts_stage_as_dict(['compute-0']),
                     {'name': 'wait-alarms-clear',
                      'timeout': 600}
                 ]
                 },
                {'name': 'sw-upgrade-complete',
                 'total_steps': 5,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'activate-upgrade',
                      'release': strategy.nfvi_upgrade.release},
                     {'name': 'complete-upgrade',
                      'release': strategy.nfvi_upgrade.release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                  ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_build_complete_invalid_state(self):
        """
        Test the sw_upgrade strategy build_complete:
        - invalid upgrade state
        Verify:
        - build fails
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            nfvi_upgrade=True,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        build_phase = strategy.build_phase.as_dict()

        expected_results = {
            'total_stages': 0,
            'result': 'initial',
        }

        sw_update_testcase.validate_phase(build_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_build_complete_unupgraded_controller_1(self):
        """
        Test the sw_upgrade strategy build_complete:
        - unupgraded controller host
        Verify:
        - build fails
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            nfvi_upgrade=True,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        build_phase = strategy.build_phase.as_dict()

        expected_results = {
            'total_stages': 0,
            'result': 'initial',
        }

        sw_update_testcase.validate_phase(build_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_build_complete_locked_controller(self):
        """
        Test the sw_upgrade strategy build_complete:
        - locked controller host
        Verify:
        - build fails
        """
        self.create_host('controller-0',
                         admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED)
        self.create_host('controller-1')
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            nfvi_upgrade=True,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        build_phase = strategy.build_phase.as_dict()

        expected_results = {
            'total_stages': 0,
            'result': 'failed',
            'result_reason':
                'all controller hosts must be unlocked-enabled-available'
        }

        sw_update_testcase.validate_phase(build_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_build_complete_locked_worker(self):
        """
        Test the sw_upgrade strategy build_complete:
        - locked worker host
        Verify:
        - build fails
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
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

        strategy = self.create_sw_upgrade_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            nfvi_upgrade=True,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        build_phase = strategy.build_phase.as_dict()

        expected_results = {
            'total_stages': 0,
            'result': 'failed',
            'result_reason':
                'all worker hosts must be unlocked-enabled-available'
        }

        sw_update_testcase.validate_phase(build_phase, expected_results)

    @testtools.skip('Retries not implemented')
    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_1)
    def test_sw_upgrade_strategy_controller_missing_strategy_fields(self):
        """
        Test the sw_upgrade strategy add controller strategy stages:
        - serial apply
        Verify:
        - controller-0 upgraded
        - the missing fields do not cause deserialization failures
        """
        self.create_host('controller-0')
        self.create_host('controller-1')

        controller_hosts = []
        for host in list(self._host_table.values()):
            if (HOST_PERSONALITY.CONTROLLER in host.personality and
                    HOST_NAME.CONTROLLER_0 == host.name):
                controller_hosts.append(host)
        strategy = self.create_sw_upgrade_strategy()
        strategy._add_controller_strategy_stages(controllers=controller_hosts,
                                                 reboot=True)

        strategy_dict = strategy.as_dict()
        # remove the fields that do not exist in the previous version
        #  - the retry fields in 'unlock'
        # in this strategy the unlock hosts stage is located at:
        # - first stage of apply is sw-upgrade-controllers for controller-0
        # - 4th step (index 3) in that stage is the unlock-hosts step

        # Ensure the field exists before we remove it
        self.assertEqual(
            120,
            strategy_dict['apply_phase']['stages'][0]['steps'][3]['retry_delay'])
        # remove the fields that would not exist in an older version
        strategy_dict['apply_phase']['stages'][0]['steps'][3].pop('retry_delay')
        strategy_dict['apply_phase']['stages'][0]['steps'][3].pop('retry_count')

        # rebuild from the dictionary. If the new code is not robust, it would
        # raise an exception
        new_strategy = strategy_rebuild_from_dict(strategy_dict)

        # the default value should be re-populated
        strategy_dict = new_strategy.as_dict()
        self.assertEqual(
            120,
            strategy_dict['apply_phase']['stages'][0]['steps'][3]['retry_delay'])
