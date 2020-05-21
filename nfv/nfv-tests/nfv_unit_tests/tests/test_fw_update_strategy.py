#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import mock
import uuid

from nfv_vim import nfvi

from nfv_vim.strategy._strategy import FwUpdateStrategy

from nfv_vim.objects import HOST_PERSONALITY
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION

from . import sw_update_testcase  # noqa: H304


def create_fw_update_strategy(
        controller_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        storage_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        max_parallel_worker_hosts=2,
        default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
        alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
        single_controller=False):
    """
    Create a firmware update strategy
    """
    return FwUpdateStrategy(
        uuid=str(uuid.uuid4()),
        controller_apply_type=controller_apply_type,
        storage_apply_type=storage_apply_type,
        worker_apply_type=worker_apply_type,
        max_parallel_worker_hosts=max_parallel_worker_hosts,
        default_instance_action=default_instance_action,
        alarm_restrictions=alarm_restrictions,
        ignore_alarms=[],
        single_controller=single_controller
    )


@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled', sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestFwUpdateStrategy(sw_update_testcase.SwUpdateStrategyTestCase):
    """
    Firmware Update Strategy Unit Tests
    """

    def test_fw_update_strategy_worker_stages_ignore(self):
        """
        Test the fw_update strategy add worker strategy stages:
        - ignore worker apply
        Verify:
        - stages not created ; fw update is only supported for worker nodes
        """

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')

        # default apply type is 'ignore' for all node types.
        # Only worker nodes support firmware upgrade.
        strategy = create_fw_update_strategy()

        worker_hosts = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)

        success, reason = strategy._add_worker_strategy_stages(
            sorted(worker_hosts, key=lambda host: host.name),
            reboot=True)

        assert success is True, "Strategy creation failed"

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'completion_percentage': 100,
            'total_stages': 0
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_storage_serial_no_instances(self):
        """
        Test the fw_update strategy on a storage system:
        - 2 controllers
        - 2 storage hosts
        - 4 worker hosts
        options
        - serial apply
        - no instances
        """

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts'},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts'},
                     {'name': 'lock-hosts',
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

    def test_fw_update_strategy_storage_parallel_no_instances(self):
        """
        Test the fw_update strategy on a storage system:
        - 2 controllers
        - 2 storage hosts
        - 4 worker hosts
        options
        - parallel apply ; max 3
        - no instances
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            max_parallel_worker_hosts=3)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_storage_serial_migrate(self):
        """
        Test the fw_update strategy on a storage system:
        - 2 controllers
        - 2 storage hosts
        - 4 worker hosts
        options
        - serial apply
        - migrate 3 instances
        """

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_1", 'compute-1')
        self.create_instance('small', "test_instance_2", 'compute-3')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-2']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-2']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-2']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-0']},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-1']},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-3']},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_2']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-3']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_storage_parallel_migrate(self):
        """
        Test the fw_update strategy on a storage system:
        - 2 controllers
        - 2 storage hosts
        - 4 worker hosts
        options
        - parallel apply ; max 4
        - migrate 4 instances
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')

        self.create_instance('small', "test_instance_1", 'compute-1')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=4)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-5']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-5']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-5']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-1', 'compute-2',
                                       'compute-3', 'compute-4']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_1',
                                       'test_instance_2',
                                       'test_instance_3',
                                       'test_instance_4']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1', 'compute-2',
                                       'compute-3', 'compute-4']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1', 'compute-2',
                                       'compute-3', 'compute-4']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_standard_serial_stop_start(self):
        """
        Test the fw_update strategy on a storage system:
        - 2 controllers
        - 2 storage hosts
        - 4 worker hosts
        options
        - serial apply
        - stop start 4 instances
        """

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')
        self.create_host('compute-6')
        self.create_host('compute-7')

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_1", 'compute-2')
        self.create_instance('small', "test_instance_2", 'compute-4')
        self.create_instance('small', "test_instance_3", 'compute-6')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 8,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-1']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-3']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-3']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-5']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-5']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-5']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-7']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-7']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-7']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-0']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-2']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-2']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-2']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-4']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_2']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-4']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-4']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_2']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts', 'entity_names': ['compute-6']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_3']},
                     {'name': 'lock-hosts', 'entity_names': ['compute-6']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts', 'entity_names': ['compute-6']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_3']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_standard_parallel_stop_start(self):
        """
        Test the fw_update strategy on a standard system:
        - 2 controllers
        - 8 worker hosts
        options
        - parallel apply ; max 10
        - stop start 8 instances
        """

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')
        self.create_host('compute-6')
        self.create_host('compute-7')

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_1", 'compute-1')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_5", 'compute-5')
        self.create_instance('small', "test_instance_6", 'compute-6')
        self.create_instance('small', "test_instance_7", 'compute-7')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            max_parallel_worker_hosts=10)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3',
                                       'compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1',
                                       'test_instance_2', 'test_instance_3',
                                       'test_instance_4', 'test_instance_5',
                                       'test_instance_6', 'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3',
                                       'compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3',
                                       'compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1',
                                       'test_instance_2', 'test_instance_3',
                                       'test_instance_4', 'test_instance_5',
                                       'test_instance_6', 'test_instance_7']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_standard_parallel_migrate_host_aggregate(self):
        """
        Test the fw_update strategy on a storage system:
        - 2 controllers
        - 10 worker hosts
        options
        - parallel apply ; max 10
        - migrate instances ; 1 per host ; 1 locked
        - hosts with no instances updated first
        - host aggregate limits enforced
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
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

        self.create_host_aggregate('aggregate-1', ['compute-0', 'compute-2',
                                                   'compute-4', 'compute-6'])

        self.create_host_aggregate('aggregate-2', ['compute-1', 'compute-3',
                                                   'compute-5', 'compute-7'])

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_1", 'compute-1')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3',
            admin_state=nfvi.objects.v1.INSTANCE_ADMIN_STATE.LOCKED)
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_5", 'compute-5')
        self.create_instance('small', "test_instance_6", 'compute-6')
        self.create_instance('small', "test_instance_7", 'compute-7')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=10)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-8', 'compute-9']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-8', 'compute-9']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-8', 'compute-9']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3']},
                     {'name': 'disable-host-services',
                      'entity_names': ['compute-0', 'compute-1',
                                        'compute-2', 'compute-3']},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1',
                                       'test_instance_2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'disable-host-services',
                     'entity_names': ['compute-4', 'compute-5',
                                      'compute-6', 'compute-7']},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_4', 'test_instance_5',
                                       'test_instance_6', 'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_standard_parallel_stop_start_host_aggregate(self):
        """
        Test the fw_update strategy on a standard system:
        -  2 controllers
        - 10 worker hosts
        options
        - parallel apply ; max 4
        - stop start instances ; 1 per host ; 1 locked
        - locked instances or hosts with no instances updated first
        - 2x4 host aggregate groups
        - hosts with locked instances or none at all are grouped
        """
        self.create_host('controller-0')
        self.create_host('controller-1')
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

        self.create_host_aggregate('aggregate-1', ['compute-0', 'compute-2',
                                                   'compute-4', 'compute-6'])

        self.create_host_aggregate('aggregate-2', ['compute-1', 'compute-3',
                                                   'compute-5', 'compute-7'])

        self.create_instance('small', "test_instance_0", 'compute-0', admin_state=nfvi.objects.v1.INSTANCE_ADMIN_STATE.LOCKED)
        self.create_instance('small', "test_instance_1", 'compute-1', admin_state=nfvi.objects.v1.INSTANCE_ADMIN_STATE.LOCKED)
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_5", 'compute-5')
        self.create_instance('small', "test_instance_6", 'compute-6')
        self.create_instance('small', "test_instance_7", 'compute-7')
        self.create_instance('small', "test_instance_8", 'compute-8')
        self.create_instance('small', "test_instance_9", 'compute-9')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            max_parallel_worker_hosts=4)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-8', 'compute-9']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_8', 'test_instance_9']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-8', 'compute-9']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-8', 'compute-9']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_8', 'test_instance_9']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_2', 'test_instance_3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-3']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_2', 'test_instance_3']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-4', 'compute-5']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_4', 'test_instance_5']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4', 'compute-5']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-4', 'compute-5']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_4', 'test_instance_5']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-6', 'compute-7']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_6', 'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-6', 'compute-7']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-6', 'compute-7']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_6', 'test_instance_7']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_standard_parallel_migrate_overlap_host_aggregate(self):
        """
        Test the fw_update strategy on a standard system:
        -  2 controllers
        - 10 worker hosts
        options
        - parallel apply ; max 2
        - migrate 10 instances ; 1 per worker host
        - locked instances or hosts with no instances updated first
        - 3 host aggregate groups with overlap ; 4, 3, 10
        - hosts with locked instances or none at all are grouped
        """

        self.create_host('controller-0')
        self.create_host('controller-1')
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

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1', 'compute-5']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_0',
                                       'test_instance_6']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-6']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_2',
                                       'test_instance_7']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-2', 'compute-7']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                 },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_3',
                                       'test_instance_8']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3', 'compute-8']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                 },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_4',
                                       'test_instance_9']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-4', 'compute-9']},
                     {'name': 'system-stabilize',
                      'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_sx(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 1 all-in-one controller
        options
        - serial apply
        - no instances
        """

        self.create_host('controller-0', aio=True)

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            single_controller=True)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_sx_stop_start(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 1 all-in-one controller
        options
        - serial apply
        - stop start 1 instance
        """
        self.create_host('controller-0', aio=True)

        self.create_instance('small', "test_instance_0", 'controller-0')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            single_controller=True)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_sx_migrate_reject(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 1 all-in-one controller
        options
        - serial apply
        - migrate instances ; not possible in sx
        """
        self.create_host('controller-0', aio=True)

        self.create_instance('small', "test_instance_0", 'controller-0')
        self.create_instance('small', "test_instance_1", 'controller-0')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            single_controller=True)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        success, reason = strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        assert success is False, "Strategy creation failed"

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'completion_percentage': 100,
            'total_stages': 0
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_sx_serial_migrate_no_openstack(self):
        """
        Test the sw_patch strategy add worker strategy stages:
        - 1 all-in-one controller host
        - no openstack
        - serial apply
        - migrate instance action with no instance
        """
        self.create_host('controller-0', aio=True, openstack_installed=False)

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            single_controller=True)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                 ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_dx_no_instances(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 2 all-in-one controllers
        options
        - serial apply
        - no instances
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_dx_migrate_instance(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 2 all-in-one controllers
        options
        - serial apply
        - migrate 1 instance
        """

        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small', "test_instance_0", 'controller-0')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            single_controller=False)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                  ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_dx_migrate_instances(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 2 all-in-one controllers
        options
        - serial apply
        - migrate 2 instances which switches the controller update order
        """

        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small', "test_instance_0", 'controller-0')
        self.create_instance('small', "test_instance_1", 'controller-1')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            single_controller=False)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                    ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_dx_stop_start_instance(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 2 all-in-one controllers
        options
        - serial
        - stop start 1 instance
        """

        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small', "test_instance_0", 'controller-0')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            single_controller=False)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)
        # assert success is False, "Strategy creation failed"

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                  ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_dx_stop_start_instances(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 2 all-in-one controllers
        options
        - serial
        - stop start instances
        """

        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_instance('small', "test_instance_0", 'controller-0')
        self.create_instance('small', "test_instance_1", 'controller-1')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            single_controller=False)

        fw_update_host_list = []
        for host in self._host_table.values():
            if HOST_PERSONALITY.WORKER in host.personality:
                fw_update_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 9,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_dx_plus_parallel_locked_hosts(self):
        """
        Test the fw_update strategy on an All-In-One system:
        - 2 all-in-one controllers
        - 6 computes ; 2 are locked
        options
        - parallel apply ; max 2
        - no instances
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        self.create_host('compute-0')
        self.create_host('compute-1',
                         admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
                         oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
                         avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE)
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5',
                         admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
                         oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
                         avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE)

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            max_parallel_worker_hosts=2)

        fw_update_worker_host_list = []
        for host in self._host_table.values():
            if host._nfvi_host.admin_state == nfvi.objects.v1.HOST_ADMIN_STATE.UNLOCKED:
                if HOST_PERSONALITY.WORKER in host.personality:
                    fw_update_worker_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_worker_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                      'total_steps': 7,
                      'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 6,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-3', 'compute-4']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-3', 'compute-4']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-3', 'compute-4']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_plus_parallel_migrate_anti_affinity(self):
        """
        Test the fw_update strategy on an All-In-One Plus system:
        - 2 all-in-one controllers
        - 6 worker hosts
        options
        - parallel apply ; max 2
        - migrate instances with 2 anti affinity groups
        """

        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_1", 'compute-1')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_5", 'compute-5')

        self.create_instance_group('instance_group_1',
                                   ['test_instance_0', 'test_instance_1'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        self.create_instance_group('instance_group_2',
                                   ['test_instance_3', 'test_instance_5'],
                                   [nfvi.objects.v1.INSTANCE_GROUP_POLICY.ANTI_AFFINITY])

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            max_parallel_worker_hosts=2)

        fw_update_worker_host_list = []
        for host in self._host_table.values():
            if host._nfvi_host.admin_state == nfvi.objects.v1.HOST_ADMIN_STATE.UNLOCKED:
                if HOST_PERSONALITY.WORKER in host.personality:
                    fw_update_worker_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_worker_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_0', 'test_instance_2']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-2']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-1', 'compute-3']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_1', 'test_instance_3']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-1', 'compute-3']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-1', 'compute-3']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-4', 'compute-5']},
                     {'name': 'disable-host-services'},
                     {'name': 'migrate-instances',
                      'entity_names': ['test_instance_4', 'test_instance_5']},
                     {'name': 'lock-hosts',
                      'entity_names': ['compute-4', 'compute-5']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-4', 'compute-5']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_fw_update_strategy_aio_plus_parallel_stop_start(self):
        """
        Test the fw_update strategy on an All-In-One Plus system:
        - 2 all-in-one controllers
        - 8 worker hosts
        options
        - parallel apply ; max 10
        - stop start 8 instances
        """
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('compute-3')
        self.create_host('compute-4')
        self.create_host('compute-5')
        self.create_host('compute-6')
        self.create_host('compute-7')

        self.create_instance('small', "test_instance_0", 'compute-0')
        self.create_instance('small', "test_instance_1", 'compute-1')
        self.create_instance('small', "test_instance_2", 'compute-2')
        self.create_instance('small', "test_instance_3", 'compute-3')
        self.create_instance('small', "test_instance_4", 'compute-4')
        self.create_instance('small', "test_instance_5", 'compute-5')
        self.create_instance('small', "test_instance_6", 'compute-6')
        self.create_instance('small', "test_instance_7", 'compute-7')

        strategy = create_fw_update_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            max_parallel_worker_hosts=10)

        fw_update_controller_host_list = []
        fw_update_worker_host_list = []
        for host in self._host_table.values():
            if host._nfvi_host.admin_state == nfvi.objects.v1.HOST_ADMIN_STATE.UNLOCKED:
                if HOST_PERSONALITY.WORKER in host.personality:
                    fw_update_worker_host_list.append(host)

        strategy._add_worker_strategy_stages(
            sorted(fw_update_worker_host_list, key=lambda host: host.name),
            reboot=True)

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['controller-0']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 7,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'lock-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                     'entity_names': ['controller-1']},
                     {'name': 'system-stabilize', 'timeout': 60}
                 ]
                },
                {'name': 'fw-update-worker-hosts',
                 'total_steps': 8,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'fw-update-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3',
                                       'compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'stop-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1',
                                       'test_instance_2', 'test_instance_3',
                                       'test_instance_4', 'test_instance_5',
                                       'test_instance_6', 'test_instance_7']},
                     {'name': 'lock-hosts',
                     'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3',
                                       'compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'system-stabilize', 'timeout': 15},
                     {'name': 'unlock-hosts',
                      'entity_names': ['compute-0', 'compute-1',
                                       'compute-2', 'compute-3',
                                       'compute-4', 'compute-5',
                                       'compute-6', 'compute-7']},
                     {'name': 'start-instances',
                      'entity_names': ['test_instance_0', 'test_instance_1',
                                       'test_instance_2', 'test_instance_3',
                                       'test_instance_4', 'test_instance_5',
                                       'test_instance_6', 'test_instance_7']},
                     {'name': 'system-stabilize', 'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)
